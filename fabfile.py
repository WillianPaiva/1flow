# -*- coding: utf-8 -*-
import os

# Use this in case paramiko seems to go crazy. Trust me, it can do, especially
# when using the multiprocessing module.
#
#import logging
# logging.basicConfig(format=
#                     '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#                     level=logging.DEBUG)


from fabric.api import env, task

import sparks.django.fabfile as sdf

from oneflow import settings as oneflow_settings

# Make the main deployment tasks immediately accessible
runable, deploy, fast_deploy = sdf.runable, sdf.deploy, sdf.fast_deploy

env.project     = '1flow'
env.virtualenv  = '1flow'
env.settings    = oneflow_settings
env.root        = '/home/1flow/www'
env.host_string = 'obi.1flow.net'
env.environment = 'test'


@task
def duncan():
    env.host_string = 'duncan'
    env.environment = 'hoster'


@task
def local():
    env.host_string = 'localhost'
    env.environment = 'test'
    env.root        = os.path.expanduser('~/sources/1flow')


@task
def test():
    """ This is the default config, we don't need to set anything here. """

    pass


@task(alias='prod')
def production():
    env.host_string = '1flow.net'
    env.environment = 'production'


@task
def oneflowapp():
    env.host_string      = '1flow.net'
    env.environment      = 'production'
    env.environment_vars = 'SPARKS_DJANGO_SETTINGS=oneflowapp'
