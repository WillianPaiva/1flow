# -*- coding: utf-8 -*-
u"""
Copyright 2012-2014 Olivier Cortès <oc@1flow.io>.

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

import logging
import humanize

from celery import task

from django.contrib.auth import get_user_model
from social.apps.django_app.utils import load_strategy

from .utils.dateutils import now

LOGGER = logging.getLogger(__name__)

User = get_user_model()


@task
def celery_beat_test():
    """ Test Celery beat by issuing a LOGGER() call. """

    LOGGER.debug(u'testing celery beat scheduler (debug)…')
    LOGGER.info(u'testing celery beat scheduler (info)…')
    LOGGER.warning(u'testing celery beat scheduler (warning)…')
    LOGGER.error(u'testing celery beat scheduler (error)…')
    LOGGER.critical(u'testing celery beat scheduler (critical)…')


@task(queue='high')
def refresh_access_tokens():
    """ Refresh all social access tokens in turn.

    This should avoid hitting http://dev.1flow.net/webapps/1flow/group/664/
    """

    start_time = now()

    users = User.objects.all()

    # sleep_time = 1500 / count
    count  = users.count()
    done   = 0
    errors = 0
    nosoc  = 0

    django_stategy = load_strategy()

    for user in users:
        # See http://django-social-auth.readthedocs.org/en/latest/use_cases.html#token-refreshing # NOQA
        # LOGGER.warning(u'Refreshing invalid access_token for user %s.',
        #               user.username)

        social_accounts = user.social_auth.filter(provider='google-oauth2')

        if social_accounts.count() == 0:
            nosoc += 1
            continue

        for social in social_accounts:
            try:
                social.refresh_token(django_stategy)

            except:
                LOGGER.exception(u'Access token could not be refreshed for '
                                 u'user %s, forcing re-authentication at '
                                 u'next login.', user.username)

                # With `associate_by_email` in the social-auth pipeline,
                # a reconnecting user will be re-associated with his
                # existing Django account, getting back all his preferences
                # and 1flow data. We delete here only the association.
                social.delete()
                errors += 1
            else:
                done += 1

    LOGGER.warning(u'refresh_access_tokens finished, %s/%s refreshed, '
                   u'%s error(s), %s not associated, duration: %s.',
                   done, count, errors, nosoc,
                   humanize.time.naturaldelta(now() - start_time))
