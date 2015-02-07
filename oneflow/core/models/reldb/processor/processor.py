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

import re
import six
import copy
# import uuid
import logging

from statsd import statsd
from constance import config
from transmeta import TransMeta
# from json_field import JSONField
from collections import OrderedDict
from django.conf import settings
from django.db import models
from django.db.models.signals import pre_save  # , post_save, pre_delete
from django.utils.translation import ugettext_lazy as _
from django.utils.text import slugify
from django.contrib.contenttypes import generic

from mptt.models import MPTTModelBase, MPTTModel, TreeForeignKey
from sparks.django.models.mixins import DiffMixin
from sparks.foundations.classes import SimpleObject

from ..duplicate import AbstractDuplicateAwareModel
from ..language import Language

# from oneflow.base.utils.http import split_url

from ..common import DjangoUser as User  # ORIGINS,
from exceptions import ProcessorSecurityException, InstanceNotAcceptedException
from category import ProcessorCategory

LOGGER = logging.getLogger(__name__)


__all__ = [
    'Processor',
]


# ————————————————————————————————————————————————————————————— Class & related


class ProcessorMeta(MPTTModelBase, TransMeta):

    """ This one follows the BaseFeedMeta idea. """

    pass


class Processor(six.with_metaclass(ProcessorMeta, MPTTModel,
                DiffMixin, AbstractDuplicateAwareModel)):

    """ content processor model.

    A processor takes some input and does something with it.

    The input can be anything, from an URI string to a database model ID/klass.

    It can eventually return something if it's part of a processor chain,
    or can alter directly the model in some conditions (this needs more
    thinking and debate, at least for the security implications ?).

    Examples of processors :

    - 1flow's historical integrated processor:
            - does a requests.get() (URL → utf-8 HTML content)
            - html2text (utf-8 HTML → utf-8 Markdown)
            - if it fails, it wipes the HTML content, for next processor
              to find a clean context.

    - the "newspaper full" one:
        - does the download() and parse() at the same time.

    - the newspaper download() only (produces only HTML).

    - the breadability full processor.

    - the multipage finder processor:
      - requests.get() HTML,
      - inspects the HTML for pages links,
      - TODO: does it run the website default parser?
        Then how is the multipage launched? There seem to be a
        chichen-and-egg like question.
    """

    class Meta:
        app_label = 'core'
        verbose_name = _(u'Processor')
        verbose_name_plural = _(u'Processors')
        translate = ('short_description', 'description', )

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

    user = models.ForeignKey(
        User,
        null=True, blank=True,
        verbose_name=_(u'Creator'),
        related_name='processors'
    )

    maintainer = models.ForeignKey(
        User,
        null=True, blank=True,
        verbose_name=_(u'Maintainer'),
        related_name='maintained_processors'
    )

    parent = TreeForeignKey('self', null=True, blank=True,
                            related_name='children')

    categories = models.ManyToManyField(
        ProcessorCategory, null=True, blank=True, related_name='processors',
        help_text=_(u'Any relevant categories. Helps reducing resources '
                    u'consumtion when looking up processors, and '
                    u'also helps staff members find processors to manage.')
    )

    languages = models.ManyToManyField(
        Language, null=True, blank=True, related_name='processors',
        help_text=_(u'The language(s) in which this processor can '
                    u'process content. Let empty (None/null) for any '
                    u'language or if not relevant.'),
    )

    is_active = models.BooleanField(
        # False upon creation of an empty processor seemsa sane default.
        default=False,
        help_text=_(u'Indicates whether this processor is globally active '
                    u'or not, despite its active status in processor chains '
                    u'(this field takes precedence).'),
    )

    source_address = models.CharField(
        null=True, blank=True,
        max_length=384, verbose_name=_(u'Source address'),
        help_text=_(u'The processor home on the web, if any. A web URL, '
                    u'or a github short address.'))

    needs_parameters = models.BooleanField(
        default=False, blank=True, verbose_name=_(u'Needs parameters?'),
        help_text=_(u'Defaults to False; and indicates the processor does '
                    u'need some parameters specified to operate. '
                    u'See https://github.com/1flow/1flow/wiki/Processors '
                    u'for details.'))

    short_description = models.CharField(
        null=True, blank=True,
        max_length=256, verbose_name=_(u'Short description'))

    description = models.TextField(
        null=True, blank=True,
        verbose_name=_(u'Description'))

    requirements = models.TextField(
        null=True, blank=True, verbose_name=_(u'Requirements'),
        help_text=_(u'PIP-compatible requirements. Can be empty. See '
                    u'https://github.com/1flow/1flow/wiki/Processors '
                    u'for details.'))

    accept_code = models.TextField(
        blank=True, verbose_name=_(u'Accept source code'),
        help_text=_(u'See https://github.com/1flow/1flow/wiki/Processors '
                    u'for details.'))

    process_code = models.TextField(
        blank=True,
        verbose_name=_(u'Processing source code'),
        help_text=_(u'See https://github.com/1flow/1flow/wiki/Processors '
                    u'for details.'))

    chainings = generic.GenericRelation(
        # Using the model class would imply an import loop.
        'ChainedItem',
        content_type_field='item_type',
        object_id_field='item_id')

    # ————————————————————————————————————————————————————————— Python & Django

    def __unicode__(self):
        """ I'm __unicode__, pep257. """

        return u'{0} ({1})'.format(self.name, self.id)

    # ——————————————————————————————————————————————————————————— Class methods

    # ———————————————————————————————————————————————————————— Instance methods

    def update_changed_slug(self, old_slug, new_slug):
        """ Eventually update our code with the new slug if relevant.

        This method is called at `pre_save()` when a processor detects
        that its slug changed.
        """

        changed = False

        for attr_name in ('accept_code', 'process_code', 'requirements'):

            old_code = getattr(self, attr_name)

            if old_code is None:
                # Happens when a processor is beiing created
                # inactive and author didn't write any code yet.
                continue

            # pattern, repl, string
            new_code = re.sub(ur'''['"]{0}['"]'''.format(old_slug),
                              u"'{0}'".format(new_slug),
                              old_code, re.UNICODE)

            if new_code != old_code:
                setattr(self, attr_name, new_code)
                changed = True

        if changed:
            self.save()

            LOGGER.info(u'%s: updated code for changed slug %s → %s.',
                        self, old_slug, new_slug)

    def _internal_exec(self, code_to_run, instance, **kwargs):
        """ Create a local scope dict for pseudo-restricted exec calls. """

        from oneflow.core.models import reldb as core_models

        local_scope = OrderedDict({
            'instance': instance,

            # The communication tunnel between exec() and the processor.
            'data': SimpleObject(),

            # This will ship all exceptions, including ours.
            'models': core_models,

            # TODO: enhance the logger to match the documentation.
            'LOGGER': LOGGER,

            'statsd': statsd,

            'get_processor_by_slug': lambda x: Processor.objects.get(slug=x),

            # TODO: does copy really copy the LazySettingsObject?
            'settings': copy.copy(settings),
            'config': copy.copy(config),

            'verbose': kwargs.get('verbose', True),
            'force': kwargs.get('force', False),
            'commit': kwargs.get('commit', True),
        })

        function_string = """
def processor_function({0}):
{1}

data.result = processor_function({2})
""".format(
            u', '.join(local_scope.keys()),
            code_to_run.replace(u'\n', u'\n    '),
            u', '.join(u'%s=%s' % (k, k) for k in local_scope.keys()),
        )

        # LOGGER.info(u'Running: %s', len(function_string))

        exec function_string in {}, local_scope

        # LOGGER.info(u'Executed %s! Returning: %s', len(function_string),
        #             local_scope['data'].result)

        return local_scope['data'].result

    def security_check(self, only=None):
        """ Raise an exception if :param:`code` tries to do bad things.

        .. note:: it will only detect **obvious** things, and it's probably
            not clever enough, eg. I'm pretty sure it will also detect false
            positives.

        """

        def check_for_obvious_crap(code):
            """ This function will miss complexly hidden things.

            But it's a start.
            """

            raise NotImplementedError('BOOOOO')

            if u'import' in code:
                raise ProcessorSecurityException('%s: ', self)

        for code_type, code_text in (
            ('accept', self.accept_code),
            ('process', self.process_code),
        ):
            if only is None or only == code_type:
                check_for_obvious_crap(code_text)

    def accepts(self, instance, **kwargs):
        """ Return True/False if we can process this instance in its state. """

        # TODO: implement the config and uncomment this.
        #
        # if config.PROCESSOR_DYNAMIC_SECURITY_CHECK:
        #     self.security_check('accept')

        verbose = kwargs.get('verbose', True)

        if verbose and settings.DEBUG:
            LOGGER.debug(u'%s: testing acceptance of %s %s…', self,
                         instance._meta.verbose_name, instance.id)

        try:
            result = self._internal_exec(self.accept_code,
                                         instance, **kwargs)
        except:
            LOGGER.error(u'%s: exception while running accepts() code.', self)
            raise

        if verbose:
            if result:
                LOGGER.info(u'%s: ACCEPTED %s %s.', self,
                            instance._meta.verbose_name, instance.id)
            else:
                LOGGER.info(u'%s: REJECTED %s %s.', self,
                            instance._meta.verbose_name, instance.id)

        return result

    def process(self, instance, **kwargs):
        """ Process the instance, do something with it. """

        # TODO: implement the config and uncomment this.
        #
        # if config.PROCESSOR_DYNAMIC_SECURITY_CHECK:
        #     self.security_check('process')

        verbose = kwargs.get('verbose', True)

        accepted = self.accepts(instance, **kwargs)

        # LOGGER.info(u'%s >>> %s %s accepted=%s, verbose=%s, '
        #             u'force=%s, commit=%s.',
        #             self, instance._meta.verbose_name, instance.id,
        #             accepted, verbose, kwargs.get('force', False),
        #             kwargs.get('commit', True))

        if accepted:
            if verbose and settings.DEBUG:
                LOGGER.debug(u'%s: processing accepted %s %s…',
                             self, instance._meta.verbose_name, instance.id)

            try:
                result = self._internal_exec(self.process_code,
                                             instance, **kwargs)
            except:
                LOGGER.error(u'%s: exception while running process() code.',
                             self)
                raise

            if verbose:
                LOGGER.info(u'%s: processed %s %s.', self,
                            instance._meta.verbose_name, instance.id)

            return result

        if verbose:
            LOGGER.warning(u'%s: not processed %s %s (was rejected).',
                           self, instance._meta.verbose_name, instance.id)

        raise InstanceNotAcceptedException

# ————————————————————————————————————————————————————————————————————— Signals


def processor_pre_save(instance, **kwargs):
    """ Do pre_save work. """

    if instance.slug is None or instance.slug.strip() == u'':
        instance.slug = slugify(instance.name)

    # The following part must always come last, to
    # also detect automatic changes to the slug.

    diff = instance.diff

    if 'slug' in diff:

        LOGGER.info(u'%s: slug changed, updating other processors…', instance)

        old_slug = diff['slug'][0]
        new_slug = diff['slug'][1]

        for processor in instance._meta.model.objects.all():
            processor.update_changed_slug(old_slug, new_slug)


# def processor_post_save(instance, **kwargs):
#   """ Do post_save work. """
#
#     if kwargs.get('created', False):
#         return


pre_save.connect(processor_pre_save, sender=Processor)
# post_save.connect(processor_post_save, sender=Processor)
