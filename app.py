#!/usr/bin/env python3

from aws_cdk import core

from gbc_prototype_1.gbc_prototype_1_stack import GbcPrototype1Stack


app = core.App()
GbcPrototype1Stack(app, "gbc-prototype-1")

app.synth()
