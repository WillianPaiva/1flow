# -*- coding: utf-8 -*-
u"""
Copyright 2012-2014 Olivier Cortès <oc@1flow.io>.

____________________________________________________________________


The :class:`User` and :class:`UserManager` classes can completely and
transparently replace the one from Django.

We don't use the `username` attribute, but it is implemented as a
readonly property, returning the `email`, which we use as required
user name field.

____________________________________________________________________

Copyright 2012-2014 Olivier Cortès <oc@1flow.io>

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

from transmeta import TransMeta
from json_field import JSONField

from django.db import models
from django.utils.http import urlquote
from django.db.models.signals import post_save  # , pre_save, pre_delete

from django.contrib.auth.models import (BaseUserManager,
                                        AbstractBaseUser,
                                        PermissionsMixin)
from django.utils.translation import ugettext_lazy as _

from mptt.models import MPTTModel, TreeForeignKey

from ..profiles.models import AbstractUserProfile
from ..base.utils.dateutils import now

LOGGER = logging.getLogger(__name__)


# —————————————————————————————————————————————————————————————————————— Models


class EmailContent(models.Model):
    __metaclass__ = TransMeta

    name    = models.CharField(_('Email name'),
                               max_length=128, unique=True)
    subject = models.CharField(_('Email subject'), max_length=256)
    body    = models.TextField(_('Email body'))

    def __unicode__(self):
        return _(u'{field_name}: {truncated_field_value}').format(
            field_name=self.name, truncated_field_value=self.subject[:30]
            + (self.subject[30:] and u'…'))

    class Meta:
        translate = ('subject', 'body', )
        verbose_name = _(u'Email content')
        verbose_name_plural = _(u'Emails contents')


class UserManager(BaseUserManager):
    """ This is a free adaptation of Django's user manager.

        See https://github.com/django/django/blob/master/django/contrib/auth/models.py  # NOQA
        as of 20130526.
    """

    def create_user(self, username, email, password=None, **extra_fields):
        """ Creates and saves a User with the given username,
            email and password. """

        now1 = now()

        if not email:
            raise ValueError('User must have an email')

        email = UserManager.normalize_email(email)

        user = self.model(username=username, email=email,
                          is_active=True, is_staff=False, is_superuser=False,
                          last_login=now1, date_joined=now1, **extra_fields)

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password, **extra_fields):
        u = self.create_user(username, email, password, **extra_fields)
        u.is_staff = True
        u.is_active = True
        u.is_superuser = True
        u.save(using=self._db)
        return u


def get_user_avatar_upload_path(instance, filename):

    if not filename.strip():
        filename = uuid.uuid4()

    # The filename will be used in a shell command later. In case the
    # user/admin forgets the '"' in the configuration, avoid problems.
    filename = filename.replace(u' ', u'_')

    if instance:
        return 'user/{0}/avatars/{1}'.format(instance.id, filename)

    return u'avatars/%Y/%m/%d/{0}'.format(filename)


class User(AbstractBaseUser, PermissionsMixin, AbstractUserProfile):
    """ Username, password and email are required.
        Other fields are optional. """

    # NOTE: AbstractBaseUser brings `password` and `last_login` fields.

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ('email', )

    # This attribute will be filled by OneToOne relations,
    # to create them and check objects when needed.
    check_methods = []
    extended_check_methods = []

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    objects = UserManager()

    username = models.CharField(_('User name'), max_length=254,
                                unique=True, db_index=True,
                                help_text=_('Required. letters, digits, '
                                            'and "@+-_".'))
    email = models.EmailField(_('email address'),  max_length=254,
                              unique=True, db_index=True,
                              help_text=_('Any valid email address.'))
    first_name = models.CharField(_('first name'), max_length=64, blank=True)
    last_name = models.CharField(_('last name'), max_length=64, blank=True)
    is_staff = models.BooleanField(_('staff status'), default=False,
                                   help_text=_('Designates whether the user '
                                               'can log into this admin '
                                               'site.'))
    is_active = models.BooleanField(_('active'), default=True,
                                    help_text=_('Designates whether this user '
                                                'should be treated as '
                                                'active. Unselect this instead '
                                                'of deleting accounts.'))
    date_joined = models.DateTimeField(_('date joined'), default=now)

    avatar = models.ImageField(
        verbose_name=_(u'Avatar'), null=True, blank=True,
        upload_to=get_user_avatar_upload_path, max_length=256,
        help_text=_(u'Use either avatar when 1flow instance hosts the '
                    u'image, or avatar_url when hosted elsewhere. If '
                    u'both are filled, avatar takes precedence.'))

    avatar_url = models.URLField(
        verbose_name=_(u'Avatar URL'), null=True, blank=True, max_length=384,
        help_text=_(u'Full URL of the avatar displayed in the feed '
                    u'selector. Can be hosted outside of 1flow.'))

    address_book = JSONField(verbose_name=_(u'Address book'),
                             default=list, blank=True)

    # —————————————————————————————————————————————————————————————— Properties

    @property
    def is_local(self):
        return self.password != u'!'

    @property
    def has_contacts(self):

        return len(self.address_book) > 0

    # ————————————————————————————————————————————————————————————————— Methods

    def _run_check_methods(self, methods_list, extended_check=False,
                           force=False, commit=True):
        """ Internal method to run checks.
        """
        all_went_ok = True
        failed_checks = []

        for check_method_name in methods_list:
            try:
                result = getattr(self, check_method_name)(
                    extended_check=extended_check, force=force, commit=commit)

            except:
                failed_checks.append(check_method_name)
                LOGGER.exception(u'Check method “%s” failed for user %s',
                                 check_method_name, self)
            else:
                if not result:
                    all_went_ok = False

        return all_went_ok, failed_checks

    def check(self, extended_check=False, propagate_extended=False,
              force=False, commit=True):

        LOGGER.info(u'Checking user %s…', self)
        LOGGER.info(u'Running check %s…', u', '.join(self.check_methods))

        all_went_ok = True
        failed_checks = []

        awo, fcs = self._run_check_methods(self.check_methods,
                                           extended_check=extended_check,
                                           force=force, commit=commit)

        if not awo:
            all_went_ok = False

        failed_checks.extend(fcs)

        if extended_check:
            LOGGER.info(u'Running extended checks %s for user %s…',
                        u', '.join(self.extended_check_methods), self)

            awo, fcs = self._run_check_methods(
                self.extended_check_methods,
                extended_check=propagate_extended,
                force=force, commit=commit
            )

            if not awo:
                all_went_ok = False

            failed_checks.extend(fcs)

        if failed_checks:
            LOGGER.info(u'Done checking user %s; %s check(s) failed.',
                        self, u', '.join(failed_checks))
        else:
            LOGGER.info(u'Done checking user %s.', self)

        return all_went_ok

    def get_absolute_url(self):
        return _("/users/{username}/").format(urlquote(self.username))

    def get_full_name(self):
        """ Returns the first_name plus the last_name, with a space in between.
        """
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        "Returns the short name for the user."
        return self.username

    # NOTE: self.email_user() comes from the AbstractUserProfile class


# ———————————————————————————————————————————————————————————————— User signals


def user_post_save(instance, **kwargs):
    """ Check the user. This will create all he/she needs. """

    user = instance

    if kwargs.get('created', False):
        user.check(force=True)


post_save.connect(user_post_save, sender=User)


# ————————————————————————————————————————————————————————— Configuration model


class Configuration(MPTTModel):

    """ Hierarchical key/value (de-)activable configuration system. """

    name = models.CharField(verbose_name=_(u'Name'),
                            max_length=128, unique=True)
    value = models.TextField(verbose_name=_(u'Value'),
                             null=True, blank=True)
    notes = models.TextField(verbose_name=_(u'Notes'),
                             null=True, blank=True)

    is_active = models.BooleanField(verbose_name=_(u'Is active'),
                                    default=True, blank=True)

    parent   = TreeForeignKey('self', null=True, blank=True,
                              related_name='children')

    class Meta:
        app_label = 'base'
        verbose_name = _(u'Configuration')
        verbose_name_plural = _(u'Configurations')

    def __unicode__(self):
        return self.name

    @classmethod
    def check_token(cls, token):
        """ Check if a token is valid or not.

        The method will lookup configuration records which icontain ``token``
        in their name, with the exact value of :param:`token`, and which are
        currently active.
        """

        try:
            cls.objects.get(name__icontains='token',
                            value=token, is_active=True)

        except cls.DoesNotExist:
            return False

        except:
            LOGGER.exception('Exception occured while checking token')
            return False

        else:
            return True


# ————————————————————————————————————————————————————————— Permission adapters


class OwnerOrSuperuserEditAdaptor(object):
    """ This is the custom adaptor for django-inplaceedit permissions.

        It will grant edit access if the current user is superuser or
        staff and he has NOT disabled the super_powers preference, or
        if the current user is the owner of the model instance being
        edited.

        .. note:: it makes some assumptions about beiing used with
            1flow models. Eg. it assumes the user will have a `.mongo`
            attribute, and that `obj` instance will have a `.owner`
            or `.user` attribute. Besides the `.mongo` attr, the
            others are quite common in all the apps I found until today.

    """

    @classmethod
    def obj_parent_chain(cls, obj, parent_chain):
        """ Return the last object of the parent-children chain.

        Eg. if we are authorizing on a class Child which has a Parent
        which has a GrandParent (which has a `.user` attribute), do
        equivalent of returning child.parent.grandparent.user, whatever
        the nesting level the chain is.
        """

        current_obj = obj

        for chain_node in parent_chain + ('user', ):
            current_obj = getattr(current_obj, chain_node)

        return current_obj


    @classmethod
    def can_edit(cls, adaptor_field):

        user = adaptor_field.request.user
        obj = adaptor_field.obj

        if user.is_anonymous():
            return False

        elif user.is_superuser:
            return True

        elif user.mongo.has_staff_access:
            return True

        else:
            try:
                if isinstance(obj, models.Model):
                    # We are editing a Django model. A user can be
                    # editing his own account, or one of its objects.
                    if hasattr(obj, 'INPLACEEDIT_PARENTCHAIN'):
                        pobj = cls.obj_parent_chain(
                            obj, obj.INPLACEEDIT_PARENTCHAIN)

                        return user == pobj

                    else:
                        return user == obj or user == obj.user

                else:
                    # We are editing a MongoDB Document. Either the it's
                    # user account object, or one of its own objects. In
                    # 1flow core, this is stated by either a `.owner`
                    # (which has my semantic preference) attribute, or a
                    # more classic `.user` (àla Django, used when the
                    # relation is not a real "ownership" but a simple
                    # N-N relation).
                    try:
                        return user == obj.django \
                            or user.mongo == obj.owner

                    except AttributeError:
                        # We don't try/except this one: it can crash with
                        # AttributeError for the same reason as the previous,
                        # but it will be catched by the outer try/except
                        # because we have nothing more to try, anyway.
                        return user == obj.django or user.mongo == obj.user

            except:
                LOGGER.exception(u'Exception while testing %s ownership on %s',
                                 user, obj)

            # This test is good for staff members,
            # but too weak for normal users.
            #can_edit = has_permission(obj, user, 'edit')

        return False
