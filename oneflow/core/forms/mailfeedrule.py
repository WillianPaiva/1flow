# -*- coding: utf-8 -*-
u"""
Copyright 2013-2014 Olivier Cortès <oc@1flow.io>.

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

import random
import logging

from constance import config

from django import forms
from django.utils.translation import ugettext as _

from ..models import MailAccount, MailFeedRule
from ..models.reldb.feed.common import (
    MAIL_RULES_OPERATIONS,
    MAIL_RULES_OPERATION_DEFAULT,
)

from oneflow.base.utils import get_common_values

LOGGER = logging.getLogger(__name__)


class GroupedMailboxChoiceField(forms.ChoiceField):

    """ Artificially group mailboxes. Common ones, then for each account.

    Reference: https://djangosnippets.org/snippets/1968/
    """

    def __init__(self, *args, **kwargs):
        """ Initialize the choices with a MailAccount queryset. """

        self.queryset = kwargs.pop('queryset')

        LOGGER.info('GroupedMailboxChoiceField init with %s', self.queryset)

        super(GroupedMailboxChoiceField, self).__init__(*args, **kwargs)

    def _get_choices(self):
        """ Exactly the same as ChoiceField, except returns new iterator. """

        LOGGER.info('GroupedMailboxChoiceField get choices 1')

        if hasattr(self, '_choices'):
            return self._choices

        LOGGER.info('GroupedMailboxChoiceField get choices 2')

        return self.__iter__

    choices = property(_get_choices, forms.ChoiceField._set_choices)

    def __iter__(self):
        """ Iterate mailboxes grouped. """

        LOGGER.info('GroupedMailboxChoiceField ITER with: %s', self.queryset)

        mailboxes_by_account = {
            # Get a copy of mailboxes list so we can update them.
            account: account.mailboxes[:]
            for account in self.queryset.all()
        }

        common_names = get_common_values(
            mailboxes_by_account,
            (cmb[0] for cmb in MailAccount.MAILBOXES_COMMON)
        )

        yield (_(u'Common'), MailAccount.MAILBOXES_COMMON
               + ((mbn, mbn) for mbn in common_names))

        for account, mailboxes in mailboxes_by_account:
            yield (account, [(mbn, mbn) for mbn in mailboxes])


class MailFeedRuleForm(forms.ModelForm):

    """ A simple mail feed rule model form. """

    def __init__(self, *args, **kwargs):
        """ Hey pep257, that's an init method. """

        # Not completely implemented yet
        _dummy_ = kwargs.pop('user')
        _dummy_

        super(MailFeedRuleForm, self).__init__(*args, **kwargs)

        # self.fields['mailbox'] = GroupedMailboxChoiceField(
        #     queryset=MailAccount.objects.filter(user=user))
        # self.fields['mailbox'] = forms.ChoiceField(
        #     choices=MailAccount.MAILBOXES_COMMON.items())

    class Meta:
        model = MailFeedRule
        fields = ('header_field', 'other_header',
                  'match_type', 'match_value', )


class MailFeedRulePositionForm(forms.ModelForm):

    """ A mail feed rule model form to update its position in list. """

    class Meta:
        model = MailFeedRule
        fields = ('position', )


class MailFeedRuleGroupForm(forms.ModelForm):

    """ A mail feed rule model form to update its group. """

    merge_with = forms.ModelChoiceField(queryset=MailFeedRule.objects.none(),
                                        required=False)
    split = forms.BooleanField(required=False)

    switch = forms.BooleanField(required=False)

    class Meta:
        model = MailFeedRule
        fields = ()

    def __init__(self, *args, **kwargs):
        """ Refine the ``merge_with`` QS to the current mailfeed's rules. """

        super(MailFeedRuleGroupForm, self).__init__(*args, **kwargs)

        self.fields['merge_with'].queryset = MailFeedRule.objects.filter(
            mailfeed=self.instance.mailfeed)

    def save(self):
        """ Do the merge/split operation silently and automatically. """

        def get_random_number(exclude_from):

            while 1:
                number = random.randint(1, max_val)

                if number not in exclude_from:
                    return number

        super(MailFeedRuleGroupForm, self).save()

        instance = self.instance
        merge_with = self.cleaned_data['merge_with']
        split = self.cleaned_data['split']
        switch = self.cleaned_data['switch']

        if split is True:
            group = instance.group

            instance.group = None
            instance.group_operation = MAIL_RULES_OPERATION_DEFAULT
            instance.save()

            try:
                remaining = self.fields['merge_with'].queryset.get(group=group)

            except MailFeedRule.MultipleObjectsReturned:
                # Still more than one remaining. Leave
                # them untouched, they are still a group.
                pass

            else:
                remaining.group = None
                remaining.group_operation = MAIL_RULES_OPERATION_DEFAULT
                remaining.save()

        elif switch is True:
            operation = instance.group_operation

            operations = [x[0] for x in MAIL_RULES_OPERATIONS.get_choices()]

            next_operation = operations[
                (operations.index(operation) + 1) % len(operations)
            ]

            self.fields['merge_with'].queryset.filter(
                group=instance.group).update(group_operation=next_operation)

        else:
            if merge_with.group is None:
                # create a random group number

                max_val = abs(config.MAIL_RULES_GROUPS_MAX) * 3

                exclude_from = [self.fields['merge_with'].queryset.distinct(
                                'group').values_list('group', flat=True)]

                try:
                    exclude_from.remove(None)

                except:
                    pass

                merge_with.group = instance.group = \
                    get_random_number(exclude_from)
                merge_with.group_operation = instance.group_operation = \
                    MAIL_RULES_OPERATION_DEFAULT

            else:
                # we are merging with an existing group

                instance.group = merge_with.group
                instance.group_operation = merge_with.group_operation

            merge_with.save()
            instance.save()
