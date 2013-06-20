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

from fabric.api import env, task, roles, local as fablocal

from sparks.fabric import (with_remote_configuration,
                           set_roledefs_and_parallel)
import sparks.django.fabfile as sdf

# Make the main deployment tasks immediately accessible
runable, deploy, fast_deploy = sdf.runable, sdf.deploy, sdf.fast_deploy
maintenance_mode, operational_mode = sdf.maintenance_mode, sdf.operational_mode
run_command, restart_services = sdf.run_command, sdf.restart_services

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
env.environment  = 'test'
env.pg_superuser = 'oneflow_admin'
env.pg_superpass = 'ZQmeDuNF7b2GMC'
env.repository   = 'git@dev.1flow.net:1flow.git'


def get_current_git_branch():
    return fablocal('git rev-parse --abbrev-ref HEAD',
                    capture=True).strip()


@task
def local():
    # NOTE: in theory a local environment doesn't need any roledef, because
    # we use Profile.development for running processes and all fabric
    # operations should be run via local(). BUT, in fact, they are run via
    # run() or sudo() (sparks doesn't make any difference, all tasks are
    # "remote"), that's why we populate roledefs, to benefit from all sparks
    # tasks.
    set_roledefs_and_parallel({
        'db': ['localhost'],
        'web': ['localhost'],
        'lang': ['localhost'],
        'flower': ['localhost'],
        'worker': ['localhost'],
        #'redis': ['localhost'],
    })

    # As of sparks 2.2+, it should not be needed to set env.host_string anymore,
    # but it's still comfortable to have it when lanching tasks that are not
    # fully roledefs-compatible (eg. sdf.compilemessages ran alone).
    env.host_string = 'localhost'
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
        edit firewall / iptables
        start LXC

    """

    #
    # WARNING: when adding preview machine(s),
    # don't forget to add django settings files for them…
    #
    set_roledefs_and_parallel({
        'db': ['obi.1flow.io'],
        'web': ['obi.1flow.io'],
        'lang': ['obi.1flow.io'],
        'flower': ['worbi.1flow.io'],
        'worker_high': ['worbi.1flow.io'],
        'worker_low': ['worbi.1flow.io'],
        #'redis': ['duncan.licorn.org'],
    })

    if branch is None:
        env.branch = get_current_git_branch()

    # implicit: else: branch will be 'develop',
    # set directly from the sparks defaults.

    # we force the user because we can login as standard user there
    env.user        = '1flow'
    env.env_was_set = True


@task(alias='prod')
def production():
    # we force the user because we can login as standard user there
    env.user        = '1flow'
    env.environment = 'production'
    set_roledefs_and_parallel({
        'db': ['1flow.io'],
        'web': ['1flow.io'],
        'flower': ['worker-01.1flow.io'],
        'worker_high': ['worker-01.1flow.io'],
        'worker_low': [
            'worker-02.1flow.io',
            #'worker-03.1flow.io', wait for DNS to expire…
            'worker-05.1flow.io',
        ],
        #'redis': ['duncan.licorn.org'],
    })
    env.env_was_set = True


@task
def zero(branch=None):
    """ A master clone, restarted from scratch everytime to test migrations. """

    set_roledefs_and_parallel({
        'db': ['zero.1flow.io'],
        'web': ['zero.1flow.io'],
        'worker': ['zero.1flow.io'],
        'flower': ['zero.1flow.io'],
        #'redis': ['zero.1flow.io'],
    })

    if branch is None:
        env.branch = 'develop'
    else:
        env.branch = get_current_git_branch()

    env.host_string = 'zero.1flow.io'

    # env.user is set via .ssh/config
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


@task
@with_remote_configuration
def testapps(remote_configuration):

    project_apps = (app.split('.', 1)[1] for app
                    in remote_configuration.django_settings.INSTALLED_APPS
                    if app.startswith('{0}.'.format(env.project)))

    print(str(list(project_apps)))


@task
@roles('db')
def firstdata():
    sdf.putdata('./oneflow/landing/fixtures/landing_2013-05-14_final-before-beta-opening.json') # NOQA
    sdf.putdata('./oneflow/base/fixtures/base_2013-05-14_final-before-beta-opening.json') # NOQA


@task(aliases=('first', ))
def firstdeploy():
    deploy()
    firstdata()
