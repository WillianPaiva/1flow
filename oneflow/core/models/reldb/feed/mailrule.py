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
import re
import logging
import operator

from positions import PositionField

from django.db import models
from django.utils.translation import ugettext_lazy as _

# from mptt.models import MPTTModel, TreeForeignKey

# from django.utils.translation import ugettext as _
# from django.utils.text import slugify
# from sparks.django.models import ModelDiffMixin
# from oneflow.base.utils.dateutils import now

from sparks.django.models.mixins import ModelDiffMixin

from ..account.common import OTHER_VALID_HEADERS_lower, BASE_HEADERS

from mail import MailFeed
from common import (
    RULES_OPERATIONS,

    MAIL_MATCH_TYPES,
    MAIL_HEADER_FIELDS,
    MAIL_RULES_OPERATIONS,

    MAIL_MATCH_TYPE_DEFAULT,
    MAIL_HEADER_FIELD_DEFAULT,
    MAIL_GROUP_OPERATION_DEFAULT,
)


LOGGER = logging.getLogger(__name__)


class MailFeedRule(ModelDiffMixin):

    """ Mail feed rule.

    A mail feed can have one or more rule.

    Each rule can apply to one or more mail accounts.

    If the account is null, the rule will apply to all accounts.
    """

    class Meta:
        app_label = 'core'
        verbose_name = _(u'Mail feed rule')
        verbose_name_plural = _(u'Mail feed rules')
        ordering = ('group', 'position', )

    INPLACEEDIT_PARENTCHAIN = ('mailfeed', )

    mailfeed = models.ForeignKey(MailFeed, related_name='rules')

    group = models.IntegerField(verbose_name=_(u'Rules group'),
                                null=True, blank=True)

    group_operation = models.IntegerField(
        verbose_name=_(u'Rules group operation'),
        default=MAIL_GROUP_OPERATION_DEFAULT, blank=True,
        choices=MAIL_RULES_OPERATIONS.get_choices(),
        help_text=_(u'Condition between rules of this group.')
    )

    header_field = models.IntegerField(
        verbose_name=_(u'Header'),
        default=MAIL_HEADER_FIELD_DEFAULT, blank=True,
        choices=MAIL_HEADER_FIELDS.get_choices(),
        help_text=_(u"E-mail field on which the match type is performed.")
    )

    match_type = models.IntegerField(
        verbose_name=_(u'Match type'),
        default=MAIL_MATCH_TYPE_DEFAULT, blank=True,
        choices=MAIL_MATCH_TYPES.get_choices(),
        help_text=_(u"Operation applied on the header "
                    u"to compare with match value.")
    )

    match_case = models.BooleanField(
        verbose_name=_(u'Match case'),
        default=False, blank=True,
        help_text=_(u"Do we care about uppercase and lowercase characters?")
    )

    match_value = models.CharField(
        verbose_name=_(u'Match value'),
        max_length=1024, null=True, blank=True,
        help_text=_(u"Examples: “Tweet from”, “Google Alert:”. "
                    u"Can be any text."))
    #
    # De-activated, considered too complex to handle.
    # This information is already in the mailfeed.
    #
    # match_action = models.CharField(
    #     verbose_name=_(u'Action when matched'),
    #     max_length=10, null=True, blank=True,
    #     choices=tuple(MailFeed.MATCH_ACTION_CHOICES.items()),
    #     help_text=_(u'Choose nothing to execute '
    #                 u'action defined at the feed level.'))
    #
    # finish_action =  models.CharField(
    #     verbose_name=_(u'Finish action'),
    #     max_length=10, null=True, blank=True,
    #     choices=tuple(MailFeed.FINISH_ACTION_CHOICES.items()),
    #     help_text=_(u'Choose nothing to execute '
    #                 u'action defined at the feed level.'))
    #

    other_header = models.CharField(
        verbose_name=_(u'Other header'),
        max_length=255, null=True, blank=True,
        help_text=_(u"Specify here if you chose “Other header” "
                    u"in previous field.")
    )

    # Used to have many times the same rule in different feeds
    clone_of = models.ForeignKey('MailFeedRule', null=True, blank=True)

    position = PositionField(collection=('mailfeed', 'group', ),
                             default=0, blank=True)

    is_valid = models.BooleanField(verbose_name=_(u'Checked and valid'),
                                   default=True, blank=True)

    check_error = models.CharField(max_length=255, null=True, blank=True)

    # —————————————————————————————————————————————————————————————— Properties

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

            if self.match_type in (MAIL_MATCH_TYPES.RE_MATCH,
                                   MAIL_MATCH_TYPES.NRE_MATCH):
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
                MAIL_MATCH_TYPES.CONTAINS: operator.contains,
                MAIL_MATCH_TYPES.NCONTAINS: ncontains,
                MAIL_MATCH_TYPES.STARTS: mymethodcaller('startswith'),
                MAIL_MATCH_TYPES.NSTARTS: nstarts,
                MAIL_MATCH_TYPES.ENDS: mymethodcaller('endswith'),
                MAIL_MATCH_TYPES.NENDS: nends,
                MAIL_MATCH_TYPES.EQUALS: operator.eq,
                MAIL_MATCH_TYPES.NEQUALS: operator.ne,
                MAIL_MATCH_TYPES.RE_MATCH: re.match,
                MAIL_MATCH_TYPES.NRE_MATCH: nre_match,
            }

            self._operation_ = OPERATIONS[self.match_type]

            return self._operation_

    # —————————————————————————————————————————————————————————————————— Django

    def __unicode__(self):
        """ OMG, that's __unicode__, pep257. """

        return _(u'Rule #{0}: {2} for MailFeed {1}').format(
            self.id,
            self.mailfeed,
            _(u'{0} {1} “{2}”').format(
                self.other_header
                if self.header_field == u'other'
                else MAIL_HEADER_FIELDS[self.header_field],
                MAIL_MATCH_TYPES[self.match_type],
                self.match_value,
                # MailFeed.MATCH_ACTION_CHOICES.get(self.match_action,
                #                                   _(u'feed default')),
                # MailFeed.FINISH_ACTION_CHOICES.get(self.finish_action,
                #                                    _(u'feed default')),
            ))

    def repr_for_json(self):
        """ Return our attributes in a JSON-compatible form. """

        return {
            'id': self.id,
            'group': self.group,
            'group_operation': self.group_operation,
            'position': self.position,

            'header_field': self.header_field,
            'other_header': self.other_header,
            'match_type': self.match_type,
            'match_value': self.match_value,
        }

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
        """ Check if the rule is appliable or not, and mark it as such. """

        is_valid = True

        if self.header_field == MAIL_HEADER_FIELDS.OTHER:
            other = self.other_header

            if other.strip().endswith(':'):
                self.other_header = other = other.strip()[:-1]

            if other.lower() not in OTHER_VALID_HEADERS_lower:
                is_valid = False
                self.check_error = _(u'Unrecognized header name “{0}”. Please '
                                     u'look at http://bit.ly/smtp-headers '
                                     u'to find a list of valid headers. '
                                     u'Perhaps just a typo?').format(other)

        if self.match_type in (MAIL_MATCH_TYPES.RE_MATCH,
                               MAIL_MATCH_TYPES.NRE_MATCH):
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
        """ True if :param:`message` matches the current rule or its group. """

        if self.group:
            return self.match_message_in_group(message)

        else:
            return self.match_message_individual(message)

    def match_message_in_group(self, message):
        """ Return True if our rule group says so. """

        operation_any = self.group_operation == RULES_OPERATIONS.ANY
        operation_all = not operation_any

        rules_group = self.mailfeed.rules.filter(group=self.group)

        for rule in rules_group:

            if rule.match_message_individual(message):
                if operation_any:
                    # First match makes the group be true.
                    return True

            else:
                if operation_all:
                    # First non-match kills the group.
                    return False

        # OK, this is kind of a nice shortcut.
        return operation_all

    def match_message_individual(self, message):
        """ Test message against the current rule, member of a group or not. """

        def match_header(header, value):
            if not self.match_case:
                header = header.lower()

            return self.operation(header, value)

        HEADERS = BASE_HEADERS.copy()
        HEADERS[u'other'] = self.other_header

        #
        # TODO: implement body searching.
        #

        if self.match_case:
            value = self.match_value

        else:
            # HEADS UP: we don't care for the RE; the
            # second parameter in that case is ignored.
            value = self.match_value.lower()

        for header_name in HEADERS[self.header_field]:
            header = message.get(header_name, u'')

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
