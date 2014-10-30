# -*- coding: utf-8 -*-
u"""
Copyright 2014 Olivier Cortès <oc@1flow.io>.

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

import uuid

from django.utils.translation import ugettext_lazy as _

from sparks.django.utils import NamedTupleChoices


BROADCAST_CHOICES = NamedTupleChoices(
    'BROADCAST_CHOICES',

    ('NONE', -1, _(u'Not Broadcasted')),

    ('GLOBAL', 0, _(u'Use global broadcast setting')),

    ('TRUSTED', 1, _(u'To trusted instances only')),

    ('READ', 1, _(u'To instances that have read permission')),

    ('ALL', 2, _(u'To all non-blocked instances')),
)

NODE_PERMISSIONS = NamedTupleChoices(
    'NODE_PERMISSIONS',

    # This node is completely blocked and will be denied access.
    ('NONE', -1, _(u'NO permission (blocked)')),

    # This node is completely blocked and will be denied access.
    ('GLOBAL', 0, _(u'Use global permission')),

    # The node can talk to us, broadcast
    # other nodes, but doesn't read anything.
    ('BASE', 1, _(u'Access (token exchange)')),

    # The node can access only our statistics.
    ('STATS', 2, _(u'Statistics read')),

    # The node will be able to read only the models we give access to.
    ('FINE', 3, _(u'Fine-grained model read')),

    # The node can read all our models.
    ('READ', 4, _(u'Global models read')),

    # The node can read everything and will be
    # able to do more, but I don't know what yet.
    ('TRUST', 5, _(u'Trusted node')),
)

SYNC_STATUS = NamedTupleChoices(
    'SYNC_STATUS',

    ('AUTH_WAIT', 99, _(u'Waiting for authorization')),

    ('IDLE', 0, _(u'Idle')),

    ('SYNCHRONIZING', 1, _(u'Synchronizing')),
    # ('RESYNC', 2, _(u'Re-synchronizing')),

    ('FAILED', 9, _(u'Synchronization failed')),
)


def default_broadcast_choice():
    """ Return the global choice. """

    return BROADCAST_CHOICES.GLOBAL


def default_node_permission():
    """ Return the global choice. """

    return NODE_PERMISSIONS.GLOBAL


def generate_token():
    """ Return an uuid4 hex token. """

    return uuid.uuid4().hex
