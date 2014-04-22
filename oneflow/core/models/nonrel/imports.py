# -*- coding: utf-8 -*-
"""
    Copyright 2013-2014 Olivier Cortès <oc@1flow.io>

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

from celery import task


from mongoengine import Document, CASCADE, PULL
from mongoengine.fields import (StringField, DateTimeField, IntField, ListField, ReferenceField,
                                GenericReferenceField, DBRef)
from django.utils.translation import ugettext_lazy as _, ugettext as __

from ....base.utils.dateutils import (timedelta, today, combine,
                                      now, time)  # , make_aware, utc)

from .common import DocumentHelperMixin  # , CACHE_ONE_DAY
from .folder import Folder
from .user import User
from .feed import Feed

LOGGER = logging.getLogger(__name__)

IMPORT_STATUS_CHOICES = (
    (u'P', _(u'Pending')),
    (u'R', _(u'Running')),
    (u'F', _(u'Finished')),
    (u'E', _(u'Error')),
)


@task(name='Import.run', queue='low')
def import_run(import_id):

    import_ = OPMLImport.objects.get(id=import_id)
    return import_.run()


class OPMLImport(Document, DocumentHelperMixin):
    """
    Store a user's OPML import in database until it's processed
    """

    user         = ReferenceField('User', reverse_delete_rule=CASCADE)
    date_created = DateTimeField(default=now)
    date_started = DateTimeField()
    duration     = IntField()
    status       = StringField(max_length=1, choices=IMPORT_STATUS_CHOICES,
                               default=u'P')
    import_type  = StringField(default=u'OPML')
    content      = StringField(default=u'')
    error        = StringField(default=u'')
    obj_created  = ListField(GenericReferenceField())
    task_id      = StringField()

    # A folder under which OPML feeds and folders will be stored
    folder = ReferenceField('Folder', verbose_name=_(u'Parent folder'), required=False)
    meta = {
        'db_alias': 'archive',
    }

    def start(self):
        res = import_run.apply_async((self.id, ), countdown=5)
        self.update(set__task_id=res.id)

    def run(self):

        # parse OPML
        # create feeds if not already
        #   remember already existing for later
        # create subscriptions
        #   use custom feed names in subscriptions if any
        # for each already existing feed
        #   create all reads;                       |
        #       today unread                        | in a new method
        #       all other past read + auto_read     |

        pass
