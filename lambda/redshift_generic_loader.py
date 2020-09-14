import psycopg2
import boto3
import json
import datetime as dt
import pytz


def get_credentials(credentialName, region):
    """
    Call to the AWS Secret Manager where the credentials are stored encrypted
    :param credentialName: Name assigned to the specific credentials
    :param region: AWS datacenter region
    :return: a tuple with 2 items:
            [0] ->  0 for success or 1 for error
            [1] ->  credentials or error message
    """
    try:
        session = boto3.session.Session()
        client = session.client(service_name='secretsmanager', region_name=region)
        secret = json.loads(client.get_secret_value(SecretId=credentialName)['SecretString'])
        return (0, secret)
    except Exception as e:
        return (1, str(e))


def lambda_handler(event, context):
    sns = boto3.client('sns')
    s3 = boto3.client('s3')

    try:
        flag_config_file_exists = False
        flag_connection_created = False

        # Get info from triggered event
        key = event["Records"][0]["s3"]["object"]["key"]
        temp1 = key.split('/')
        file_uploaded = temp1.pop()
        print(f'File uploaded: {file_uploaded}')
        temp1.append('config.json')
        config_file = '/'.join(temp1)
        bucket_name = event["Records"][0]["s3"]["bucket"]["name"]
        print(f'Expected config file: {config_file}')
        print(f'Bucket: {bucket_name}')

        # Get config file and prepare to use it
        s3.download_file(bucket_name, config_file, '/tmp/config.json')
        flag_config_file_exists = True
        print(f'File Downloaded')
        with open('/tmp/config.json', 'r') as open_file:
            data = json.load(open_file)
        # Check if the uploaded file is the one to be loaded
        if file_uploaded != data['file_to_load']:
            print('Uploaded file is not meant to be loaded, check config.json if it is incorrect')
            return "Success!"

        region = data['aws_region']
        db_credentials = data['secret_manager']['redshift']
        aws_credentials = data['secret_manager']['agent']
        sql = data['redshift']['sql']
        sns_topic = data['sns']['topicARN']
        tableName = data['redshift']['table_name']

        # Get credentials and check if it was decrypted successfully
        db = get_credentials(db_credentials, region)
        aws = get_credentials(aws_credentials, region)
        if db[0] > 0 or aws[0] > 0:
            raise Exception(f'Secret Manager Exception: {db[1]}')
        else:
            print("Success: {}".format(db[1]))
            print("Success: {}".format(aws[1]))
            db = db[1]
            aws = aws[1]

            # Inject credential variables into sql string
            print(f'Trying to inject...')
            sql = sql.replace('{access_key_id}', aws['access_key_id'])
            sql = sql.replace('{secret_access_key}', aws['secret_access_key'])
            print(f'SQL: {sql}')

            # Connect to Redshift
            conn = psycopg2.connect(user=db['username'], password=db['password'], host=db['host'], port=db['port'],
                                    dbname=db['dbName'])
            flag_connection_created = True

            # Timestamp last_refresh table
            local_tz = pytz.timezone("America/Toronto")
            timestamp = dt.datetime.now().astimezone(local_tz).strftime("%b %d, %Y %I:%M:%S %p")
            sql_timestamp = f'''
                            delete from last_refreshed where table_name='{tableName}' 
                                and exists (select 1 from last_refreshed where table_name='{tableName}');
                            insert into last_refreshed values ('{tableName}', '{timestamp}');
                            '''
            cursor = conn.cursor()
            cursor.execute(sql)
            cursor.execute(sql_timestamp)
            conn.close()

            # Publish a simple message to the specified SNS topic
            response = sns.publish(
                TopicArn=sns_topic,
                Message=f'{tableName} was loaded successfully!',
                Subject=f'{tableName} was loaded successfully!',
            )
            print(response)
    except Exception as e:
        if not (flag_config_file_exists):
            print('Nothing to do! The config.json does not exist')
            return "Success!"

        if flag_connection_created:
            print('Closing connection to Redshift...')
            conn.close()

        print("Loading Exception: {}".format(str(e)))

        response = sns.publish(
            TopicArn=sns_topic,
            Message=f'Loading Exception: {str(e)}',
            Subject=f'{tableName} has failed!',
        )
        print(response)
        raise Exception(str(e))
    return "Success!"