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
import simplejson as json

from dateutil import parser as date_parser

from django import forms
from django.core.urlresolvers import reverse, reverse_lazy

from django.utils.translation import ugettext_lazy as _
from django.core.validators import URLValidator
from django.contrib import messages

from mongodbforms import DocumentForm

from django_select2.widgets import (Select2Widget, Select2MultipleWidget,
                                    HeavySelect2MultipleWidget)

from ..models.nonrel import (
    Folder, Subscription, Feed, Article, Read
)
from .fields import OnlyNameChoiceField, OnlyNameMultipleChoiceField


LOGGER = logging.getLogger(__name__)

#
#
# HEADS UP: 20141112: THIS IS AN OLD MONGODB FILE.
#           UNUSED IN THE RELATIONAL IMPLEMENTATION.
#           KEPT FOR MEMORIES, UNTIL UPCOMING DELETION.
#
#


class ManageFolderForm(DocumentForm):
    parent = OnlyNameChoiceField(queryset=Folder.objects.all(),
                                 empty_label=_(u'(None)'),
                                 label=_(u'Parent folder'),
                                 required=False, widget=Select2Widget())

    subscriptions = OnlyNameMultipleChoiceField(
        label=_(u'Subscriptions'), queryset=Subscription.objects.none(),
        required=False, widget=Select2MultipleWidget(),
        help_text=_(u'These are the ones held directly by the folder; they '
                    u'are displayed above subfolders. There can be none, if '
                    u'you prefer dispatching your subscriptions in subfolders '
                    u'only.'))

    class Meta:
        model = Folder
        fields = ('name', 'parent', )
        widgets = {
            'name': forms.TextInput(),
        }

    def __init__(self, *args, **kwargs):

        self.folder_owner = kwargs.pop('owner')

        super(ManageFolderForm, self).__init__(*args, **kwargs)

        folders_tree = self.folder_owner.get_folders_tree(for_parent=True)

        if self.instance.id:
            try:
                folders_tree.remove(self.instance)
            except ValueError:
                pass

            else:
                for f in self.instance.children_tree:
                    try:
                        folders_tree.remove(f)

                    except ValueError:
                        # ValueError: list.remove(x): x not in list
                        # Happens when try to remove a level-N+ folder
                        # from a list limited to level N-1 folder. No
                        # need to continue, folders_tree return a
                        # depth-aware list.
                        break

            try:
                self.fields['subscriptions'].initial = \
                    self.folder_owner.subscriptions_by_folder[self.instance]

            except KeyError:
                # No subscriptions in this folder yet.
                pass

        self.fields['parent'].queryset = folders_tree
        self.fields['subscriptions'].queryset = \
            self.folder_owner.subscriptions.order_by('name')

    def clean_parent(self):

        try:
            parent = self.cleaned_data['parent']

        except:
            return self.folder_owner.root_folder

        if parent is None:
            return self.folder_owner.root_folder

        return parent

    def is_valid(self):

        res = super(ManageFolderForm, self).is_valid()

        if not res:
            return False

        if self.instance.id is None:

            parent_folder = self.cleaned_data['parent']

            try:
                Folder.objects.get(
                    owner=self.folder_owner, name=self.cleaned_data['name'],
                    parent=parent_folder)
            except Folder.DoesNotExist:
                return True

            else:
                if parent_folder == self.folder_owner.root_folder:
                    self._errors['already_exists'] = \
                        _(u'A top folder by that name already exists.')
                else:
                    self._errors['already_exists'] = \
                        _(u'A folder by that name already exists '
                          u'at the same place.')

                return False

        return True

    def save(self, commit=True):

        parent_folder  = self.cleaned_data.get('parent')
        parent_changed = False

        # id == None means creation, else we are editing.
        if self.instance.id:

            # We need to get the previous values; Django doesn't cache
            # them and self.instance is already updated with new values.
            old_folder = Folder.objects.get(id=self.instance.id)

            if old_folder.parent != parent_folder:
                # The form.save() will set the new parent, but
                # will not unset instance from parent.children.
                # We need to take care of this.
                try:
                    old_folder.parent.remove_child(self.instance,
                                                   full_reload=False,
                                                   update_reverse_link=False)
                except AttributeError:
                    # A top folder is becoming a sub-folder. It had no parent.
                    pass
                parent_changed = True

        else:
            # In "add folder" mode, parent has always changed, it's new!
            parent_changed = True

        folder = super(ManageFolderForm, self).save(commit=False)

        if self.instance.id is None:
            folder.owner = self.folder_owner

        if commit:
            folder.save()

        if parent_changed:
            # In edit or create mode, we need to take care of the other
            # direction of the double-linked relation. This will imply
            # a superfluous write in case of an unchanged parent
            parent_folder.add_child(folder, full_reload=False,
                                    update_reverse_link=False)

        self.synchronize_subscriptions_folders(folder)

        return folder

    def synchronize_subscriptions_folders(self, folder):
        """ NOTE: `folder` is just self.instance passed
            through to avoid to look it up again. """

        try:
            initial_subscriptions = \
                self.folder_owner.subscriptions_by_folder[self.instance]

        except KeyError:
            initial_subscriptions = []

        updated_subscriptions = self.cleaned_data['subscriptions']

        for subscription in initial_subscriptions:
            if subscription not in updated_subscriptions:
                subscription.update(pull__folders=folder)

        if self.folder_owner.preferences.selector.subscriptions_in_multiple_folders: # NOQA
            subscr_kwargs = {'add_to_set__folders': folder}

        else:
            subscr_kwargs = {'set__folders': [folder]}

        for subscription in updated_subscriptions:
            # This will update more things than needed, but in the case of
            # a changed preference, this will make the subscription appear
            # in one folder only again.
            # TODO: when the preference has a trigger on save() that do
            # this automatically, uncomment the following line to simply
            # move new subscriptions to this folder, and not touch others.
            #
            # if subscription not in initial_subscriptions:
            subscription.update(**subscr_kwargs)


class ManageSubscriptionForm(DocumentForm):

    class Meta:
        model = Subscription

        # NOTE: as we manage `folders` differently and very specially, given
        # the value of a user preference, we MUST NOT put `folders` here in
        # `fields`, because in one of 2 cases, setting the initial value will
        # not work because of attribute being a list and field being not.
        fields = ('name', )
        widgets = {
            'name': forms.TextInput(),
        }

    def __init__(self, *args, **kwargs):

        super(ManageSubscriptionForm, self).__init__(*args, **kwargs)

        folders_queryset = self.instance.user.folders_tree

        if self.instance.user.preferences.selector.subscriptions_in_multiple_folders: # NOQA
            self.fields['folders'] = OnlyNameMultipleChoiceField(
                queryset=folders_queryset, required=False, label=_(u'Folders'),
                widget=Select2MultipleWidget(), initial=self.instance.folders)
                # no empty_label here.

        else:
            self.fields['folders'] = OnlyNameChoiceField(
                queryset=folders_queryset, required=False,
                widget=Select2Widget(), label=_(u'Folder'),
                empty_label=_(u'(None)'))

            try:
                self.fields['folders'].initial = self.instance.folders[0]

            except IndexError:
                # Subscription is not in any folder yet.
                pass

    def save(self, commit=True):

        subscription = super(ManageSubscriptionForm, self).save(commit=False)
        preferences  = subscription.user.preferences.selector

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

        return subscription


class AddSubscriptionForm(forms.Form):

    feeds = OnlyNameMultipleChoiceField(queryset=Feed.objects.none(),
                                        required=False,
                                        label=_(u'Search 1flow\'s streams'))

    search_for = forms.CharField(label=_(u'Enter an URL'), required=False)

    def __init__(self, *args, **kwargs):

        self.owner = kwargs.pop('owner')

        super(AddSubscriptionForm, self).__init__(*args, **kwargs)

        # not_shown = [s.feed.id for s in self.owner.subscriptions]
        # LOGGER.warning(len(not_shown))

        # NOTE: this query is replicated in the completer view.
        self.fields['feeds'].queryset = Feed.good_feeds(
            id__nin=[s.feed.id for s in self.owner.subscriptions])

        count = self.fields['feeds'].queryset.count()

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

        created_subscriptions = []

        selector_prefs = self.owner.preferences.selector

        for feed in self.cleaned_data['feeds']:

            folders = []

            for tag in feed.tags:
                folders.append(Folder.add_folder_from_tag(tag, self.owner))

                if not selector_prefs.subscriptions_in_multiple_folders:
                    # One is enough.
                    break

            subscription = Subscription.subscribe_user_to_feed(self.owner, feed,
                                                               background=True)

            subscription.folders = folders

            if commit:
                subscription.save()

            created_subscriptions.append(subscription)

        return created_subscriptions
