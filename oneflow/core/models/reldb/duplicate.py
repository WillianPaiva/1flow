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

import inspect
import logging

from statsd import statsd
# from constance import config

from celery import task

# from django.conf import settings
from django.db import models
from django.db.models.loading import get_model
from django.utils.translation import ugettext_lazy as _
# from django.utils.text import slugify

# from oneflow.base.utils import register_task_method

from ..common import DUPLICATE_STATUS

LOGGER = logging.getLogger(__name__)


__all__ = [
    'AbstractDuplicateAwareModel',
    'abstract_replace_duplicate_task',
]


class AbstractDuplicateAwareModel(models.Model):

    """ Generic things to handle model instance duplicates. """

    class Meta:
        abstract = True
        app_label = 'core'

    # —————————————————————————————————————————————————————————————————— Fields

    duplicate_of = models.ForeignKey(
        'self', verbose_name=_(u'Duplicate of'), null=True, blank=True,
        help_text=_(u'This element is a duplicate of another, which is '
                    u'referenced here.'))

    duplicate_status = models.IntegerField(
        verbose_name=_(u'duplicate status'),
        null=True, blank=True,
        choices=DUPLICATE_STATUS.get_choices(),
        help_text=_(u'This status will be filled only if the current '
                    u'instance is a duplicate of another. See '
                    u'models/common.py for possible values and explanations.'))

    # ————————————————————————————————————————————————————————————————— Methods

    def register_duplicate(self, duplicate, force=False, background=True):
        """ Register an instance as a duplicate of the current one. """

        verbose_name = self._meta.verbose_name
        verbose_name_plural = self._meta.verbose_name_plural

        if duplicate.duplicate_of:
            if duplicate.duplicate_of != self:
                # NOTE: for Article, this situation can't happen IRL
                # (demonstrated with Willian 20130718).
                #
                # Any "second" duplicate *will* resolve to the master via the
                # redirect chain. It will *never* resolve to an intermediate
                # URL in the chain.
                #
                # For other objects it should happen too, because the
                # `get_or_create()` methods should return the `.duplicate_of`
                # attribute if it is not None.

                LOGGER.warning(u'%s %s is already a duplicate of '
                               u'another instance, not %s. Aborting.',
                               verbose_name, duplicate, duplicate.duplicate_of)
                return

        LOGGER.info(u'Registering %s %s as duplicate of %s…',
                    verbose_name, duplicate, self)

        # Register the duplication immediately, for other
        # background operations to use ourselves as value.
        duplicate.duplicate_of = self
        duplicate.duplicate_status = DUPLICATE_STATUS.NOT_REPLACED
        duplicate.save()

        statsd.gauge('%s.counts.duplicates' % verbose_name_plural,
                     1, delta=True)

        if background:
            LOGGER.info(u'Replacing %s %s by %s in the background…',
                        self._meta.verbose_name, duplicate, self)

            # NOTE: we don't directly transmit the model class
            # to ease with celery arguments serialization.
            return abstract_replace_duplicate_task.delay(
                self._meta.app_label, self._meta.object_name,
                self.id, duplicate.id)

        else:
            LOGGER.info(u'Replacing %s %s by %s in the foreground…',
                        self._meta.verbose_name, duplicate, self)

            return abstract_replace_duplicate_task(self._meta.app_label,
                                                   self._meta.object_name,
                                                   self.id, duplicate.id)

    def abstract_replace_duplicate(self, duplicate, abstract_model,
                                   field_name, many_to_many=False):
        """ Replace an instance of a model in concrete models of an abstract class.  # NOQA

        This method was first inplemented for tags, then refactored for
        languages.

        Returns False if *any* instance failed to replace the duplicate,
        True if *all* instances replaced it correctly, so that the caller
        can know if the replacing process must take place again or not.
        """

        if many_to_many:
            def replace_duplicate_in_field(instance, field_name,
                                           self, duplicate):
                field = getattr(instance, field_name)
                field.remove(duplicate)
                field.add(self)

        else:
            def replace_duplicate_in_field(instance, field_name,
                                           self, duplicate):
                setattr(instance, field_name, self)
                instance.save()

        base_instance_name = self._meta.verbose_name
        sub_classes = abstract_model.__subclasses__()
        sub_classes_count = len(sub_classes)

        LOGGER.info(u'Replacing duplicate %s %s by master %s '
                    u'in %s models (%s)…',
                    base_instance_name,
                    duplicate, self,
                    sub_classes_count,
                    u', '.join(m.__name__ for m in sub_classes))

        all_models_all_instances_count = 0
        all_models_all_failed_count = 0

        # Get all concrete classes that inherit from abstract_model
        for model in sub_classes:

            verbose_name = model._meta.verbose_name
            verbose_name_plural = model._meta.verbose_name_plural

            all_instances = model.objects.filter(**{field_name: duplicate})
            all_instances_count = all_instances.count()
            failed_instances_count = 0

            LOGGER.info(u'Replacing %s %s by %s in %s %s instances…',
                        base_instance_name,
                        duplicate, self,
                        all_instances_count, verbose_name)

            # For each concrete class, get each instance
            for instance in all_instances:

                try:
                    replace_duplicate_in_field(instance, field_name,
                                               self, duplicate)

                except:
                    failed_instances_count += 1
                    LOGGER.exception(u'Replacing %s %s by %s '
                                     u'failed in %s %s',
                                     base_instance_name,
                                     duplicate, self,
                                     verbose_name, instance)

            all_models_all_instances_count += all_instances_count
            all_models_all_failed_count += failed_instances_count

            LOGGER.info(u'Replaced %s %s by %s in %s %s (%s failed).',
                        base_instance_name,
                        duplicate, self,
                        all_instances_count - failed_instances_count,
                        verbose_name_plural,
                        failed_instances_count)

        LOGGER.info(u'Done replacing %s duplicate %s by %s in %s models: '
                    u'%s instances processed, %s failed.',
                    base_instance_name,
                    duplicate, self,
                    sub_classes_count,
                    all_models_all_instances_count,
                    all_models_all_failed_count)

        return all_models_all_failed_count == 0


# ——————————————————————————————————————————————————————————————————————— Tasks


@task(name='AbstractDuplicateAwareModel.replace_duplicate', queue='background')
def abstract_replace_duplicate_task(app_label, model_name, self_id, dupe_id):
    """ Call replace_duplicate() on all our concrete classes.

    .. note:: this task is forged manually because:
        - celery tasks as method are bugged as hell (and this is advertised).
        - AbstractDuplicateAwareModel is abstract thus we cannot use
          register_task_method() because we have no base model to do that on.

    .. todo:: refresh / simplify / update for Django 1.7
        cf. http://stackoverflow.com/a/26126935/654755
    """

    model = get_model(app_label, model_name)

    # Rehydrate instances
    self = model.objects.get(id=self_id)
    dupe = model.objects.get(id=dupe_id)

    dupe.duplicate_status = DUPLICATE_STATUS.REPLACING
    dupe.save()

    all_went_ok = True

    # http://stackoverflow.com/a/4094654/654755
    for base_class in inspect.getmro(self._meta.model):

        if base_class == AbstractDuplicateAwareModel:
            # This class will necessarily get brought by getmro(),
            # but obviously we don't want it: we are looking for
            # concrete classes only.
            continue

        try:
            verbose_name = base_class._meta.verbose_name

        except AttributeError:
            # Probably the “NewBase” class, or another special one.
            continue

        try:
            succeeded = base_class.replace_duplicate(self, dupe)

        except AttributeError:
            if base_class._meta.abstract:
                # We don't expect abstract classes
                # to implement replace_duplicate().
                continue

            if u'oneflow' in unicode(base_class):
                # This is likely a developper miss.

                raise NotImplementedError(
                    u'Model {0} has to implement a `replace_duplicate()` '
                    u'method.'.format(verbose_name))

        except:
            LOGGER.exception(u'Problem while running %s.replace_duplicate('
                             u'#%s, #%s)', model.__name__, self.id, dupe.id)
            all_went_ok = False

        if succeeded is None:
            raise NotImplementedError(
                u'Model {0}\'s `replace_duplicate()` method should return '
                u'True/False but not None!'.format(verbose_name))

        if not succeeded:
            all_went_ok = False

    if all_went_ok:
        dupe.duplicate_status = DUPLICATE_STATUS.FINISHED

    else:
        dupe.duplicate_status = DUPLICATE_STATUS.FAILED

    dupe.save()
