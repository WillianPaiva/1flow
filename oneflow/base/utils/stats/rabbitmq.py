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
import pyrabbit

from django.conf import settings

# from sparks.fabric import is_localhost
from oneflow.base.utils.http import split_url

LOGGER = logging.getLogger(__name__)

# AMQP_RE = re.compile(ur'amqp://(?P<username>[^:]+):(?P<password>\w+)@(?P<hostname_and_port>[^/]+)/(?P<vhost>[^/]+)', re.I)  # NOQA


def get_rabbitmq_client_args_from_broker_url():
    """ Decompose BROKER_URL into a tuple suitable for rabbitmq.Client(). """

    proto, host_and_port, vhost = split_url(settings.BROKER_URL)

    things = host_and_port.rsplit('@', 1)

    if len(things) > 1:
        username, password = things[0].split(':', 1)
        host_and_port = things[1]
    else:
        username, password = 'guest', 'guest'

    if not vhost:
        vhost = '/'

    host_and_port = host_and_port.replace(':5672', ':55672')

    return [host_and_port, username, password, vhost]


if settings.BROKER_URL.lower().startswith('amqp://'):
    rabbitmq_params = get_rabbitmq_client_args_from_broker_url()
    rabbitmq_client = pyrabbit.Client(*rabbitmq_params[:-1])

    try:
        rabbitmq_client.is_alive()
    except:
        rabbitmq_params[0] = rabbitmq_params[0].replace(':55672', ':15672')
        rabbitmq_client = pyrabbit.Client(*rabbitmq_params[:-1])

    rabbitmq_vhost  = rabbitmq_params[-1]
else:
    rabbitmq_client = None


def rabbitmq_queues():
    """ Return rabbitMQ client get_queues() result, or {}.

    ``{}`` is when RabbitMQ is not available, eg. ``BROKER_URL`` doesn't
     start with ``amqp://``.
    """

    if rabbitmq_client is None:
        return {}

    try:
        queues = rabbitmq_client.get_queues(rabbitmq_vhost)

    except:
        LOGGER.exception(u'Could not connect to RabbitMQ API. '
                         u'Is the web interface plugin enabled?')
        return {}

    return [
        q for q in sorted(queues, key=lambda q: q['name'])
        if not (
            q['name'].startswith('amq.gen')
            or 'celery' in q['name']
        )
    ]
