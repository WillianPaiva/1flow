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

from ..models import TwitterAccount, TwitterFeedRule

from ..models.reldb.feed.common import (
    TWITTER_RULES_OPERATIONS,
    TWITTER_RULES_OPERATION_DEFAULT,
)

LOGGER = logging.getLogger(__name__)


class TwitterFeedRuleForm(forms.ModelForm):

    """ A simple twitter feed rule model form. """

    def __init__(self, *args, **kwargs):
        """ Hey pep257, that's an init method. """

        # Not completely implemented yet
        _dummy_ = kwargs.pop('user')
        _dummy_

        super(TwitterFeedRuleForm, self).__init__(*args, **kwargs)

        # self.fields['twitterbox'] = GroupedMailboxChoiceField(
        #     queryset=TwitterAccount.objects.filter(user=user))
        # self.fields['twitterbox'] = forms.ChoiceField(
        #     choices=TwitterAccount.MAILBOXES_COMMON.items())

    class Meta:
        model = TwitterFeedRule
        fields = ('match_field', 'match_type', 'match_value', )


class TwitterFeedRulePositionForm(forms.ModelForm):

    """ A twitter feed rule model form to update its position in list. """

    class Meta:
        model = TwitterFeedRule
        fields = ('position', )


class TwitterFeedRuleGroupForm(forms.ModelForm):

    """ A twitter feed rule model form to update its group. """

    merge_with = forms.ModelChoiceField(queryset=TwitterFeedRule.objects.none(),
                                        required=False)
    split = forms.BooleanField(required=False)

    switch = forms.BooleanField(required=False)

    class Meta:
        model = TwitterFeedRule
        fields = ()

    def __init__(self, *args, **kwargs):
        """ Refine the ``merge_with`` QS to the current twitterfeed's rules. """

        super(TwitterFeedRuleGroupForm, self).__init__(*args, **kwargs)

        self.fields['merge_with'].queryset = TwitterFeedRule.objects.filter(
            twitterfeed=self.instance.twitterfeed)

    def save(self):
        """ Do the merge/split operation silently and automatically. """

        def get_random_number(exclude_from):

            while 1:
                number = random.randint(1, max_val)

                if number not in exclude_from:
                    return number

        super(TwitterFeedRuleGroupForm, self).save()

        instance = self.instance
        merge_with = self.cleaned_data['merge_with']
        split = self.cleaned_data['split']
        switch = self.cleaned_data['switch']

        if split is True:
            group = instance.group

            instance.group = None
            instance.group_operation = TWITTER_RULES_OPERATION_DEFAULT
            instance.save()

            try:
                remaining = self.fields['merge_with'].queryset.get(group=group)

            except TwitterFeedRule.MultipleObjectsReturned:
                # Still more than one remaining. Leave
                # them untouched, they are still a group.
                pass

            else:
                remaining.group = None
                remaining.group_operation = TWITTER_RULES_OPERATION_DEFAULT
                remaining.save()

        elif switch is True:
            operation = instance.group_operation

            operations = [x[0] for x in TWITTER_RULES_OPERATIONS.get_choices()]

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
                    TWITTER_RULES_OPERATION_DEFAULT

            else:
                # we are merging with an existing group

                instance.group = merge_with.group
                instance.group_operation = merge_with.group_operation

            merge_with.save()
            instance.save()
