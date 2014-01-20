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

import ast
import uuid
import redis

from jsonfield import JSONField
from transmeta import TransMeta

from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext as _
from django.utils.text import slugify

#from django.db.models import Q
#from django.db.models.aggregates import Count
#from django.utils import dateformat
#from django.contrib.sites.models import Site
#from django.template.defaultfilters import slugify

REDIS = redis.StrictRedis(host=settings.REDIS_HOST,
                          port=settings.REDIS_PORT,
                          db=settings.REDIS_DB)

DjangoUser = get_user_model()


class ListField(models.TextField):
    __metaclass__ = models.SubfieldBase
    description = "Stores a python list"

    def __init__(self, *args, **kwargs):
        super(ListField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        if not value:
            value = []

        if isinstance(value, list):
            return value

        return ast.literal_eval(value)

    def get_prep_value(self, value):
        if value is None:
            return value

        return unicode(value)

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return self.get_db_prep_value(value)


class Feedback(models.Model):
    """ Adds the feedback abilitily to any object.

        Stored in Redis for fastiness.

        Implement via 3 redis objects for every instance feedbacked:
            - an integer, the current score
            - a list of users who +ed the instance
            - a list of users who -ed the instance

        Only users IDs are stored in lists.
    """

    stored_feedback_score     = models.IntegerField(null=True)
    stored_feedback_positives = ListField(default=[])
    stored_feedback_negatives = ListField(default=[])

    class Meta:
        abstract = True

    def feedback_store_permanently(self):
        """ Meant to be run via a celery task, once a day or the like.
            Named after `*_permanently` to avoid confusion between
            `store` and `score`.
        """

        self.stored_feedback_score = self.score
        self.stored_feedback_positives, self.stored_feedback_negatives = \
            self.feedbacks()
        self.save()

    @property
    def feedback_key_base(self):
        return 'f:{0}:{1}'.format(self.__class__.__name__, self.id)

    @property
    def feedback_score(self):

        score = REDIS.get(self.feedback_key_base)

        if score is None:
            if self.stored_feedback_score is None:
                new_score = 0

            else:
                new_score = self.stored_feedback_score

            REDIS.set(score, new_score)

            return new_score

    def feedback_get(self, positive=None, resolve=False):
        """ Return either one or two lists of the DjangoUsers (
            if :param:`resolve` is ``True``) or just their IDs.

            :param positive: a boolean indicating if you want the user who
                provided positive or negative feedback on the current
                instance. Can be ``None`` (which is the default), in which
                case 2 lists are returned ``(positive, negative)``.
            :param resolve: a boolean defaulting to ``False``. If ``True``,
                returned  lists will
                contain :class:`~django.contrib.auth.models.User`
                instances, else only plain integer IDs will be returned.

        """

        score_key = self.feedback_key_base

        if positive is None:
            pipe = REDIS.pipeline()

            positive_list, negative_list = (
                pipe.smembers(score_key + '+').smembers(
                    score_key + '-').execute()
            )

            if resolve:
                return (DjangoUser.objects.filter(id__in=positive_list),
                        DjangoUser.objects.filter(id__in=negative_list))

            return positive_list, negative_list

        else:
            ids = REDIS.smembers(score_key + '+' if positive else '-')

            if resolve:
                return DjangoUser.objects.filter(id__in=ids)

            return ids

    def feedback_add(self, user, positive):

        score_key     = self.feedback_key_base
        feedback_list = score_key + '+' if positive else '-'
        feedback_neg  = score_key + '-' if positive else '+'

        if not REDIS.sadd(feedback_list, user.id):
            raise ValueError('Duplicate feedback for '
                             'user {0} on {1} #{2}'.format(
                                 user, self.__class__.__name__, self.id))

        pipe = REDIS.pipeline()

        if positive:
            pipe.incr(score_key)

        else:
            pipe.decr(score_key)

        pipe.srem(feedback_neg, user.id)
        pipe.sadd(feedback_list, user.id)

        pipe.execute()


class HierarchyManager(models.Manager):
    def get_roots(self):
        return self.get_query_set().filter(parent__isnull=True)


class Hierarchy(models.Model):
    """ Add the hierarchy ability to any other model. """

    parent = models.ForeignKey('self', null=True)

    tree = HierarchyManager()

    class Meta:
        abstract = True

    def get_children(self):
        return self._default_manager.filter(parent=self)

    def get_descendants(self):
        descs = set(self.get_children())
        for node in list(descs):
            descs.update(node.get_descendants())
        return descs


class NameAndSlug(models.Model):
    name = models.CharField(max_length=128)
    slug = models.CharField(max_length=128)

    class Meta:
        abstract = True


class Source(NameAndSlug):
    url         = models.URLField()
    description = models.CharField(max_length=2048)

    # TODO:
    #logo        = models.ImageField()


class Category(Hierarchy, NameAndSlug):
    class Meta:
        verbose_name_plural = _(u'Categories')


class Author(models.Model):
    name  = models.CharField(max_length=128)
    email = models.CharField(max_length=128)
    url   = models.URLField()


class Information(Feedback):
    """ Images are converted on the fly. """

    # TODO: finish this model
    source   = models.ForeignKey(Source, null=True)
    author   = models.ForeignKey(Author)
    content  = models.TextField()
    abstract = models.TextField()
    grows    = models.ManyToManyField(DjangoUser, through='Grow')
    category = models.ForeignKey(Category)

    # TODO: add different dates… (creation, … ??)

    # TODO: finish this field
    tags = JSONField()


def grow_default_public_status(grow):
    return grow.user.get_profile().default_public


class Grow(Feedback):
    """ user ∞ information

         can be seen as a “ read ”, but it's much more.
    """

    # TODO: finish this model
    information = models.ForeignKey(Information)
    user        = models.ForeignKey(DjangoUser)
    is_public   = models.BooleanField(default=grow_default_public_status)


class Comment(Feedback, Hierarchy):
    """ """

    user = models.ForeignKey(DjangoUser)
    grow = models.ForeignKey(Grow)


class HelpContent(models.Model):
    __metaclass__ = TransMeta

    label = models.CharField(_(u'Help section label'),
                             max_length=128, unique=True,
                             help_text=_(u'Any text. Will NOT show '
                                         u'anywhere, but is used to '
                                         u'distinguish sections from '
                                         u'one another.'))
    ordering = models.IntegerField(_(u'Ordering'), help_text=_(u'An integer '
                                   u'that will be used to order help sections '
                                   u'on the help page.'), default=0)
    active = models.BooleanField(default=True, help_text=_(u'is this help '
                                 u'section currently displayed on the '
                                 u'website?'))
    name    = models.CharField(_(u'Help section name'), max_length=128,
                               help_text=_(u'Any text. Will be the title '
                                           u'of the help section.'))
    content = models.TextField(_(u'Help section content'),
                               help_text=_(u'Any text. Entered as Markdown.'))

    def __unicode__(self):
        return _(u'{field_name}: {truncated_field_value}').format(
            field_name=self.label, truncated_field_value=self.content[:30]
            + (self.content[30:] and u'…'))

    @property
    def slug(self):
        return slugify(self.name) or uuid.uuid4().hex

    class Meta:
        app_label = 'core'
        ordering = ['ordering', 'id']
        translate = ('name', 'content', )
        verbose_name = _(u'Help section')
        verbose_name_plural = _(u'Help contents')
