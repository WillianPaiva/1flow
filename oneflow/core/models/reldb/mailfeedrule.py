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
import re
import logging
import operator

from collections import OrderedDict
from positions import PositionField

from django.db import models
from django.utils.translation import ugettext_lazy as _

# from mptt.models import MPTTModel, TreeForeignKey

# from django.utils.translation import ugettext as _
# from django.utils.text import slugify
# from sparks.django.models import ModelDiffMixin
# from oneflow.base.utils.dateutils import now

from sparks.django.models import ModelDiffMixin

import mail_common as common
from mailaccount import MailAccount
from mailfeed import MailFeed

LOGGER = logging.getLogger(__name__)


class MailFeedRule(ModelDiffMixin):

    """ Mail feed rule.

    A mail feed can have one or more rule.

    Each rule can apply to one or more mail accounts.

    If the account is null, the rule will apply to all accounts.
    """

    INPLACEEDIT_PARENTCHAIN = ('mailfeed', )

    HEADER_FIELD_CHOICES = OrderedDict((
        (u'subject', _(u'Subject')),
        (u'from', _(u'Sender')),
        (u'to', _(u'Recipient (To:, Cc: or Bcc:)')),
        (u'list', _(u'Mailing-list')),
        (u'other', _(u'Other header (please specify)')),
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
        (u're_match', _(u'matches regular expression')),
        (u'nre_match', _(u'does not match reg. expr.')),
    ))

    group = models.IntegerField(verbose_name=_(u'Rules group'),
                                null=True, blank=True)

    group_operation =  models.CharField(
        verbose_name=_(u'Rules group operation'),
        max_length=10, default=u'any', blank=True, null=True,
        choices=tuple(MailFeed.RULES_OPERATION_CHOICES.items()),
        help_text=_(u'Condition between rules of this group.'))

    mailfeed = models.ForeignKey(MailFeed)
    account = models.ForeignKey(MailAccount, null=True, blank=True,
                                verbose_name=_(u'Mail account'),
                                help_text=_(u"To apply this rule to all "
                                            u"accounts, just don't choose "
                                            u"any."))
    mailbox = models.CharField(verbose_name=_(u'Mailbox'),
                               max_length=255, default=u'INBOX',
                               null=True, blank=True)
    recurse_mailbox = models.BooleanField(verbose_name=_(u'Recurse mailbox'),
                                          default=True, blank=True)
    header_field = models.CharField(verbose_name=_(u'Header'),
                                    max_length=10, default=u'any',
                                    choices=tuple(HEADER_FIELD_CHOICES.items()),
                                    help_text=_(u"E-mail field on which the "
                                                u"match type is applied."))
    other_header = models.CharField(verbose_name=_(u'Other header'),
                                    max_length=255, null=True, blank=True,
                                    help_text=_(u"Specify here if you chose "
                                                u"“Other header” in previous "
                                                u"field."))
    match_type = models.CharField(verbose_name=_(u'Match type'),
                                  max_length=10, default=u'contains',
                                  choices=tuple(MATCH_TYPE_CHOICES.items()),
                                  help_text=_(u"Operation applied on the "
                                              u"header to compare with match "
                                              u"value."))
    match_case = models.BooleanField(verbose_name=_(u'Match case'),
                                     default=False, blank=True,
                                     help_text=_(u"Do we care about uppercase "
                                                 u"and lowercase characters?"))
    match_value = models.CharField(verbose_name=_(u'Match value'),
                                   default=u'', max_length=1024,
                                   help_text=_(u"Examples: “Tweet de”, "
                                               u"“Google Alert:”. Can be "
                                               u"any text."))

    match_action = models.CharField(
        verbose_name=_(u'Action when matched'),
        max_length=10, null=True, blank=True,
        choices=tuple(MailFeed.MATCH_ACTION_CHOICES.items()),
        help_text=_(u'Choose nothing to execute '
                    u'action defined at the feed level.'))

    finish_action =  models.CharField(
        verbose_name=_(u'Finish action'),
        max_length=10, null=True, blank=True,
        choices=tuple(MailFeed.FINISH_ACTION_CHOICES.items()),
        help_text=_(u'Choose nothing to execute '
                    u'action defined at the feed level.'))

    # Used to have many times the same rule in different feeds
    clone_of = models.ForeignKey('MailFeedRule', null=True, blank=True)
    position = PositionField(collection=('mailfeed', 'group', ),
                             default=0, blank=True)
    is_valid = models.BooleanField(verbose_name=_(u'Checked and valid'),
                                   default=True, blank=True)
    check_error = models.CharField(max_length=255, default=u'', blank=True)

    class Meta:
        app_label = 'core'
        ordering = ('group', 'position', )

    @property
    def operation(self):
        """ Return a Python function doing the operation of the rule.

        Cache it in an attribute to avoid redoing all the work each time
        this property is called, because in many cases the rule will be
        called more than once (on multiple messages of multiple mailboxes).
        """

        try:
            return self._operation_

        except AttributeError:

            def mymethodcaller(name):
                def caller(a, b):
                    return getattr(a, name)(b)

                return caller

            def ncontains(a, b):
                return not operator.contains(a, b)

            def nstarts(a, b):
                return not a.startswith(b)

            def nends(a, b):
                return not a.endswith(b)

            if self.match_type in (u're_match', u'nre_match'):
                # The .lower() should work also with the RE. It
                # should even be faster than a standard /I match().
                compiled_re = re.compile(self.match_value
                                         if self.match_case
                                         else self.match_value.lower())

            def re_match(a, b):
                """ :param:`b` is ignored, it's here for call compat only. """

                return bool(compiled_re.match(a))

            def nre_match(a, b):
                return not re_match(a, b)

            OPERATIONS = {
                u'contains': operator.contains,
                u'ncontains': ncontains,
                u'starts': mymethodcaller('startswith'),
                u'nstarts': nstarts,
                u'ends': mymethodcaller('endswith'),
                u'nends': nends,
                u'equals': operator.eq,
                u'nequals': operator.ne,
                u're_match': re.match,
                u'nre_match': nre_match,
            }

            self._operation_ = OPERATIONS[self.match_type]

            return self._operation_

    # —————————————————————————————————————————————————————————————————— Django

    def __unicode__(self):
        """ OMG, that's __unicode__, pep257. """

        return _(u'Rule #{2}: {3}, applied to {0} for MailFeed {1}').format(
            _(u'all accounts') if self.account is None
            else _(u'account {0}').format(self.account),
            self.mailfeed,
            self.id,
            _(u'{0} {1} “{2}” → {3} → {4}').format(
                self.other_header
                if self.header_field == u'other'
                else self.HEADER_FIELD_CHOICES[self.header_field],
                self.MATCH_TYPE_CHOICES[self.match_type],
                self.match_value,
                MailFeed.MATCH_ACTION_CHOICES.get(self.match_action,
                                                  _(u'feed default')),
                MailFeed.FINISH_ACTION_CHOICES.get(self.finish_action,
                                                   _(u'feed default')),
            ))

    def save(self, *args, **kwargs):
        """ Check the rule is valid before saving. """

        changed_fields = self.changed_fields

        if 'header_field' in changed_fields \
            or 'other_header' in changed_fields \
            or 'match_type' in changed_fields \
                or'match_value' in changed_fields:

            self.check_is_valid(commit=False)

        super(MailFeedRule, self).save(*args, **kwargs)

    # ——————————————————————————————————————————————————————————————— Internals

    def check_is_valid(self, commit=True):
        """ TODO: implement this. """

        is_valid = True

        if self.header_field == u'other':
            other = self.other_header

            if other.strip().endswith(':'):
                self.other_header = other = other.strip()[:-1]

            if other.lower() not in common.OTHER_VALID_HEADERS_lower:
                is_valid = False
                self.check_error = _(u'Unrecognized header name “{0}”. Please '
                                     u'look at http://bit.ly/smtp-headers '
                                     u'to find a list of valid headers. '
                                     u'Perhaps just a typo?').format(other)

        if self.match_type in (u're_match', u'nre_match'):
            try:
                re.compile(self.match_value)

            except Exception as e:
                is_valid = False
                self.check_error = _(u'Invalid regular expression “{0}”: '
                                     u'{1}').format(self.match_value,
                                                    unicode(e))

        if is_valid != self.is_valid:
            self.is_valid = is_valid

            if is_valid and self.check_error:
                self.check_error = u''

            if commit:
                self.save()

    def match_message(self, message):
        """ Return ``True`` if :param:`message` matches the current rule. """

        def match_header(header, value):
            if not self.match_case:
                header = header.lower()

            return self.operation(header, value)

        HEADERS = common.BASE_HEADERS.copy()
        HEADERS[u'other'] = self.other_header

        if self.match_case:
            value = self.match_value

        else:
            # HEADS UP: we don't care for the RE; the
            # second parameter in that case is ignored.
            value = self.match_value.lower()

        for header_name in HEADERS[self.header_field]:
            header = message.get(header_name, '')

            if isinstance(header, list) or isinstance(header, tuple):
                if len(header) > 2:
                    for header_part in header:
                        if isinstance(header, list) \
                                or isinstance(header, tuple):
                            header = u'{0} {1}'.format(*header_part)

                            if match_header(header, value):
                                return True

                        else:
                            if match_header(header_part, value):
                                return True

                else:
                    if header[1].startswith(u'<'):
                        # Here we've got [u'Olivier Cortès', '<oc@1flow.io>']
                        # it's the same person; one test.

                        header = u'{0} {1}'.format(*header)

                        if match_header(header, value):
                            return True

                    else:
                        # There we've got [u'Toto <n@t.com>', u'Tutu <m@t.com>']
                        # They are 2 different persons and 2 tests.

                        for header_part in header:
                            if match_header(header_part, value):
                                return True
            else:
                if match_header(header, value):
                    return True

        return False
