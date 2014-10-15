# -*- coding: utf-8 -*-
"""
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

import logging

# from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
# from django.db.models.signals import pre_save, post_save, pre_delete

from sparks.django.models import ModelDiffMixin

# from django.utils.translation import ugettext as _
# from django.utils.text import slugify

from ..common import DjangoUser  # , REDIS
# from mail_common import email_get_first_text_block

LOGGER = logging.getLogger(__name__)


class CombinedFeed(ModelDiffMixin):

    """ An aggregate of other feed types, including itself. """

    name = models.CharField(max_length=255, verbose_name=_(u'Feed name'))
    user = models.ForeignKey(DjangoUser, verbose_name=_(u'Creator'))
    is_restricted = models.BooleanField(verbose_name=_(u'Restricted'),
                                        default=False, blank=True,
                                        help_text=_(u'Can other 1flow users '
                                                    u'subscribe to this feed?'))

    class Meta:
        app_label = 'core'

    # —————————————————————————————————————————————————————————————————— Django

    def __unicode__(self):
        """ OMG, that's __unicode__, pep257. """

        return u'“{0}” of user {1}'.format(self.name, self.user)
