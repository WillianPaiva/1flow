# -*- coding: utf-8 -*-
"""
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

import uuid
import logging

from django.db import models
from django.db.models.signals import pre_save
from django.utils.translation import ugettext_lazy as _
from django.utils.text import slugify

from sparks.django.models import DiffMixin

from mptt.models import MPTTModel, TreeForeignKey

from oneflow.base.fields import IntRedisDescriptor
from oneflow.base.utils import register_task_method

from common import lowername, DjangoUser as User


LOGGER = logging.getLogger(__name__)


__all__ = [
    'Folder',

    'folder_all_items_count_default',
    'folder_starred_items_count_default',
    'folder_unread_items_count_default',
    'folder_archived_items_count_default',
    'folder_bookmarked_items_count_default',
]


def qs_order_by_lower_name(queryset, field=None):
    """ Order a QuerySet by lowercase(field); field is “name” by default. """

    return queryset.extra(
        select={'_lower_order_by_field_': 'lower({0})'.format(field or 'name')}
    ).order_by('_lower_order_by_field_')


def get_folder_image_upload_path(instance, filename):

    if not filename.strip():
        filename = uuid.uuid4()

    # The filename will be used in a shell command later. In case the
    # user/admin forgets the '"' in the configuration, avoid problems.
    filename = filename.replace(u' ', u'_')

    if instance:
        return 'user/{0}/folder/{1}/images/{2}'.format(
            instance.user.username, instance.id, filename)

    return u'images/%Y/%m/%d/{0}'.format(filename)


# ——————————————————————————————————————————————————————————————— Redis Helpers


def folder_all_items_count_default(folder, *args, **kwargs):

    return folder.reads.all().count()


def folder_starred_items_count_default(folder, *args, **kwargs):

    return folder.reads.filter(is_starred=True).count()


def folder_unread_items_count_default(folder, *args, **kwargs):

    return folder.reads.filter(is_read=False).count()


def folder_archived_items_count_default(folder, *args, **kwargs):

    return folder.reads.filter(is_archived=True).count()


def folder_bookmarked_items_count_default(folder, *args, **kwargs):

    return folder.reads.filter(is_bookmarked=True).count()


# —————————————————————————————————————————————————————————————————————— Models


class Folder(MPTTModel, DiffMixin):

    """ A simple folder structure. """

    class Meta:
        app_label = 'core'
        verbose_name = _(u'Folder')
        verbose_name_plural = _(u'Folders')
        unique_together = ('name', 'user', 'parent', )

    user = models.ForeignKey(User, verbose_name=_(u'Owner'),
                             related_name='folders')

    name = models.CharField(verbose_name=_(u'Name'), max_length=255)
    slug = models.CharField(verbose_name=_(u'slug'), max_length=255,
                            null=True, blank=True)

    parent = TreeForeignKey('self', null=True, blank=True,
                            related_name='children')

    date_created = models.DateTimeField(auto_now_add=True, blank=True,
                                        verbose_name=_(u'Date created'))

    # Allow the user to also customize the visual of his/her subscription.
    image = models.ImageField(
        verbose_name=_(u'Image'), null=True, blank=True,
        upload_to=get_folder_image_upload_path, max_length=256,
        help_text=_(u'A custom image for the folder. Takes precedence over '
                    u'image_url if both are filled.'))

    image_url = models.URLField(
        verbose_name=_(u'Image URL'), null=True, blank=True, max_length=384,
        help_text=_(u'A full URL of an online image, if you prefer hosting '
                    u'it outside of 1flow.'))

    # —————————————————————————————————————————————————————— Cached descriptors

    all_items_count = IntRedisDescriptor(
        attr_name='f.aa_c', default=folder_all_items_count_default,
        set_default=True)

    unread_items_count = IntRedisDescriptor(
        attr_name='f.ua_c', default=folder_unread_items_count_default,
        set_default=True)

    starred_items_count = IntRedisDescriptor(
        attr_name='f.sa_c', default=folder_starred_items_count_default,
        set_default=True)

    archived_items_count = IntRedisDescriptor(
        attr_name='f.ra_c',
        default=folder_archived_items_count_default,
        set_default=True, min_value=0)

    bookmarked_items_count = IntRedisDescriptor(
        attr_name='f.ba_c', default=folder_bookmarked_items_count_default,
        set_default=True)

    # ————————————————————————————————————————————————————————— Django & Python

    def __unicode__(self):
        """ Wake up, pep257. That's just the unicode method. """

        return _(u'{0} (#{1}, level {2}) for user {3}{4}{5}').format(
            self.name, self.id, self.level, self.user,
            _(u', parent: {0} (#{1})').format(self.parent.name, self.parent.id)
            if self.parent else u'',
            _(u', children: {0}').format(u', '.join(
                _(u'{0} (#{1})').format(child.name, child.id)
                for child in self.children.all()))
            if self.children != [] else u'')

    # —————————————————————————————————————————————————————————————— Properties

    @property
    def has_content(self):

        # PERF: it's faster to test for children than query for subscriptions.
        return self.children or self.subscriptions

    @property
    def max_depth(self):

        return 4 \
            if self.user.preferences.selector.extended_folders_depth \
            else 2

    @property
    def children_tree(self):
        """ Return my children and their own, in tree order. """

        return self.get_descendants()

    @property
    def children_by_name(self):

        return qs_order_by_lower_name(self.children.all())

    # ——————————————————————————————————————————————————————————— Class methods

    @classmethod
    def get_root_for(cls, user):
        """ Get the root folder for a user. Might create it on the fly. """

        root, created = cls.objects.get_or_create(user=user,
                                                  name=u'__root__',
                                                  parent=None)

        return root

    @classmethod
    def add_folder_from_tag(cls, tag, user, parent=None):
        """ Return (folder, created) or raise an exception. """

        raise NotImplementedError("REVIEW for RELDB.")

        if len(tag.parents) == 1:
            parent_folder, _created = cls.add_folder_from_tag(tag.parents[0],
                                                              user)

        elif len(tag.parents) > 1:
            best_parent = tag.parents[0]

            # TODO: get the best tag from the LANG or whatever.
            #
            # for parent_tag in tag.parents:
            #    …

            parent_folder, _created = cls.add_folder_from_tag(best_parent,
                                                              user)

        else:
            parent_folder = None

        folder, created = cls.add_folder(tag.name, user, parent_folder)

        return folder, created

    @classmethod
    def add_folder(cls, name, user, parent=None, children=None):
        """ Return (folder, created) or raise an exception. """

        assert parent is None or isinstance(parent, cls)
        assert children is None or hasattr(children, '__iter__')

        if children is None:
            children = ()

        if parent is None:
            parent = cls.get_root_for(user)

        # Should we disable the name __root__ ?
        # In fact, this doesn't raise any problem.
        # There will always be a root with parent=None
        # Satisfy the user root folder query.
        # So let the user be free.
        #
        # elif name == u'__root__':
        #     raise RuntimeError('Name __root___ is reserved')

        folder, created = cls.objects.get_or_create(name=name,
                                                    user=user,
                                                    parent=parent)
        if created:
            parent.children.add(folder)

            if children:
                folder.children.add(*children)

            LOGGER.info(u'Created folder %s.', folder)

        return folder, created

    # ————————————————————————————————————————————————————————————————— Methods

    def get_subfolders(self, current_level):

        raise NotImplementedError('Use MPTT for get_subfolders()')

        if current_level >= self.max_depth:
            return models.QuerySet()

        children = models.QuerySet(model=self.__class__)

        for child in sorted(self.children, key=lowername):
            children.append(child)
            children.extend(child.get_subfolders(current_level + 1))

        return children

    def purge(self, self_delete=True):
        """ Remove a folder and all its content (subfolders, subscriptions). """

        for child in self.children.all():

            # Don't bother multiple queries to delete children:
            # with MPTT, deleting us will also delete our children.
            child.purge(self_delete=False)

        for subscription in self.subscriptions.all():
            # Don't delete subscription if present in another folder, in case
            # user has activated the multi-folder subscriptions preference.
            if subscription.folders.count() == 1:
                subscription.delete()

        if self_delete:
            self.delete()


# ——————————————————————————————————————————————————————————————— Tasks methods


register_task_method(Folder, Folder.purge, globals(), queue=u'background')



# ————————————————————————————————————————————————————————————————————— Signals


def folder_pre_save(instance, **kwargs):

    if not instance.slug:
        instance.slug = slugify(instance.name)


pre_save.connect(folder_pre_save, sender=Folder)


# ————————————————————————————————————————————————————————— external properties
#                                            Defined here to avoid import loops


def User_root_folder_property_get(self):

    return Folder.get_root_for(self)


def User_top_folders_property_get(self):

    return qs_order_by_lower_name(self.folders.filter(parent=self.root_folder))


def User_folders_tree_property_get(self):
    """ Returns the full (but preference-via
        depth-limited) user folders tree as a list. """

    return self.get_folders_tree()


def User_get_folders_tree_method(self, for_parent=False):
    """ Return the user folder tree, excluding his/her root folder. """

    root_folder = self.root_folder

    # Thanks, Django-MPTT
    return root_folder.get_descendants().filter(
        level__lte=root_folder.max_depth - (1 if for_parent else 0))


User.root_folder      = property(User_root_folder_property_get)
User.top_folders      = property(User_top_folders_property_get)
User.folders_tree     = property(User_folders_tree_property_get)
User.get_folders_tree = User_get_folders_tree_method
