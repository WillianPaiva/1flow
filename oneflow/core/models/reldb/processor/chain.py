# -*- coding: utf-8 -*-
u"""
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
import six
import json
# import uuid
import logging

from statsd import statsd
from constance import config
from transmeta import TransMeta
# from json_field import JSONField
from celery.exceptions import SoftTimeLimitExceeded
from cacheops import cached

# from simple_history.models import HistoricalRecords

from django.conf import settings
from django.db import models, transaction
from django.db.models.signals import pre_save  # , post_save, pre_delete
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.utils.text import slugify

from mptt.models import MPTTModelBase, MPTTModel, TreeForeignKey
from sparks.django.models.mixins import DiffMixin
from sparks.foundations.utils import combine_dicts

from ..duplicate import AbstractDuplicateAwareModel
from ..language import Language

from ..common import DjangoUser as User  # ORIGINS,

from .category import ProcessorCategory
from .processor import Processor
from .exceptions import (
    InstanceNotAcceptedException,
    StopProcessingException,
    NeverProcessException,
)

# from error import ProcessingError


LOGGER = logging.getLogger(__name__)


__all__ = [
    'ProcessingChain',
    'run_processing_chains',
    'get_default_processing_chain_for',
]


# ————————————————————————————————————————————————————————————— Class & related


class AtomicOrNot(transaction.Atomic):

    """ """

    def __init__(self, real_transaction=False, using=None, savepoint=True):

        self.real_transaction = real_transaction

        transaction.Atomic.__init__(self, using, savepoint)

    def __enter__(self, *args, **kwargs):

        if self.real_transaction:
            return transaction.Atomic.__enter__(self, *args, **kwargs)

    def __exit__(self, *args, **kwargs):

        if self.real_transaction:
            return transaction.Atomic.__exit__(self, *args, **kwargs)


class ProcessingChainManager(models.Manager):

    """ Simple manager with natural keys support. """

    def get_by_natural_key(self, slug):
        """ Get by slug. """

        return self.get(slug=slug)


class ProcessingChainMeta(MPTTModelBase, TransMeta):

    """ This one follows the BaseFeedMeta idea. """

    pass


class ProcessingChain(six.with_metaclass(ProcessingChainMeta, MPTTModel,
                      DiffMixin, AbstractDuplicateAwareModel)):

    """ string processors chain model.

    Holds common data of a given chain of (m)any processors. Examples
    of famous chains:

        - configured equivalent of 1flow's historical default:
          - HTML2Text from URL.
          - Newspaper full.
          - breadbility full.
          - top_image extractor.

    """

    class Meta:
        app_label = 'core'
        verbose_name = _(u'Processing chain')
        verbose_name_plural = _(u'Processing chains')
        translate = ('short_description', 'description', )

    objects = ProcessingChainManager()

    name = models.CharField(
        max_length=128,
        verbose_name=_(u'Name'),
    )

    slug = models.CharField(
        max_length=128,
        verbose_name=_(u'slug'),
        null=True, blank=True,
        unique=True,
    )

    user = models.ForeignKey(User,
                             null=True, blank=True,
                             verbose_name=_(u'Creator'),
                             related_name='processor_chains')

    parent = TreeForeignKey('self', null=True, blank=True,
                            related_name='children')

    languages = models.ManyToManyField(
        Language, null=True, blank=True,
        related_name='processor_chains',
        help_text=_(u'The language(s) in which this processor can '
                    u'process content. Let empty (None/null) for any '
                    u'language or if not relevant.'),
    )

    categories = models.ManyToManyField(
        ProcessorCategory, null=True, blank=True,
        related_name='processor_chains',
        help_text=_(u'Any relevant categories. Helps reducing resources '
                    u'consumtion when looking up processing chains, and '
                    u'also helps staff members find chains to manage.')
    )

    is_active = models.BooleanField(default=True)

    applies_on = models.ManyToManyField(
        ContentType,
        null=True, blank=True,
        verbose_name=_(u'Applies on'),
        limit_choices_to={'app_label': 'core'},
        help_text=_(u'On which 1flow models can this chain run ? Not '
                    u'selecting any is like selecting all.'))

    short_description = models.CharField(
        null=True, blank=True,
        max_length=256, verbose_name=_(u'Short description'),
        help_text=_(u'Public short description of the feed, for '
                    u'auto-completer listing. Markdown text.'))

    description = models.TextField(
        null=True, blank=True,
        verbose_name=_(u'Description'),
        help_text=_(u'Public description of the feed. Markdown text.'))

    #
    # TODO: create a chain_representation as JSON that represents the
    #       chain.processors.order_by('position') and see if changed at
    #       every save(). This should be linked in ChainedItem.save()
    #       method too, to update the current very model. This will allow
    #       to revert to previous versions of the chain by reverting the
    #       ChainedItem instances of the current chain.
    #
    # ————————————————————————————————————————————————————————— Python & Django

    def __unicode__(self):
        """ I'm __unicode__, pep257. """

        return u'{0} ({1})'.format(self.name, self.id)

    def natural_key(self):
        """ Helps (de-)serialization. """

        return (self.slug, )

    # ————————————————————————————————————————————————————————————— Pproperties

    @property
    def websites_using_subset(self):
        """ Return a random subset of at most 3 websites using this chain. """

        return self.websites.all().order_by('?')[:3]

    # ——————————————————————————————————————————————————————————— Class methods

    @classmethod
    def for_model(cls, model):

        return cls.objects.filter(is_active=True).filter(
            applies_on__in=(ContentType.objects.get_for_model(model), None)
        )

    @property
    def parameters(self):
        """ Return true if any of our items accepts parameters. """

        return any(item.item.parameters
                   for item in self.chained_items.all())

    def accepts(self, instance, **kwargs):
        """ Return True if any of my items accepts instance. """

        verbose = kwargs.get('verbose', True)

        if verbose and settings.DEBUG:
            LOGGER.debug(u'%s [accepts]: testing %s %s…', self,
                         instance._meta.verbose_name, instance.id)

        # See run() for implementation informations.
        for item in self.chained_items.filter(
                is_active=True).order_by('position'):

            processor = item.item

            if not processor.is_active:
                if verbose:
                    LOGGER.warning(u'%s [accepts]: skipped inactive %s at '
                                   u'pos. %s.', self, processor, item.position)
                continue

            if processor.accepts(instance, **kwargs):
                if verbose and settings.DEBUG:
                    LOGGER.debug(u'%s [accepts]: accepted %s %s by '
                                 u'processor %s at pos. %s.', self,
                                 instance._meta.verbose_name, instance.id,
                                 processor, item.position)
                return True

        if verbose and settings.DEBUG:
            LOGGER.debug(u'%s [accepts]: NO processor accepted %s %s.',
                         self, instance._meta.verbose_name, instance.id)

        return False

    def must_abort(self, instance, verbose=True, force=False, commit=True):
        """ Return True if the current chain must not run.

        There are a lot of conditions in which it can run or abort:

            - the chain itself is currently inactive,
            - any of its categories is inactive,
            - the instance's :meth:`processing_must_abort`()
              method returns ``True``.

        In any of these cases (tested in this order), the chain will
        create a temporary processing error and will abort. The temporary
        error will be later queried by a catch-all task that will re-launch
        the aborted processings.
        """

        # The instance has reported it MUST NEVER be processed with this chain.
        # This happens when it's a duplicate item, which can be quite common.
        if instance.processing_errors.filter(
                is_temporary=False, chain=self).exists():
            LOGGER.error(u'%s: %s %s must not be processed at all, aborting.',
                         self, instance._meta.verbose_name, instance.id)
            return True

        chain_must_abort = False

        if not self.is_active:
            LOGGER.warning(u'%s: currently inactive, aborting.', self)
            chain_must_abort = True

        if self.categories.filter(is_active=False).exists():
            LOGGER.warning(u'%s: in at least one currently inactive '
                           u'category, aborting.', self)
            chain_must_abort = True

        try:
            if instance.processing_must_abort(force=force, commit=commit):
                LOGGER.warning(u'%s %s is not processable yet, aborting.',
                               instance._meta.verbose_name, instance.id)
                chain_must_abort = True

        except NeverProcessException, e:
            instance.processing_errors.create(
                chain=self, is_temporary=False,
                exception=unicode(e)
            )
            return True

        if chain_must_abort:
            if not instance.processing_errors.filter(chain=self).exists():
                instance.processing_errors.create(
                    chain=self, is_temporary=True,
                    # no particular `exception` field, it's a temporary error.
                )

        return chain_must_abort

    def record_instance_error(self, instance, processor, exception):
        """ create a processing error on an instance for a processor.

        .. note:: this will update statsd appropriately.
        """

        try:
            instance.processing_errors.create(
                processor=processor,
                is_temporary=True,
                exception=unicode(exception))

        except:
            LOGGER.exception(u'%s: could not create processing error '
                             u'on %s %s with %s (exc. was: %s)', self,
                             instance._meta.verbose_name, instance.id,
                             processor, unicode(exception))

        else:
            self.update_statsd_errors_count(processor, instance, 1)

    def update_statsd_errors_count(self, processor, instance, delta_value):
        """ Send statsd delta_value for workflow processor categories. """

        # We don't report stats errors for chains, only processors.
        # For chains this would mean too much false-positive stats,
        # they can have too many categories.
        if isinstance(processor.item, Processor):

            workflow_categories = processor.item.categories.exclude(
                # Sorry for this too-bare selector.
                # It's the simplest way for now.
                slug__contains=u'-')

            if workflow_categories.exists():
                # Graphite will complain (or ignore)
                # if there are spaces in the name.
                plural_name = slugify(
                    instance._meta.verbose_name_plural.lower())

                with statsd.pipeline() as spipe:
                    for category in workflow_categories.all():
                        spipe.gauge(
                            '{0}.counts.{1}_errors'.format(
                                plural_name,
                                category.slug),
                            delta_value, delta=True)

    def clear_previous_errors(self, instance, processors, verbose=True):
        """ clear all instance errors related to some processors.

        .. note:: this will update statsd appropriately.
        """

        # This should select only temporary errors, because definitive
        # ones have a `chain` field but no `processor`.
        previous_errors = instance.processing_errors.filter(
            processor__in=processors)

        if previous_errors.exists():
            errors_count = previous_errors.count()

            for processor in processors:
                self.update_statsd_errors_count(processor, instance, -1)

            previous_errors.delete()

            if verbose:
                LOGGER.info(u'%s: cleared now-obsolete previous %s '
                            u'error(s).', self, errors_count)

    def process(self, instance, verbose=True, force=False,
                commit=True, parameters=None):
        """ Run the processing chain on a given instance.

        The chain takes care of input types, argument passing and exceptions.
        Its processors will do the dirty work and update the instance if it's
        in their attribution.

        The chain process() methods has transaction management, at every
        depth level (chains running chains running chains…).
        """

        if verbose and settings.DEBUG:
            LOGGER.debug(u'%s [run]: processing %s %s…', self,
                         instance._meta.verbose_name, instance.id)

        all_went_ok = True

        if self.must_abort(instance=instance, verbose=verbose,
                           force=force, commit=commit):
            return

        @cached(timeout=60 * 60)
        def _processor_categories_slugs(processor):

            return processor.categories.all().values_list('slug', flat=True)

        fine_grained_transactions = config.PROCESSING_FINE_GRAINED_TRANSACTIONS

        # We cannot filter directly on item__is_active=True
        # because of the generic relation. Too bad.
        processors = self.chained_items.filter(
            is_active=True).order_by('position').prefetch_related(
            'item', 'item__categories'
        )

        for item in processors:

            #
            # HEADS UP: "item" can hold a processor or another chain.
            #           They behave the same. The item.item is the
            #           processor or the chain itself.
            #
            processor = item.item

            # We filtered the chained items on is_active (this means
            # “is processor X active IN THIS CHAIN”. But now we need
            # to ask “is the processor X active at the global level?”
            # until there is a way to forward back-and-forth active
            # status of processors and chains between the global level
            # and the position-chained level.
            if not processor.is_active:
                if verbose:
                    LOGGER.warning(u'%s [run]: skipped inactive %s at '
                                   u'pos. %s.', self, processor, item.position)
                continue

            parameters = parameters or combine_dicts(
                item.parameters or {},

                # As documented in combine_dicts, the instance parameters
                # will take precedence and overwrite the processor ones
                # because they are in second position. This is a cascade.
                instance.processing_parameters,
            )

            if 'transactions_depth_level' in parameters:
                parameters['transactions_depth_level'] += 1

            else:
                parameters['transactions_depth_level'] = 0

            if isinstance(processor, Processor):
                # NOTE: Skipping if `process_category=False` is only valid for
                # processors. We cannot skip chains, because even if they are
                # tagged with category X, some of their processors can still
                # process other things. And BTW, the chain itself will not
                # alter the instance, only processors will.
                for category in _processor_categories_slugs(processor):
                    if not parameters.get('process_{0}'.format(category),
                                          True):
                        if verbose:
                            LOGGER.warning(u'%s [run]: skipped processor %s at '
                                           u'pos. %s, bypassed by parameters.',
                                           self, processor, item.position)
                        continue

            if verbose and settings.DEBUG:
                LOGGER.debug(u'%s [run]: running %s at pos. %s, verbose=%s, '
                             u'force=%s, commit=%s with parameters=%s.',
                             self, processor, item.position,
                             verbose, force, commit, parameters)

            try:
                with AtomicOrNot(real_transaction=fine_grained_transactions):
                    try:
                        # This will run accepts() automatically.
                        processor.process(
                            instance,
                            # parameters must be a dict(); if not
                            # set in the chained item, it can be
                            # None, which can crash process code.
                            parameters=parameters,
                            verbose=verbose,
                            force=force,
                            commit=commit
                        )

                    except InstanceNotAcceptedException:
                        # Don't make transaction.atomic() fail for that.
                        continue

                    except StopProcessingException:
                        # Don't make transaction.atomic() fail for
                        # that, it would wipe what was already done.
                        LOGGER.info(u'%s [run]: stopping processing of '
                                    u'%s %s after %s, on explicit stop '
                                    u'request.',
                                    self, instance._meta.verbose_name,
                                    instance.id, processor)
                        break

            except SoftTimeLimitExceeded as e:
                LOGGER.error(u'%s: runtime took too long for %s #%s, '
                             u'stopped while running %s (transaction '
                             u'was rolled back, instance left intact).',
                             self, instance._meta.verbose_name,
                             instance.id, processor)

                # NOTE: we record the chained item, not the processor itself,
                # else we don't know in which chain the processing failed.
                # Only the processor is not sufficient, because we don't know
                # what happened before it in the chain.
                self.record_instance_error(instance, item, e)
                all_went_ok = False
                break

            except Exception as e:
                LOGGER.exception(u'%s [run]: processing %s %s with %s '
                                 u'failed (transaction was rolled back, '
                                 u'instance left intact).', self,
                                 instance._meta.verbose_name,
                                 instance.id, processor)

                # See previous comment about same call to save_error().
                self.record_instance_error(instance, item, e)
                all_went_ok = False
                break

        if all_went_ok:

            self.clear_previous_errors(instance, processors, verbose=verbose)

        if verbose:
            LOGGER.info(u'%s [run]: processed %s %s.', self,
                        instance._meta.verbose_name, instance.id)

    def to_json(self):
        """ Return a JSON representation of the current chain.

        This JSON representation is used in processing errors to store
        how the chain was configured at the time of the error.
        """

        return json.dumps({
            'chain': self.id,
            'processors': [
                cp.processor_id for cp in self.processors.order_by('position')
            ]
        })

# ————————————————————————————————————————————————————————————————————— Signals


def processor_chain_pre_save(instance, **kwargs):
    """ Do pre_save work. """

    if instance.slug is None or instance.slug.strip() == u'':
        instance.slug = slugify(instance.name)


# def processor_chain_post_save(instance, **kwargs):
#     """ Do post_save work. """

#     if kwargs.get('created', False):
#         return


pre_save.connect(processor_chain_pre_save, sender=ProcessingChain)
# post_save.connect(processor_chain_post_save, sender=ProcessingChain)


# —————————————————————————————————————————————————————————— exported functions


def run_processing_chains(instance, verbose=True, force=False, commit=True):
    """ Run compatible processing chains on one instance.

    There can be more than one chain that can apply on a given model. They
    will be all be run in turn. Generally speaking (at the time of the first
    implementation), this is not wanted. This function should be called with
    care.
    """

    for chain in ProcessingChain.for_model(instance._meta.model):
        chain.process(instance, verbose=verbose, force=force, commit=commit)


def get_default_processing_chain_for(model):
    """ Return ONE chain whose slug is “default” and applies on `model`.

    There should be only one chain with a slug “default” that applies on
    the :param:`model` parameter. If there is none, or more than one, this
    is a configuration error, and the appropriate Django exception will be
    raised (respectively `ObjectDoesNotExist` and `MultipleObjectsReturned`).
    """

    # This is intentional that we don't catch any exception here.

    # We need to forge the slug to be more elaborate than just "default",
    # because there will be a lot of "default" processing chains, given
    # the models. As the slug is unique, we must have a way to find them.
    default_slug = u'1fs-{0}-default'.format(model._meta.model_name)

    return ProcessingChain.for_model(model).get(slug=default_slug)
