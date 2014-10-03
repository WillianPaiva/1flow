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

from collections import OrderedDict

from django.db import models
from django.utils.translation import ugettext as _

# from django.utils.translation import ugettext as _
# from django.utils.text import slugify
# from sparks.django.models import ModelDiffMixin
# from oneflow.base.utils.dateutils import now

from common import DjangoUser  # , REDIS
from mailaccount import MailAccount

LOGGER = logging.getLogger(__name__)


class MailFeed(models.Model):

    """ Configuration of a mail-based 1flow feed. """

    name = models.CharField(max_length=255)
    user = models.ForeignKey(DjangoUser)

    class Meta:
        app_label = 'core'

    def __unicode__(self):
        """ OMG, that's __unicode__, pep257. """

        return u'Mail account “{0}” of user {1}'.format(self.name, self.user)


class MailFeedRule(models.Model):

    """ Mail feed rule.

    A mail feed can have one or more rule.

    Each rule can apply to one or more mail accounts.

    If the account is null, the rule will apply to all accounts.
    """

    mailfeed = models.ForeignKey(MailFeed)
    account = models.ForeignKey(MailAccount, null=True)

    class Meta:
        app_label = 'core'

    def __unicode__(self):
        """ OMG, that's __unicode__, pep257. """

        return _(u'Rule #{2}, applied to {0} of mail feed {1}').format(
            _(u'all accounts') if self.account is None
            else _(u'account {0}').format(self.account),
            self.mailfeed, self.id)


class MailFeedRuleLine(models.Model):

    """ Mail feed rule line.

    A rule line is kind of: “match RE xxxxxx on field fffffff”, where
    field can be ``any``, which means that all field will be matched.
    """

    HEADER_FIELD_CHOICES = OrderedDict((
        (u'any', _(u'Any')),
        (u'subject', _(u'Subject')),
        (u'from', _(u'Sender')),
        (u'to', _(u'Receipient (eg. To:, Cc: or Cci:)')),
        (u'list', _(u'Mailing-list')),
        (u'other', _(u'Other header (please type)')),
    ))

    MATCH_TYPE_CHOICES = OrderedDict((
        (u'contains', _(u'contains')),
        (u'ncontains', _(u'does not contain')),
        (u'starts', _(u'starts with')),
        (u'nstarts', _(u'does not start with')),
        (u'ends', _(u'ends with')),
        (u'nends', _(u'does not end with')),
        (u'equals', _(u'strictly equals')),
        (u'nequals', _(u'is not equal to')),
        (u're_match', _(u'Manual regular expression')),
    ))

    rule = models.ForeignKey(MailFeedRule)
    header_field = models.CharField(max_length=10, default=u'any',
                                    choices=tuple(HEADER_FIELD_CHOICES.items()))
    other_header = models.CharField(max_length=255)
    match_type = models.CharField(max_length=10, default=u'contains',
                                  choices=tuple(MATCH_TYPE_CHOICES.items()))
    match_value = models.TextField(max_length=255)

    class Meta:
        app_label = 'core'

    def __unicode__(self):
        """ OMG, that's __unicode__, pep257. """

        return _(u'Rule line {1} {2} {3} of rule #{4}').format(
            self.other_header
            if self.header_field == u'other'
            else self.header_field,
            self.match_type,
            self.match_value,
            self.rule.id
        )
