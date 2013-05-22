# -*- coding: utf-8 -*-

import redis

from django.db import models
from mongoengine import fields
from django.conf import settings
from django.contrib.auth.models import User
#from django.utils.translation import ugettext as _

from .fields import ListField

REDIS = redis.StrictRedis(host='localhost', port=6379,
                          db=getattr(settings, 'REDIS_DB'))


class RelationalFeedback(models.Model):
    """ Adds the feedback abilitily to any DB object.

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
        """ Return either one or two lists of the Users (if :param:`resolve`
            is ``True``) or just their IDs.

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
                return (User.objects.filter(id__in=positive_list),
                        User.objects.filter(id__in=negative_list))

            return positive_list, negative_list

        else:
            ids = REDIS.smembers(score_key + '+' if positive else '-')

            if resolve:
                return User.objects.filter(id__in=ids)

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


class MongoEngineFeedback(models.Model):
    """ Adds the feedback abilitily to any MongoEngine Document.

        Stored in Redis for fastiness.

        Implement via 3 redis objects for every instance feedbacked:
            - an integer, the current score
            - a list of users who +ed the instance
            - a list of users who -ed the instance

        Only users IDs are stored in lists.
    """

    stored_feedback_score     = fields.IntField(default=0)
    stored_feedback_positives = fields.ListField()
    stored_feedback_negatives = fields.ListField()

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
        """ Return either one or two lists of the Users (if :param:`resolve`
            is ``True``) or just their IDs.

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
                return (User.objects.filter(id__in=positive_list),
                        User.objects.filter(id__in=negative_list))

            return positive_list, negative_list

        else:
            ids = REDIS.smembers(score_key + '+' if positive else '-')

            if resolve:
                return User.objects.filter(id__in=ids)

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
