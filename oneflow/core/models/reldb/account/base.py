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
import uuid
import logging

from constance import config

from json_field import JSONField

# from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
# from django.db.models.signals import post_save, pre_save  # , pre_delete

from polymorphic import (
    PolymorphicQuerySet,
    PolymorphicManager,
    PolymorphicModel,
)

from sparks.django.models.mixins import DiffMixin

from oneflow.base.utils.dateutils import now, timedelta

from oneflow.base.utils import (
    # register_task_method,
    RedisExpiringLock,
)

from ..common import User

LOGGER = logging.getLogger(__name__)

__all__ = [
    'BaseAccount',
    'BaseAccountManager',
    'BaseAccountQuerySet',
    # 'baseaccount_pre_save',
]


# ————————————————————————————————————————— Utils / redis descriptors functions


def get_account_image_upload_path(instance, filename):

    if not filename.strip():
        filename = uuid.uuid4()

    # The filename will be used in a shell command later. In case the
    # user/admin forgets the '"' in the configuration, avoid problems.
    filename = filename.replace(u' ', u'_')

    if instance:
        return 'user/{0}/account/{1}/images/{1}'.format(
            instance.user.username, instance.id, filename)

    return u'images/%Y/%m/%d/{0}'.format(filename)


# ———————————————————————————————————————————————————————————————————— Managers

class BaseAccountQuerySet(PolymorphicQuerySet):

    """ Account based queryset.

    .. note:: this query set will be patched by subclasses.
    """

    def inactive(self):
        return self.filter(is_active=False)

    def active(self):
        return self.filter(is_active=True)

    def usable(self):
        return self.active().filter(is_usable=True)

    def unusable(self):
        return self.active().filter(is_usable=False)


class BaseAccountManager(PolymorphicManager):

    """ A manager that adds some things. """

    use_for_related_fields = True
    queryset_class = BaseAccountQuerySet

# ——————————————————————————————————————————————————————————————————————— Model


class BaseAccount(PolymorphicModel, DiffMixin):

    """ Base 1flow account. """

    class Meta:
        app_label = 'core'
        verbose_name = _(u'Base account')
        verbose_name_plural = _(u'Base accounts')

    # Can be overriden by inherited classes.
    usable_start_task_name   = None
    reset_unusable_task_name = None

    INPLACEEDIT_EXCLUDE = ('options', )

    # ———————————————————————————————————————————————————————————————— Managers

    objects = BaseAccountManager()

    # —————————————————————————————————————————————————————————————— Attributes

    # NOTE: keep ID a simple integer/auto
    # field, this surely helps JOIN operations.
    # id             = models.UUIDField(primary_key=True,
    #                                   default=uuid.uuid4, editable=False)

    user = models.ForeignKey(User, verbose_name=_(u'Owner'),
                             related_name='accounts')

    name = models.CharField(verbose_name=_(u'Account name'),
                            max_length=128, blank=True)

    slug = models.CharField(verbose_name=_(u'slug'),
                            max_length=255,
                            null=True, blank=True)

    # items = models.ManyToManyField(BaseItem, blank=True, null=True,
    #                               verbose_name=_(u'Feed items'),
    #                               related_name='feeds')

    date_created = models.DateTimeField(auto_now_add=True, blank=True,
                                        verbose_name=_(u'Date created'))

    date_last_conn = models.DateTimeField(
        verbose_name=_(u'Last connection date'),
        null=True, blank=True)

    conn_error = models.CharField(
        verbose_name=_(u'Last connection error'),
        max_length=255, null=True, blank=True)

    is_usable = models.BooleanField(
        verbose_name=_(u'usable'),
        default=True, blank=True,
        help_text=_(u'Is account connectivity good or not?'))

    is_active = models.BooleanField(
        verbose_name=_(u'active'),
        default=True, blank=True,
        help_text=_(u'Is account enabled for fetching?'))

    options = JSONField(default=dict, blank=True)

    notes = models.TextField(
        verbose_name=_(u'Notes'), null=True, blank=True,
        help_text=_(u'User notes for this account.'))

    image = models.ImageField(
        verbose_name=_(u'Thumbnail'), null=True, blank=True,
        upload_to=get_account_image_upload_path, max_length=256,
        help_text=_(u'Use either image when 1flow instance hosts the '
                    u'image, or image_url when hosted elsewhere. If '
                    u'both are filled, image takes precedence.'))

    image_url = models.URLField(
        verbose_name=_(u'Thumbnail URL'), null=True, blank=True, max_length=384,
        help_text=_(u'Full URL of the image displayed in the feed '
                    u'selector. Can be hosted outside of 1flow.'))

    # —————————————————————————————————————————————————————— Django & Grappelli

    def __unicode__(self):
        """ Hello, pep257. I love you so. """

        return _(u'BaseAccount {0} ({1}) of {2}').format(
            self.name, self.id, self.user.username)

    @staticmethod
    def autocomplete_search_fields():
        """ grappelli auto-complete method. """

        return ('name__icontains', )

    # —————————————————————————————————————————————————————————————— Properties

    @property
    def config_account_refresh_period(self):
        """ Return the default account refresh period.

        .. note:: it's recommended to override this
            property in polymorphic inheritant models.
        """

        return config.ACCOUNT_REFRESH_PERIOD_DEFAULT

    @property
    def refresh_lock(self):
        try:
            return self.__refresh_lock

        except AttributeError:
            self.__refresh_lock = RedisExpiringLock(
                self, lock_name='account_fetch',
            )
            return self.__refresh_lock

    @property
    def recently_usable(self):
        """ Return True if the account has been tested/connected recently. """

        return self.is_usable and (
            now() - self.date_last_conn
            < timedelta(seconds=self.config_account_refresh_period))

    # ————————————————————————————————————————————————————————————————— Methods

    def reset_unusable(self, commit=True):
        """ Mark the current instance needing to test usability.

        This is called typically when a connection parameter has changed,
        and the current account connectivity needs to be tested again to
        validate them all.
        """

        self.date_last_conn = None
        self.is_usable = False

        if commit:
            self.save()

        try:
            reset_unusable_task = self._meta.model.reset_unusable_task

        except:
            pass

        else:
            reset_unusable_task.apply_async(
                args=(self.id, ), countdown=3)

    def mark_unusable(self, message, args=(), exc=None, commit=True):
        """ Mark account unsable with date & message, log exception if any. """

        if exc is not None:
            if args:
                message = message % args

            message = u'{0} ({1})'.format(message, unicode(exc))
            LOGGER.exception(u'%s unusable: %s', self, message)

        self.date_last_conn = now()
        self.conn_error = message
        self.is_usable = False

        if commit:
            self.save()

    def mark_usable(self, commit=True, verbose=True):
        """ Mark the account usable and clear error. """

        if verbose:
            LOGGER.info(u'%s is now considered usable.', self)

        if self.is_usable:
            start_task = False

        else:
            start_task = True

        self.date_last_conn = now()
        self.conn_error = None
        self.is_usable = True

        if commit:
            self.save()

        try:
            usable_start_task = self._meta.model.usable_start_task

        except:
            pass

        else:
            if start_task:
                usable_start_task.delay(self.id)

    def has_option(self, option):
        """ True if option in self.options. """

        return option in self.options
