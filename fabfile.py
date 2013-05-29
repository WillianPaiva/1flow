# -*- coding: utf-8 -*-
"""
    1flow fabfile, which relies on sparks.

    Example calls:

        # migrate() must have the *named* `args` argument,
        # else it will conflicts with the implicit `remote_configuration`.
        fab local sdf.migrate:args='redisboard --fake'

        # Thus, this won't work:
        fab local sdf.migrate:'redisboard --fake'

        # copy model data from a DB to another:
        fab test sdf.getdata:landing
        fab local sdf.putdata

        # and then to production:
        fab production sdf.putdata

"""
import os
import pwd

from fabric.api import env, task, run
from fabric.context_managers import cd

from sparks.fabric import with_remote_configuration
import sparks.django.fabfile as sdf

# Make the main deployment tasks immediately accessible
runable, deploy, fast_deploy = sdf.runable, sdf.deploy, sdf.fast_deploy
maintenance_mode, operational_mode = sdf.maintenance_mode, sdf.operational_mode

# The Django project name
env.project    = 'oneflow'
env.virtualenv = '1flow'

# WARNING: don't set `env.user` here, it creates false-negatives when
# bare-connecting to servers manually from the current directory. Eg.:
#       paramiko.transport[DEBUG] userauth is OK
#       paramiko.transport[INFO] Authentication (publickey) failed.
# Whereas everything is OK from outside this directory.
# Conclusion: it seems `env.user` overrides even the ~/.ssh/config values.

# Where is the django project located
env.root         = '/home/1flow/www/src'
env.host_string  = 'obi.1flow.io'
env.environment  = 'test'
env.pg_superuser = 'oneflow_admin'
env.pg_superpass = 'ZQmeDuNF7b2GMC'
env.repository   = 'olive@dev.1flow.net:1flow.git'


@task
def local():
    env.host_string = 'localhost'
    env.environment = 'test'
    env.user        = pwd.getpwuid(os.getuid()).pw_name
    env.root        = os.path.expanduser('~/sources/1flow')
    env.env_was_set = True


@task(alias='test')
def preview():
    """ This is the default config, we don't need to set anything more.

        To create a new test environment:

        adapt .ssh/config
        ssh duncan
        lxc-clone
        in the LXC rootfs, clean /etc/supervisor/conf.d/*
        edit /etc/rc.local
        start LXC

    """

    # we force the user because we can login as standard user there
    env.user        = '1flow'
    env.env_was_set = True


@task
def zero():
    """ A master clone, restarted from scratch everytime to test migrations. """

    # set_roledefs_and_hosts({
    #     'db': ['zero.1flow.io'],
    #     'web': ['zero.1flow.io'],
    #     'worker': ['zero.1flow.io'],
    #     'flower': ['zero.1flow.io'],
    #     #'redis': ['zero.1flow.io'],
    # })

    # env.user is set via .ssh/config
    env.host_string = 'zero.1flow.io'
    env.branch      = 'develop'
    env.env_was_set = True


@task
def oneflowapp():
    """ 1flowapp.com parameters; must be used with test or production. """

    raise RuntimeError('As of 20130510, this environment '
                       'should not be used anymore.')

    if not hasattr(env, 'env_was_set'):
        # Without this, settings can be messed up.
        raise RuntimeError('Type `oneflowapp` *AFTER* test|production|local !')

    if env.environment == 'production':
        env.sparks_djsettings = '1flowapp_com'

    elif env.environment == 'test':
        if env.host_string == 'localhost':
            env.sparks_djsettings = 'chani_app'
        else:
            env.sparks_djsettings = 'obi_1flowapp_com'

    else:
        raise RuntimeError('environment not supported')


@task(alias='prod')
def production():

    # we force the user because we can login as standard user there
    env.user        = '1flow'
    env.host_string = '1flow.io'
    env.environment = 'production'
    env.env_was_set = True


@task
def command(cmd):
    with sdf.activate_venv():
        with cd(env.root):
            run(cmd)


@task
def out(cmd):
    with sdf.activate_venv():
        with cd(env.root):
            print(run(cmd) != '')


@task
@with_remote_configuration
def testapps(remote_configuration):

    project_apps = (app.split('.', 1)[1] for app
                    in remote_configuration.django_settings.INSTALLED_APPS
                    if app.startswith('{0}.'.format(env.project)))

    print(str(list(project_apps)))


@task
def firstdeploy():
    deploy()
    sdf.putdata('./oneflow/landing/fixtures/landing_2013-05-14_final-before-beta-opening.json') # NOQA
    sdf.putdata('./oneflow/base/fixtures/base_2013-05-14_final-before-beta-opening.json') # NOQA
