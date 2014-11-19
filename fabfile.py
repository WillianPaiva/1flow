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

from fabric.api import env, task, roles, local as fablocal

from sparks.fabric import (with_remote_configuration,
                           set_roledefs_and_parallel,
                           worker_roles)
import sparks.django.fabfile as sdf

# Make the main deployment tasks and my other favorites immediately accessible
runable, deploy, fast_deploy = sdf.runable, sdf.deploy, sdf.fast_deploy
maintenance_mode, operational_mode = sdf.maintenance_mode, sdf.operational_mode
run_command, restart_services = sdf.run_command, sdf.restart_services
stop, start, status = sdf.stop_services, sdf.start_services, sdf.status_services
remove, pick, role = sdf.remove_services, sdf.pick, sdf.role
push_environment, git_pull = sdf.push_environment, sdf.git_pull
migrate, git_update = sdf.migrate, sdf.git_update

USE_JENKINS  = pwd.getpwuid(os.getuid()).pw_name == 'jenkins'
JENKINS_JOB  = os.environ.get('JOB_NAME', '1flow')
JENKINS_ROOT = '/var/lib/jenkins/jobs/{0}/workspace'.format(JENKINS_JOB)

# The Django project name
env.project    = 'oneflow'
env.virtualenv = '1flow'
env.parallel   = {'true': True, 'false': False}[
    os.environ.get('SPARKS_PARALLEL', 'true').lower()]
env.encoding   = 'utf-8'
# cf. http://stackoverflow.com/q/9181153/654755
env.shell      = '/bin/bash -l -c'

# WARNING: don't set `env.user` here, it creates false-negatives when
# bare-connecting to servers manually from the current directory. Eg.:
#       paramiko.transport[DEBUG] userauth is OK
#       paramiko.transport[INFO] Authentication (publickey) failed.
# Whereas everything is OK from outside this directory.
# Conclusion: it seems `env.user` overrides even the ~/.ssh/config values.

# Where is the django project located
if USE_JENKINS:
    env.root = JENKINS_ROOT
else:
    env.root = '/home/1flow/www/src'

env.environment  = 'test'
# env.repository   = 'git@dev.1flow.net:1flow.git'
env.repository   = 'git@github.com:1flow/1flow.git'


def get_current_git_branch():
    """ Get current git branch (on local machine). """

    return fablocal('git rev-parse --abbrev-ref HEAD',
                    capture=True).strip()


@task
def local():
    """ The local-development task. """

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
        'beat': ['localhost'],
        'shell': ['localhost'],
        'flower': ['localhost'],
        'worker': ['localhost'],
    })

    # As of sparks 2.2+, it should not be needed to set env.host_string anymore,
    # but it's still comfortable to have it when lanching tasks that are not
    # fully roledefs-compatible (eg. sdf.compilemessages ran alone).
    env.host_string = 'localhost'

    if USE_JENKINS:
        env.root = JENKINS_ROOT
    else:
        env.root = os.path.expanduser('~/sources/1flow')

    env.env_was_set = True


@task(alias='test')
def preview(branch=None):
    """ Default config. We don't need to set anything more.

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
        'beat': ['obi.1flow.io'],
        'shell': ['worbi.1flow.io'],
        'flower': ['worbi.1flow.io'],
        'worker_high': ['obi.1flow.io'],
        'worker_medium': ['worbi.1flow.io'],
        'worker_low': ['worbi.1flow.io'],
    })

    if branch is None:
        env.branch = get_current_git_branch()
    # implicit: else: branch will be 'develop',
    # set directly from the sparks defaults.

    env.sparks_options = {
        'nice_arguments': {
            # 'worker_low': '-n 5',
            # 'worker_medium': '-n 1',
            'worker_high': '-n -3',
        },

        'worker_concurrency': {
            'worker_low': 2,
            'worker_medium': 2,
            'worker_high': 4,
        }
    }

    # we force the user because we can login as standard user there
    env.user        = '1flow'
    env.env_was_set = True


@task(aliases=('work', ))
def workers(with_shell=False, with_flower=False):
    """ Just setup the workers roles so we can act easily on all of them. """

    #
    # NOTE: don't try to simply set:
    #       env.roles = worker_roles[:] + ['beat']
    #
    #       This will not work as expected for hosts assuming more than
    #       one role (the first of them will get run multiple times).
    #
    roles = worker_roles[:] + ['beat']

    if with_shell:
        roles.append('shell')

    if with_flower:
        roles.append('flower')

    role(*roles)


@task(aliases=('kill', ))
def reboot(more=False):
    """ Remotely reboot all systems. """

    run_command("ps ax | grep 'celery.*worker' | grep -v grep "
                "| awk '{print $1}' | sudo xargs -I% kill % || true")
    if more:
        run_command("ps ax | grep 'celery.*worker' | grep -v grep "
                    "| awk '{print $1}' | sudo xargs -I% kill -9 % || true")


@task
def count():
    """ Remotely count all worker processes. """

    run_command("ps ax | grep 'celery.*worker' | grep -v grep "
                "| wc -l")


@task(alias='prod')
def production():
    """ The 1flow.io production configuration task. """

    # we force the user because we can login as standard user there
    env.user        = '1flow'
    env.environment = 'production'

    # Switch to develop to avoid needing to release a new version
    # for every little patch. 1flow.io is our new testbed. In fact,
    # It's a continuous delivery platform :-D
    env.branch = 'develop'

    env.sparks_options = {
        'shell_arguments': {
            'command_post_args': "--NotebookApp.ip='*'",
        },

        'worker_information': {
            'worker_mongo': (
                'MongoDB worker (transient)',
                'high,medium,low'
            ),
            'worker_sync': (
                'Inter-node synchronization worker',
                'sync,permanent'
            ),
            'worker_net': (
                'Network-related worker',
                'swarm,refresh'
            ),
            'worker_default': (
                'Default celery queue worker',
                'default,create'
            ),
            'worker_articles': (
                'Articles parsing worker',
                'fetch,background'
            ),
            'worker_longtasks': (
                'Long tasks worker',
                'check,clean'
            ),
        },

        'custom_arguments': {
            '__all__': '--without-heartbeat --without-mingle --without-gossip',
        },

        'nice_arguments': {

            # Lower priority
            'worker_mongo': '-n 3',
            'worker_longtasks': '-n 1',

            # Higher priority
            'flower': '-n -1',
            'shell': '-n -5',

            # Others are default.
        },

        'ionice_arguments': {
            'shell': '-c 2 -n 1',
        },

        'worker_pool': {
            '__all__': 'gevent',
        },

        # 'repository': {
        #     '__all__': 'git@10.0.3.110:1flow.git',
        # },

        'autoscale': {
            'worker_mongo':   '136,34',  # 'high,medium,low',
            'worker_sync':    '32,8',    # 'sync',
            'worker_net':     '64,16',  # 'swarm,refresh',
            'worker_default': '32,8',    # 'default,create',
            'worker_articles': '24,6',   # 'fetch,background',
            'worker_longtasks': '2,1',   # 'check,clean',

            '__all__': '8,2',
        },

        'max_tasks_per_child': {
            # Cleaning tasks are long; worker
            # consumes ~500Mb after first run.
            'worker_longtasks': '1',

            '__all__': '128',
        },

        'worker_soft_time_limit': {
            'worker_net': '120',

            # I consider that a few minutes is enough to fetch an article
            # and convert it to markdown on a loaded system. Note that it
            # can take time because of low priority of worker processes.
            # So we have to let them a fair amount of time. If it doesn't
            # acheive the conversion in this time frame, there is probably
            # a more serious problem.
            'worker_articles': '300',

            # 7 days: 604800
            # 4 days seems to be a good start.
            # If tasks last more than that, they should
            # probably be split into smaller parts.
            'worker_longtasks': '345600',

            # For general-purpose tasks, 10 minutes can seem very long.
            # On a loaded system, this is reasonable for medium-duration
            # tasks.
            '__all__': '600',
        },
    }

    set_roledefs_and_parallel({
        'db': ['1flow.io', ],
        'web': ['1flow.io', ],

        'beat': ['worker-01.1flow.io', ],
        'flower': ['worker-01.1flow.io', ],
        'shell': ['worker-01.1flow.io', ],

        'worker_sync': [
            'worker-01.1flow.io',
        ],
        'worker_default': [
            'worker-02.1flow.io',
        ],
        'worker_net': [
            'worker-02.1flow.io',
        ],
        'worker_articles': [
            'worker-03.1flow.io',
        ],
        'worker_longtasks': [
            'worker-04.1flow.io',
        ],
        'worker_mongo': [
            'worker-04.1flow.io',
        ],
    })
    env.env_was_set = True


@task
def zero(branch=None):
    """ A master clone, restarted from scratch everytime to test migrations. """

    set_roledefs_and_parallel({
        'db': ['zero.1flow.io'],
        'web': ['zero.1flow.io'],
        'beat': ['zero.1flow.io'],
        'shell': ['zero.1flow.io'],
        'worker': ['zero.1flow.io'],
        'flower': ['zero.1flow.io'],
    })

    if branch is None:
        env.branch = 'develop'
    else:
        env.branch = get_current_git_branch()

    env.host_string = 'zero.1flow.io'

    env.sparks_options = {
        'worker_concurrency': {
            '__all__': 2,
        }
    }

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
    """ Get the remote list of Django apps, to see if settings load. """

    project_apps = (app.split('.', 1)[1] for app
                    in remote_configuration.django_settings.INSTALLED_APPS
                    if app.startswith('{0}.'.format(env.project)))

    print(str(list(project_apps)))


@task
@roles('db')
def firstdata():
    """ Used when deploying a new http://1flow.io/ production environment.

    On other environments (eg. development, other domains), the
    `oneflow.landing` app is not installed, and calling this task will
    fail.
    """

    sdf.putdata('./oneflow/landing/fixtures/landing_2013-05-14_final-before-beta-opening.json')  # NOQA
    minimal_content()
    # No need, this will fail in many cases,
    # and the first run will do it anyway.
    #
    # sdf.putdata('./oneflow/fixtures/djcelery_2013-06-30_0001.json')


@task
@roles('db')
def minimal_content():
    """ Load minimal content in the database. """

    sdf.putdata('./oneflow/base/fixtures/base_2013-05-14_final-before-beta-opening.json')  # NOQA

    # No need, this will fail in many cases,
    # and the first run will do it anyway.
    #
    # sdf.putdata('./oneflow/fixtures/djcelery_2013-06-30_0001.json')


@task(aliases=('first', ))
def firstdeploy():
    """ First deployment (anywhere). deploy() then firstdata(). """

    deploy()
    firstdata()
