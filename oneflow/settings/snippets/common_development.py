# -*- coding: utf-8 -*-
#
# Include your development machines hostnames here.
#
# NOTE: this is not strictly needed, as Django doesn't enforce
# the check if DEBUG==True. But Just in case you wanted to disable
# it temporarily, this could be a good thing to have your hostname
# here.
#
# If you connect via http://localhost:8000/, everything is already OK.
#
u"""
Copyright 2013-2014 Olivier Cortès <oc@1flow.io>.

This file is part of the 1flow project.

1flow is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of
the License, or (at your option) any later version.

1flow is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with 1flow.  If not, see http://www.gnu.org/licenses/

"""

# import re

TEMPLATE_CONTEXT_PROCESSORS += (
    'django.core.context_processors.debug',
)

EMAIL_SUBJECT_PREFIX='[1flow DEV] '

INTERNAL_IPS = (
    '127.0.0.1',

    # My LAN's proxy address, else the nginx proxy makes debug disappear.
    '192.168.111.111',
)

PROJECT_APPS = (
    'oneflow.base',

    # XXX: The landing should be conditional, no?
    'oneflow.landing',

    'oneflow.core',
)

JENKINS_TASKS = (
    'django_jenkins.tasks.with_coverage',
    'django_jenkins.tasks.django_tests',   # select one django or
    # 'django_jenkins.tasks.dir_tests'      # directory tests discovery

    # Doesn't work.
    # 'django_jenkins.tasks.run_flake8',

    # Superseded by flake8
    'django_jenkins.tasks.run_pep8',
    'django_jenkins.tasks.run_pyflakes',

    # 'django_jenkins.tasks.run_pylint',
    # 'django_jenkins.tasks.run_jslint',
    # 'django_jenkins.tasks.run_csslint',
    'django_jenkins.tasks.run_sloccount',
    # 'django_jenkins.tasks.lettuce_tests',
)

ALLOWED_HOSTS += [
    'localhost',
]

# NOTE: INSTALLED_APPS is a list (not a tuple)
# in 1flow, because of the conditional landing.
INSTALLED_APPS += [
    'django_jenkins',
    'django_nose',
    # 'devserver',
]
# 'template_debug', )

DEVSERVER_DEFAULT_ADDR = '0.0.0.0'
DEVSERVER_DEFAULT_PORT = 8000

DEVSERVER_MODULES = (
    # 'devserver.modules.sql.SQLRealTimeModule',
    # 'devserver.modules.sql.SQLSummaryModule',
    # 'devserver.modules.profile.ProfileSummaryModule',

    # Modules not enabled by default
    # 'devserver.modules.ajax.AjaxDumpModule',
    'devserver.modules.profile.MemoryUseModule',
    'devserver.modules.cache.CacheSummaryModule',
    # 'devserver.modules.profile.LineProfilerModule',
)

# DEVSERVER_FILTER_SQL = (
#        re.compile('core_\w+'),  # Filter all queries related to 1flow code
# )

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
JENKINS_TEST_RUNNER = 'django_jenkins.nose_runner.CINoseTestSuiteRunner'

NOSE_ARGS = ['--stop']  # , '--ipdb', '--ipdb-failures', ]

import logging
import south.logger  # NOQA

logging.getLogger('south').setLevel(logging.CRITICAL)
