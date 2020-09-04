from aws_cdk import (
    core,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_s3 as s3,
    aws_ec2 as ec2,
    aws_s3_notifications as s3_notif
)


class GbcPrototype1Stack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        if kwargs['env'].account == '828661178764':
            gbc_environment = 'devl'
        else:
            raise ValueError('Account not mapped!')

        # Define location of lambda deployment packages:
        bucket_source = s3.Bucket.from_bucket_name(self, 'bucket_source_id', bucket_name='gbc-lambda')
        generic_loader = _lambda.S3Code(bucket_source, key='generic-loader/Archive.zip')

        # Define attributes for the networking part:
        _vpc = ec2.Vpc.from_vpc_attributes(
            self, 'myVPC',
            vpc_id='vpc-042f6b22897562107',
            availability_zones=['ca-central-1a', 'ca-central-1b']
        )

        _subnets = [
            ec2.Subnet.from_subnet_id(self, 'subnet1', subnet_id='subnet-0579afb06d9cec8ed'),
            ec2.Subnet.from_subnet_id(self, 'subnet2', subnet_id='subnet-07a0e458dc7ea0228')
        ]

        _security_group = [
            ec2.SecurityGroup.from_security_group_id(self, 'mySG', security_group_id='sg-0264ea677ccfef4ff')
        ]

        my_lambda = _lambda.Function(
            self, 'redshift-generic-loader',
            runtime=_lambda.Runtime.PYTHON_3_6,
            code=generic_loader,
            timeout=core.Duration.seconds(30),
            handler='lambda_function.lambda_handler',
            role=iam.Role.from_role_arn(self, 'myRole',
                                        role_arn='arn:aws:iam::828661178764:role/lambda-data-analytics',
                                        mutable=False),
            vpc=_vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=_subnets),
            security_groups=_security_group
        )

        # Create main bucket for pipelines and register notifications:
        main_bucket = s3.Bucket(
            self, 'new_bucket_id',
            bucket_name=f'gbc-analytics-prototype-1-cdk-{gbc_environment}',
            versioned=True
        )

        target_lambda = s3_notif.LambdaDestination(my_lambda)
        key_filter_1 = s3.NotificationKeyFilter(prefix='rafael-test/')
        main_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            target_lambda,
            key_filter_1
        )
