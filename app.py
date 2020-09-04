#!/usr/bin/env python3

from aws_cdk import core

from gbc_prototype_1.gbc_prototype_1_stack import GbcPrototype1Stack


app = core.App()

gbc_env_DEVL = core.Environment(account='828661178764', region='ca-central-1')
# gbc_env_PROD = core.Environment(account='XXXXXXXXXXXX', region='ca-central-1')

GbcPrototype1Stack(app, "gbc-prototype-1", env=gbc_env_DEVL)

app.synth()
