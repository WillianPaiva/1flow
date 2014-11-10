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
# from django.core.urlresolvers import reverse, reverse_lazy
from django.utils.translation import ugettext_lazy as _

from django_select2.widgets import Select2Widget, Select2MultipleWidget

from django_file_form.forms import FileFormMixin, UploadedFileField

from ..models import Folder, Subscription

from .fields import OnlyNameChoiceField, OnlyNameMultipleChoiceField


LOGGER = logging.getLogger(__name__)


class ManageFolderForm(FileFormMixin, forms.ModelForm):

    """ Manage folder (in the modal). """

    image = UploadedFileField(required=False)

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
        fields = ('name', 'slug', 'image_url', 'parent', )
        # widgets = {
        #     'name': forms.TextInput(),
        # }

    def __init__(self, *args, **kwargs):
        """ init(me). """

        self.folder_owner = kwargs.pop('owner')

        super(ManageFolderForm, self).__init__(*args, **kwargs)

        folders_tree = self.folder_owner.get_folders_tree(for_parent=True)

        if self.instance.id:
            try:
                folders_tree.exclude(id=self.instance.id)
            except ValueError:
                pass

            else:
                for f in self.instance.children_tree:
                    try:
                        folders_tree.exclude(id=f.id)

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
        """ Return root if no parent selected. """

        try:
            parent = self.cleaned_data['parent']

        except:
            return self.folder_owner.root_folder

        if parent is None:
            return self.folder_owner.root_folder

        return parent

    def is_valid(self):
        """ Check a lot of internal stuff to be useful to the user. """

        res = super(ManageFolderForm, self).is_valid()

        if not res:
            return False

        if self.instance.id is None:

            parent_folder = self.cleaned_data['parent']

            try:
                Folder.objects.get(
                    user=self.folder_owner,
                    name=self.cleaned_data['name'],
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
        """ Save folder and synchronize_subscriptions_folders(). """

        if self.cleaned_data['image']:
            self.instance.image = self.cleaned_data['image']
        else:
            self.instance.image = None

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
                    old_folder.parent.children.remove(self.instance)

                except AttributeError:
                    # A top folder is becoming a sub-folder. It had no parent.
                    pass
                parent_changed = True

        else:
            # In "add folder" mode, parent has always changed, it's new!
            parent_changed = True

        folder = super(ManageFolderForm, self).save(commit=False)

        if self.instance.id is None:
            folder.user = self.folder_owner

        if commit:
            folder.save()

        if parent_changed:
            # In edit or create mode, we need to take care of the other
            # direction of the double-linked relation. This will imply
            # a superfluous write in case of an unchanged parent
            parent_folder.children.add(folder)

        self.synchronize_subscriptions_folders(folder)

        self.delete_temporary_files()

        return folder

    def synchronize_subscriptions_folders(self, folder):
        """ Move subscriptions from old folder to new, given user prefs.

        .. note:: `folder` is just self.instance passed
            through to avoid to look it up again.
        """

        try:
            initial_subscriptions = \
                self.folder_owner.subscriptions_by_folder[self.instance]

        except KeyError:
            initial_subscriptions = []

        updated_subscriptions = self.cleaned_data['subscriptions']

        for subscription in initial_subscriptions:
            if subscription not in updated_subscriptions:
                subscription.folders.remove(folder)

        if self.folder_owner.preferences.selector.subscriptions_in_multiple_folders:  # NOQA
            replace_folders = False

        else:
            replace_folders = True

        for subscription in updated_subscriptions:
            # This will update more things than needed, but in the case of
            # a changed preference, this will make the subscription appear
            # in one folder only again.
            # TODO: when the preference has a trigger on save() that do
            # this automatically, uncomment the following line to simply
            # move new subscriptions to this folder, and not touch others.
            #
            # if subscription not in initial_subscriptions:
            if replace_folders:
                subscription.folders.clear()

            subscription.folders.add(folder)
