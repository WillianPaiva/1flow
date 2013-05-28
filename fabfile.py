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

from fabric.api import env, task, local as fablocal

from sparks.fabric import with_remote_configuration, set_roledefs_and_hosts
import sparks.django.fabfile as sdf

# Make the main deployment tasks immediately accessible
runable, deploy, fast_deploy = sdf.runable, sdf.deploy, sdf.fast_deploy
maintenance_mode, operational_mode = sdf.maintenance_mode, sdf.operational_mode
run_command = sdf.run_command

# The Django project name
env.project      = 'oneflow'
env.virtualenv   = '1flow'
env.user         = '1flow'
# Where is the django project located
env.root         = '/home/1flow/www/src'
env.environment  = 'test'
env.pg_superuser = 'oneflow_admin'
env.pg_superpass = 'ZQmeDuNF7b2GMC'


@task
def local():
    # NOTE: for a local environment, this roledefs is a pure placebo,
    # because sparks will not try to deploy anything via supervisor.
    # We already have a feature-complete-and-ready Profile.development.
    set_roledefs_and_hosts({
        'db': ['localhost'],
        'web': ['localhost'],
        'worker': ['localhost'],
        'flower': ['localhost'],
        #'redis': ['localhost'],
    })
    env.user        = pwd.getpwuid(os.getuid()).pw_name
    env.root        = os.path.expanduser('~/sources/1flow')
    env.env_was_set = True


@task(alias='test')
def preview(branch=None):
    """ This is the default config, we don't need to set anything more.

        To create a new test environment:

        adapt .ssh/config
        ssh duncan
        lxc-clone
        in the LXC rootfs, clean /etc/supervisor/conf.d/*
        edit /etc/rc.local
        start LXC

    """

    set_roledefs_and_hosts({
        'db': ['obi.1flow.io'],
        'web': ['obi.1flow.io'],
        'flower': ['worbi.1flow.io'],
        'worker_high': ['obi.1flow.io'],
        'worker_low': ['worbi.1flow.io'],
        #'redis': ['duncan.licorn.org'],
    })

    if branch is None:
        env.branch = fablocal('git rev-parse --abbrev-ref HEAD',
                              capture=True).strip()

    # implicit: else: branch will be 'develop',
    # set directly from the sparks defaults.

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
    env.environment = 'production'
    set_roledefs_and_hosts({
        'db': ['1flow.io'],
        'web': ['1flow.io'],
        'flower': ['1flow.io'],
        'worker_high': ['1flow.io'],
        'worker_low': ['worker02.1flow.io'],
        #'redis': ['duncan.licorn.org'],
        #'db': ['duncan.licorn.org'],
    })
    env.env_was_set = True


@task
@with_remote_configuration
def testapps(remote_configuration):

    project_apps = (app.split('.', 1)[1] for app
                    in remote_configuration.django_settings.INSTALLED_APPS
                    if app.startswith('{0}.'.format(env.project)))

    print(str(list(project_apps)))
