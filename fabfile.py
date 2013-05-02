# -*- coding: utf-8 -*-
import os

# Use this in case paramiko seems to go crazy. Trust me, it can do, especially
# when using the multiprocessing module.
#
# import logging
# logging.basicConfig(format=
#                     '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#                     level=logging.DEBUG)


from fabric.api import env, task

import sparks.django.fabfile as sdf

# Make the main deployment tasks immediately accessible
runable, deploy, fast_deploy = sdf.runable, sdf.deploy, sdf.fast_deploy

# The Django project name
env.project        = 'oneflow'
env.virtualenv     = '1flow'
# Where is the django project located
env.root           = '/home/1flow/www/src'
env.host_string    = 'obi.1flow.net'
env.environment    = 'test'
env.pg_superuser   = 'oneflow_admin'
env.pg_superpass   = 'ZQmeDuNF7b2GMC'


@task
def duncan():
    """ As of 20130501, this is not used yet. """

    env.host_string = 'duncan'
    env.environment = 'hoster'


@task
def local():
    env.host_string = 'localhost'
    env.environment = 'test'
    env.root        = os.path.expanduser('~/sources/1flow')


@task
def test():
    """ This is the default config, we don't need to set anything more. """

    pass


@task
def testapp():
    """ Install the 1flowapp.com django app on test. """

    env.environment_vars = 'SPARKS_DJANGO_SETTINGS=obi_1flowapp_com'


@task(alias='prod')
def production():
    env.host_string = '1flow.net'
    env.environment = 'production'


@task
def prodapp():
    env.host_string      = '1flow.net'
    env.environment      = 'production'
    env.environment_vars = 'SPARKS_DJANGO_SETTINGS=1flowapp_com'
