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

from pymongo.errors import DuplicateKeyError

from mongoengine import Document, NULLIFY, CASCADE, PULL
from mongoengine.fields import (StringField, ReferenceField,
                                ListField, BooleanField)
from mongoengine.errors import NotUniqueError, ValidationError, DoesNotExist

from django.utils.translation import ugettext_lazy as _

from ....base.fields import IntRedisDescriptor
from ....base.utils import register_task_method

from .common import (DocumentHelperMixin, DocumentTreeMixin,
                     PseudoQuerySet, lowername)
from .user import User

LOGGER = logging.getLogger(__name__)


__all__ = ['Folder',

           # Make these accessible to compute them from `DocumentHelperMixin`.
           'folder_all_articles_count_default',
           'folder_starred_articles_count_default',
           'folder_unread_articles_count_default',
           'folder_archived_articles_count_default',
           'folder_bookmarked_articles_count_default',
           ]


def folder_all_articles_count_default(folder, *args, **kwargs):

    return folder.reads.count()


def folder_starred_articles_count_default(folder, *args, **kwargs):

    return folder.reads(is_starred=True).count()


def folder_unread_articles_count_default(folder, *args, **kwargs):

    return folder.reads(is_read=False).count()


def folder_archived_articles_count_default(folder, *args, **kwargs):

    return folder.reads(is_archived=True).count()


def folder_bookmarked_articles_count_default(folder, *args, **kwargs):

    return folder.reads(is_bookmarked=True).count()


class Folder(Document, DocumentHelperMixin, DocumentTreeMixin):

    # BIG DB migration 20141028
    bigmig_migrated = BooleanField(default=False)
    # END BIG DB migration

    name  = StringField(verbose_name=_(u'Name'),
                        unique_with=['owner', 'parent'])
    owner = ReferenceField('User', verbose_name=_(u'Owner'),
                           reverse_delete_rule=CASCADE)

    parent = ReferenceField('self', verbose_name=_(u'Parent folder'),
                            reverse_delete_rule=NULLIFY, required=False)
    children = ListField(ReferenceField('self', reverse_delete_rule=PULL),
                         default=list, verbose_name=_(u'Children folders'))

    all_articles_count = IntRedisDescriptor(
        attr_name='f.aa_c', default=folder_all_articles_count_default,
        set_default=True)

    unread_articles_count = IntRedisDescriptor(
        attr_name='f.ua_c', default=folder_unread_articles_count_default,
        set_default=True)

    starred_articles_count = IntRedisDescriptor(
        attr_name='f.sa_c', default=folder_starred_articles_count_default,
        set_default=True)

    archived_articles_count = IntRedisDescriptor(
        attr_name='f.ra_c',
        default=folder_archived_articles_count_default,
        set_default=True, min_value=0)

    bookmarked_articles_count = IntRedisDescriptor(
        attr_name='f.ba_c', default=folder_bookmarked_articles_count_default,
        set_default=True)

    def __unicode__(self):
        return _(u'{0} (#{1}) for user {2}{3}{4}').format(
            self.name, self.id, self.owner,
            _(u', parent: {0} (#{1})').format(self.parent.name, self.parent.id)
                if self.parent else u'',
            _(u', children: {0}').format(u', '.join(
                _(u'{0} (#{1})').format(child.name, child.id)
                    for child in self.children))
                        if self.children != [] else u'')

    @classmethod
    def get_root_for(cls, user):

        try:
            return cls.objects.get(name=u'__root__', owner=user)

        except DoesNotExist:
            return cls(name=u'__root__', owner=user).save()

    def validate(self, *args, **kwargs):

        try:
            super(Folder, self).validate(*args, **kwargs)

        except ValidationError as e:
            parent_error = e.errors.get('parent', None)

            if parent_error and str(parent_error).startswith('Field is requi'):
                # Allow the creation of the root folder whatever it costs,
                # else we cannot create any directory (chicken & egg pbm).
                if self.name == u'__root__':
                    e.errors.pop('parent')

            if e.errors:
                raise e

    @classmethod
    def add_folder_from_tag(cls, tag, owner, parent=None):
        """

            Returns (folder, created) or raise an exception.
        """

        if len(tag.parents) == 1:
            parent_folder, _created = cls.add_folder_from_tag(tag.parents[0],
                                                              owner)

        elif len(tag.parents) > 1:
            best_parent = tag.parents[0]

            # TODO: get the best tag from the LANG or whatever.
            #
            # for parent_tag in tag.parents:
            #    …

            parent_folder, _created = cls.add_folder_from_tag(best_parent,
                                                              owner)

        else:
            parent_folder = None

        folder, created = cls.add_folder(tag.name, owner, parent_folder)

        return folder, created

    @classmethod
    def add_folder(cls, name, user, parent=None, children=None):
        """

            Returns (folder, created) or raise an exception.
        """

        assert parent is None or isinstance(parent, cls)
        assert children is None or hasattr(children, '__iter__')

        if children is None:
            children = ()

        if parent is None:
            parent = cls.get_root_for(user)

        created = True

        try:
            folder = cls(name=name, owner=user, parent=parent).save()

        except (NotUniqueError, DuplicateKeyError):
            created = False
            folder  = cls.objects.get(name=name, owner=user, parent=parent)

        else:
            # If the folder exists [with the same parent], no
            # need to add it as child, it's already the case.
            parent.add_child(folder, update_reverse_link=False)

        if children:
            for child in children:
                assert child.owner == folder.owner

                folder.add_child(child, full_reload=False)

            folder.reload()

        LOGGER.info(u'Created folder %s.', folder)

        return folder, created

    @classmethod
    def signal_pre_delete_handler(cls, sender, document, **kwargs):

        folder_to_delete = document

        if folder_to_delete.parent:
            for child in folder_to_delete.children:
                child.set_parent(folder_to_delete.parent)

        else:
            for child in folder_to_delete.children:
                child.unset_parent()

    @property
    def has_content(self):

        # PERF: it's faster to test for children than query for subscriptions.
        return self.children or self.subscriptions

    @property
    def max_depth(self):

        return 4 \
            if self.owner.preferences.selector.extended_folders_depth \
            else 2

    def get_subfolders(self, current_level):

        if current_level >= self.max_depth:
            return PseudoQuerySet()

        children = PseudoQuerySet(model=self.__class__)

        for child in sorted(self.children, key=lowername):
            children.append(child)
            children.extend(child.get_subfolders(current_level + 1))

        return children

    def purge(self):
        """ Remove a folder and all its content (subfolders, subscriptions). """

        for child in self.children:
            child.purge()
            child.delete()

        for subscription in self.owner.subscriptions.filter(folders=self):
            # Don't delete subscription if present in another folder, in case
            # user has activated the multi-folder subscriptions preference.
            if len(subscription.folders) == 1:
                subscription.delete()

        self.delete()

#
# HEADS UP: this task conflicts with the one from reldb. Both cannot
#           be active at the same time.
#
# register_task_method(Folder, Folder.purge, globals(), queue=u'low')

# ————————————————————————————————————————————————————————— external properties
#                                            Defined here to avoid import loops


def User_folders_property_get(self):

    return Folder.objects(owner=self, parent__ne=None)


def User_root_folder_property_get(self):

    return Folder.get_root_for(self)


def User_top_folders_property_get(self):

    return self.folders.filter(parent=self.root_folder).order_by('name')


def User_folders_tree_property_get(self):
    """ Returns the full (but preference-via
        depth-limited) user folders tree as a list. """

    return self.get_folders_tree()


def User_get_folders_tree_method(self, for_parent=False):

    folders = PseudoQuerySet(model=Folder)

    # Articificialy increment the level by one to limit the folder
    # tree to the N-1 levels. This clamps the folder manager modal.
    level = 1 if for_parent else 0

    for folder in self.top_folders.order_by('name'):
        folders.append(folder)
        folders.extend(folder.get_subfolders(level + 1))

    return folders


User.folders          = property(User_folders_property_get)
User.root_folder      = property(User_root_folder_property_get)
User.top_folders      = property(User_top_folders_property_get)
User.folders_tree     = property(User_folders_tree_property_get)
User.get_folders_tree = User_get_folders_tree_method
