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

from twitter import TwitterFeed
from common import (
    RULES_OPERATIONS,

    TWITTER_MATCH_TYPES,
    TWITTER_MATCH_FIELDS,
    TWITTER_RULES_OPERATIONS,

    TWITTER_MATCH_TYPE_DEFAULT,
    TWITTER_MATCH_FIELD_DEFAULT,
    TWITTER_GROUP_OPERATION_DEFAULT,
)


LOGGER = logging.getLogger(__name__)


class TwitterFeedRule(ModelDiffMixin):

    """ Twitter feed rule.

    A twitter feed can have one or more rule.

    Each rule can apply to one or more twitter accounts.

    If the account is null, the rule will apply to all accounts.
    """

    class Meta:
        app_label = 'core'
        verbose_name = _(u'Twitter feed rule')
        verbose_name_plural = _(u'Twitter feed rules')
        ordering = ('group', 'position', )

    INPLACEEDIT_PARENTCHAIN = ('twitterfeed', )

    twitterfeed = models.ForeignKey(TwitterFeed, related_name='rules')

    group = models.IntegerField(verbose_name=_(u'Rules group'),
                                null=True, blank=True)

    group_operation = models.IntegerField(
        verbose_name=_(u'Rules group operation'),
        default=TWITTER_GROUP_OPERATION_DEFAULT, blank=True,
        choices=TWITTER_RULES_OPERATIONS.get_choices(),
        help_text=_(u'Condition between rules of this group.')
    )

    match_field = models.IntegerField(
        verbose_name=_(u'Field'),
        default=TWITTER_MATCH_FIELD_DEFAULT, blank=True,
        choices=TWITTER_MATCH_FIELDS.get_choices(),
        help_text=_(u"E-twitter field on which the match type is performed.")
    )

    match_type = models.IntegerField(
        verbose_name=_(u'Match type'),
        default=TWITTER_MATCH_TYPE_DEFAULT, blank=True,
        choices=TWITTER_MATCH_TYPES.get_choices(),
        help_text=_(u"Operation applied on the field "
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
    # This information is already in the twitterfeed.
    #
    # match_action = models.CharField(
    #     verbose_name=_(u'Action when matched'),
    #     max_length=10, null=True, blank=True,
    #     choices=tuple(TwitterFeed.MATCH_ACTION_CHOICES.items()),
    #     help_text=_(u'Choose nothing to execute '
    #                 u'action defined at the feed level.'))
    #
    # finish_action =  models.CharField(
    #     verbose_name=_(u'Finish action'),
    #     max_length=10, null=True, blank=True,
    #     choices=tuple(TwitterFeed.FINISH_ACTION_CHOICES.items()),
    #     help_text=_(u'Choose nothing to execute '
    #                 u'action defined at the feed level.'))
    #

    other_field = models.CharField(
        verbose_name=_(u'Other field'),
        max_length=255, null=True, blank=True,
        help_text=_(u"Specify here if you chose “Other field” "
                    u"in previous field.")
    )

    # Used to have many times the same rule in different feeds
    clone_of = models.ForeignKey('TwitterFeedRule', null=True, blank=True)

    position = PositionField(collection=('twitterfeed', 'group', ),
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
        called more than once (on multiple messages of multiple twitterboxes).
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

            if self.match_type in (TWITTER_MATCH_TYPES.RE_MATCH,
                                   TWITTER_MATCH_TYPES.NRE_MATCH):
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
                TWITTER_MATCH_TYPES.CONTAINS: operator.contains,
                TWITTER_MATCH_TYPES.NCONTAINS: ncontains,
                TWITTER_MATCH_TYPES.STARTS: mymethodcaller('startswith'),
                TWITTER_MATCH_TYPES.NSTARTS: nstarts,
                TWITTER_MATCH_TYPES.ENDS: mymethodcaller('endswith'),
                TWITTER_MATCH_TYPES.NENDS: nends,
                TWITTER_MATCH_TYPES.EQUALS: operator.eq,
                TWITTER_MATCH_TYPES.NEQUALS: operator.ne,
                TWITTER_MATCH_TYPES.RE_MATCH: re.match,
                TWITTER_MATCH_TYPES.NRE_MATCH: nre_match,
            }

            self._operation_ = OPERATIONS[self.match_type]

            return self._operation_

    # —————————————————————————————————————————————————————————————————— Django

    def __unicode__(self):
        """ OMG, that's __unicode__, pep257. """

        return _(u'Rule #{0}: {2} for TwitterFeed {1}').format(
            self.id,
            self.twitterfeed,
            _(u'{0} {1} “{2}”').format(
                self.other_field
                if self.match_field == u'other'
                else TWITTER_MATCH_FIELDS[self.match_field],
                TWITTER_MATCH_TYPES[self.match_type],
                self.match_value,
                # TwitterFeed.MATCH_ACTION_CHOICES.get(self.match_action,
                #                                   _(u'feed default')),
                # TwitterFeed.FINISH_ACTION_CHOICES.get(self.finish_action,
                #                                    _(u'feed default')),
            ))

    def repr_for_json(self):
        """ Return our attributes in a JSON-compatible form. """

        return {
            'id': self.id,
            'group': self.group,
            'group_operation': self.group_operation,
            'position': self.position,

            'match_field': self.match_field,
            'other_field': self.other_field,
            'match_type': self.match_type,
            'match_value': self.match_value,
        }

    def save(self, *args, **kwargs):
        """ Check the rule is valid before saving. """

        changed_fields = self.changed_fields

        if 'match_field' in changed_fields \
            or 'other_field' in changed_fields \
            or 'match_type' in changed_fields \
                or'match_value' in changed_fields:

            self.check_is_valid(commit=False)

        super(TwitterFeedRule, self).save(*args, **kwargs)

    # ——————————————————————————————————————————————————————————————— Internals

    def check_is_valid(self, commit=True):
        """ Check if the rule is appliable or not, and mark it as such. """

        return True

        raise NotImplementedError('Impletment TwitterRule.check_is_valid')

        is_valid = True

        if self.match_field == TWITTER_MATCH_FIELDS.OTHER:
            other = self.other_field

            if other.strip().endswith(':'):
                self.other_field = other = other.strip()[:-1]

            if other.lower() not in OTHER_VALID_HEADERS_lower:
                is_valid = False
                self.check_error = _(u'Unrecognized field name “{0}”. Please '
                                     u'look at http://bit.ly/smtp-fields '
                                     u'to find a list of valid fields. '
                                     u'Perhaps just a typo?').format(other)

        if self.match_type in (TWITTER_MATCH_TYPES.RE_MATCH,
                               TWITTER_MATCH_TYPES.NRE_MATCH):
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

        rules_group = self.twitterfeed.rules.filter(group=self.group)

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

        def match_field(field, value):
            if not self.match_case:
                field = field.lower()

            return self.operation(field, value)

        HEADERS = BASE_HEADERS.copy()
        HEADERS[u'other'] = self.other_field

        #
        # TODO: implement body searching.
        #

        if self.match_case:
            value = self.match_value

        else:
            # HEADS UP: we don't care for the RE; the
            # second parameter in that case is ignored.
            value = self.match_value.lower()

        for field_name in HEADERS[self.match_field]:
            field = message.get(field_name, u'')

            if isinstance(field, list) or isinstance(field, tuple):
                if len(field) > 2:
                    for field_part in field:
                        if isinstance(field, list) \
                                or isinstance(field, tuple):
                            field = u'{0} {1}'.format(*field_part)

                            if match_field(field, value):
                                return True

                        else:
                            if match_field(field_part, value):
                                return True

                else:
                    if field[1].startswith(u'<'):
                        # Here we've got [u'Olivier Cortès', '<oc@1flow.io>']
                        # it's the same person; one test.

                        field = u'{0} {1}'.format(*field)

                        if match_field(field, value):
                            return True

                    else:
                        # There we've got [u'Toto <n@t.com>', u'Tutu <m@t.com>']
                        # They are 2 different persons and 2 tests.

                        for field_part in field:
                            if match_field(field_part, value):
                                return True
            else:
                if match_field(field, value):
                    return True

        return False
