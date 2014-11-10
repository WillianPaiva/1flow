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

import logging

from django import forms
from django.utils.translation import ugettext, ugettext_lazy as _
from django.core.urlresolvers import reverse, reverse_lazy

from django_file_form.forms import FileFormMixin, UploadedFileField
from django_select2.widgets import (
    Select2Widget, Select2MultipleWidget, HeavySelect2MultipleWidget,
)

from ..models import BaseFeed, Folder, Subscription, subscribe_user_to_feed

from fields import OnlyNameChoiceField, OnlyNameMultipleChoiceField


LOGGER = logging.getLogger(__name__)


class ManageSubscriptionForm(FileFormMixin, forms.ModelForm):

    """ Edit subscription properties. """

    thumbnail = UploadedFileField(required=False)

    class Meta:
        model = Subscription

        # NOTE: as we manage `folders` differently and very specially, given
        # the value of a user preference, we MUST NOT put `folders` here in
        # `fields`, because in one of 2 cases, setting the initial value will
        # not work because of attribute being a list and field being not.
        fields = ('name', 'notes', 'thumbnail_url', )
        # widgets = {
        #     'name': forms.TextInput(),
        # }

    def __init__(self, *args, **kwargs):
        """ init(me). """

        super(ManageSubscriptionForm, self).__init__(*args, **kwargs)

        folders_queryset = self.instance.user.folders_tree
        preferences = self.instance.user.preferences

        if preferences.selector.subscriptions_in_multiple_folders:
            self.fields['folders'] = OnlyNameMultipleChoiceField(
                queryset=folders_queryset,
                required=False, label=_(u'Folders'),
                widget=Select2MultipleWidget(),
                initial=self.instance.folders.all())
            # no empty_label here.

        else:
            self.fields['folders'] = OnlyNameChoiceField(
                queryset=folders_queryset, required=False,
                widget=Select2Widget(), label=_(u'Folder'),
                empty_label=_(u'(None)'))

            try:
                self.fields['folders'].initial = self.instance.folders.all()[0]

            except IndexError:
                # Subscription is not in any folder yet.
                pass

    def save(self, commit=True):
        """ Save the form, Luke. """

        subscription = super(ManageSubscriptionForm, self).save(commit=False)
        preferences  = subscription.user.preferences.selector

        if self.cleaned_data['thumbnail']:
            subscription.thumbnail = self.cleaned_data['thumbnail']
        else:
            subscription.thumbnail = None

        # Handle `folders` manually, because it's not in form.fields.
        if preferences.subscriptions_in_multiple_folders:
            if self.cleaned_data['folders']:
                subscription.folders = self.cleaned_data['folders']

        elif self.cleaned_data['folders'] is not None:
            # Avoid the:
            #   - 'folders : Saisissez une liste de valeurs.' error.
            #   - A ReferenceField only accepts DBRef or documents: ['folders']
            #       when nothing is selected, this makes value=[None].
            #
            # In "one folder only", we used a "select" widget which didn't
            # built a list. We need to reconstruct it for the save() to work.
            subscription.folders = [self.cleaned_data['folders']]

        elif self.cleaned_data['folders'] is None:
            # User emptied the folder field. The subscription is back to
            # “un-sorted” pseudo-folder.
            subscription.folders = []

        if commit:
            subscription.save()

        self.delete_temporary_files()

        return subscription


class AddSubscriptionForm(forms.Form):

    """ Subscribe the user to feeds. """

    feeds = OnlyNameMultipleChoiceField(queryset=BaseFeed.objects.none(),
                                        required=False,
                                        label=_(u'Search 1flow\'s streams'))

    search_for = forms.CharField(label=_(u'Enter an URL'), required=False)

    def __init__(self, *args, **kwargs):
        """ INIT ME. """

        self.owner = kwargs.pop('owner')

        super(AddSubscriptionForm, self).__init__(*args, **kwargs)

        # not_shown = [s.feed.id for s in self.owner.subscriptions]
        # LOGGER.warning(len(not_shown))

        # HEADS: this query is replicated in the completer view.
        potential_feeds = self.owner.unsubscribed_feeds

        self.fields['feeds'].queryset = potential_feeds

        count = potential_feeds.count()

        self.fields['feeds'].widget = HeavySelect2MultipleWidget(
            data_url=reverse_lazy('feeds_completer'))

        self.fields['feeds'].widget.set_placeholder(
            _(u'Select feed(s) from the {0} referenced').format(count))

        self.fields['search_for'].help_text = _(
            u'<span class="muted">NOTE: this can be long. '
            u'You will be notified when search is done.</span> '
            u'<a href="{0}" target="_blank">How does it work?</a>').format(
                reverse('help') + unicode(_(u'#adding-subscriptions')))

    def is_valid(self):
        """ Be sure the user selects one field out the two. """

        res = super(AddSubscriptionForm, self).is_valid()

        if not res:
            return False

        if not self.cleaned_data['feeds'] \
                and not self.cleaned_data['search_for']:
            self._errors['nothing_choosen'] = \
                _(u'You have to fill at least one of the two fields.')
            return False

        return True

    def save(self, commit=True):
        """ Subscribe user to new feeds. """

        created_subscriptions = []

        base_folder, created = Folder.add_folder(
            name=ugettext(u'☄ Recently subscribed feeds'), user=self.owner)

        for feed in self.cleaned_data['feeds']:

            subscription = subscribe_user_to_feed(user=self.owner,
                                                  feed=feed,
                                                  background=True)

            subscription.folders.add(base_folder)

            created_subscriptions.append(subscription)

        return created_subscriptions
