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

from celery.task.control import inspect  # , revoke


LOGGER = logging.getLogger(__name__)


def celery_tasks_names(inspect):
    """ Return a set() of Celery tasks names. """

    tasks_names = set()

    try:
        for k, v in inspect.registered_tasks().iteritems():
            for tn in v:
                if not (tn.startswith('celery') or tn.startswith('raven')):
                    tasks_names.add(tn)

    except:
        LOGGER.exception('Could not gather celery tasks names')

    return tasks_names


def celery_workers_status(inspect):
    """ REVIEW. """

    print ',\n'.join('%s: %s scheduled task(s)' % (k, len(v))
                     for (k, v) in sorted(inspect.scheduled().iteritems()))


# from flower.app import Flower
# from flower.command import options, define
# from flower.models import TaskModel
# options.broker_api = settings.BROKER_URL
# app = Flower(options=options)
# app.start()


def celery_active_queues(inspect):
    """ Return a set of celery active queues. """

    active_queues = {}

    for wname, wattr in inspect.active_queues().iteritems():
        for queue_info in wattr:
            qname = queue_info['name']
            if qname in active_queues:
                active_queues[qname].append(wname)

            else:
                active_queues[qname] = [wname]

    return active_queues


def celery_status():
    """ Full set of celery status. """

    def ftot(x):
        return '\n'.join('    %s: %s' % (l, w) for (l, w)
                         in sorted(x.iteritems()))

    i = inspect()

    try:
        active_queues = celery_active_queues(i)
    except:
        LOGGER.exception(u'Could not get Celery active queues')
        active_queues = {}

    return {
        'tasks_names': sorted(celery_tasks_names(i)),
        'active_queues': active_queues,
    }
