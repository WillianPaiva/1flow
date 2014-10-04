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

        return u'“{0}” of user {1}'.format(self.name, self.user)


class MailFeedRule(models.Model):

    """ Mail feed rule.

    A mail feed can have one or more rule.

    Each rule can apply to one or more mail accounts.

    If the account is null, the rule will apply to all accounts.
    """

    INPLACEEDIT_PARENTCHAIN = ('mailfeed', )

    HEADER_FIELD_CHOICES = OrderedDict((
        (u'any', _(u'Any')),
        (u'subject', _(u'Subject')),
        (u'from', _(u'Sender')),
        (u'to', _(u'Receipient (eg. To:, Cc: or Cci:)')),
        (u'list', _(u'Mailing-list')),
        (u'other', _(u'Other header (please type)')),
    ))

    MAILBOX_CHOICES = OrderedDict((
        (u'', _(u'All')),
        (u'INBOX', _(u'Inbox')),
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

    MATCH_ACTION_CHOICES = OrderedDict((
        (u'store', _(u'store email')),
        (u'scrap', _(u'scrap email body')),
    ))

    mailfeed = models.ForeignKey(MailFeed)
    account = models.ForeignKey(MailAccount, null=True, blank=True)
    # mailbox = models.CharField(max_length=255, default=u'INBOX',
    #                           choices=tuple(MAILBOX_CHOICES.items()))
    header_field = models.CharField(max_length=10, default=u'any',
                                    choices=tuple(HEADER_FIELD_CHOICES.items()))
    other_header = models.CharField(max_length=255, null=True, blank=True)
    match_type = models.CharField(max_length=10, default=u'contains',
                                  choices=tuple(MATCH_TYPE_CHOICES.items()))
    match_value = models.CharField(default=u'', max_length=1024)

    match_action = models.CharField(max_length=10, default=u'store',
                                    choices=tuple(MATCH_ACTION_CHOICES.items()))

    #
    # HEADS UP: 20141004, these fields are not used yet in the engine.
    #
    scrap_refine = models.CharField(null=True, blank=True, max_length=1024,
                                    help_text=_(u'Eventually refine URLs you '
                                                u'want to scrap in the email '
                                                u'body. Type a list of valid '
                                                u'URLs patterns, and start '
                                                u'with “re:” if you want to '
                                                u'use a regular expression.'))

    scrap_adblock = models.BooleanField(default=True, blank=True,
                                        help_text=_(u'Use 1flow adblocker to '
                                                    u'avoid scrapping email '
                                                    u'adds.'))

    # Used to have many times the same rule in different feeds
    clone_of = models.ForeignKey('MailFeedRule', null=True, blank=True)

    class Meta:
        app_label = 'core'

    def __unicode__(self):
        """ OMG, that's __unicode__, pep257. """

        return _(u'Rule #{2}: {3}, applied to {0} for MailFeed {1}').format(
            _(u'all accounts') if self.account is None
            else _(u'account {0}').format(self.account),
            self.mailfeed,
            self.id,
            _(u'{0} {1} “{2}” → {3}').format(
                self.other_header
                if self.header_field == u'other'
                else self.HEADER_FIELD_CHOICES[self.header_field],
                self.MATCH_TYPE_CHOICES[self.match_type],
                self.match_value,
                self.MATCH_ACTION_CHOICES[self.match_action]
            ))
