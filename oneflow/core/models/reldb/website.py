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
import uuid
import logging

from statsd import statsd
from constance import config
from transmeta import TransMeta
from json_field import JSONField
from yamlfield.fields import YAMLField

from django.db import models, ProgrammingError
from django.db.models.signals import post_save, pre_save, pre_delete
from django.utils.translation import ugettext_lazy as _
from django.utils.text import slugify

from mptt.models import MPTTModelBase, MPTTModel, TreeForeignKey
from sparks.django.models.mixins import DiffMixin

from duplicate import AbstractDuplicateAwareModel
from oneflow.base.utils.http import split_url

from ..common import ORIGINS

from processor import ProcessingChain

LOGGER = logging.getLogger(__name__)


__all__ = [
    'WebSite',
    'SOCIAL_WEBSITES',
]


# ————————————————————————————————————————————————————————————— Class & related


def get_website_image_upload_path(instance, filename):

    if not filename.strip():
        filename = uuid.uuid4()

    # The filename will be used in a shell command later. In case the
    # user/admin forgets the '"' in the configuration, avoid problems.
    filename = filename.replace(u' ', u'_')

    if instance:
        return 'website/{0}/images/{1}'.format(instance.id, filename)

    return u'images/%Y/%m/%d/{0}'.format(filename)


class WebSiteMeta(MPTTModelBase, TransMeta):

    """ This one follows the BaseFeedMeta idea. """

    pass


class WebSite(six.with_metaclass(WebSiteMeta, MPTTModel,
              DiffMixin, AbstractDuplicateAwareModel)):

    """ Web site object. Used to hold options for a whole website. """

    class Meta:
        app_label = 'core'
        verbose_name = _(u'Web site')
        verbose_name_plural = _(u'Web sites')
        translate = ('short_description', 'description', )

    # HEADS UP: we exclude the URL from inplace_edit form, else the
    # Django URLField will always add a trailing slash to domain-only
    # websites while we remove them. This is probably a bug in our heads
    # (we shouldn't remove the trailing slash on domain-only URLs ?),
    # but we want it to work this way for now.
    #
    # For 'mail_warned', it's the traditional JSONField + inplace error.
    INPLACEEDIT_EXCLUDE = ['url', 'mail_warned', ]

    # class MPTTMeta:
    #     order_insertion_by = ['url']

    name = models.CharField(
        max_length=128,
        verbose_name=_(u'name'),
        null=True, blank=True
    )

    slug = models.CharField(
        max_length=128,
        verbose_name=_(u'slug'),
        null=True, blank=True
    )
    url  = models.URLField(unique=True, verbose_name=_(u'url'), blank=True)

    parent = TreeForeignKey('self', null=True, blank=True,
                            related_name='children')

    # TODO: move this into Website to avoid too much parallel fetches
    # when using multiple feeds from the same origin website.
    fetch_limit_nr = models.IntegerField(
        default=config.FEED_FETCH_PARALLEL_LIMIT,
        verbose_name=_(u'fetch limit'), blank=True,
        help_text=_(u'The maximum number of articles that can be fetched '
                    u'from the website in parallel. If less than {0}, do '
                    u'not touch: the workers have already tuned it from '
                    u'real-life results.').format(
                        config.FEED_FETCH_PARALLEL_LIMIT))

    mail_warned = JSONField(default=list, blank=True)

    date_created = models.DateTimeField(
        auto_now_add=True, db_index=True,
        verbose_name=_(u'Date added'),
        help_text=_(u'When the web site was added to the 1flow database.'))

    date_updated = models.DateTimeField(
        auto_now=True, verbose_name=_(u'Date updated'),
        help_text=_(u'When the web site was updated.'))

    image = models.ImageField(
        verbose_name=_(u'Image'), null=True, blank=True,
        upload_to=get_website_image_upload_path, max_length=256,
        help_text=_(u'Use either image when 1flow instance hosts the '
                    u'image, or image_url when hosted elsewhere. If '
                    u'both are filled, image takes precedence.'))

    image_url = models.URLField(
        null=True, blank=True, max_length=384,
        verbose_name=_(u'Image URL'),
        help_text=_(u'Full URL of the image displayed in the feed '
                    u'selector. Can be hosted outside of 1flow.'))

    short_description = models.CharField(
        null=True, blank=True,
        max_length=256, verbose_name=_(u'Short description'),
        help_text=_(u'Public short description of the feed, for '
                    u'auto-completer listing. Markdown text.'))

    description = models.TextField(
        null=True, blank=True,
        verbose_name=_(u'Description'),
        help_text=_(u'Public description of the feed. Markdown text.'))

    processing_chain = models.ForeignKey(ProcessingChain,
                                         null=True, blank=True,
                                         related_name='websites')

    processing_parameters = YAMLField(
        null=True, blank=True,
        verbose_name=_(u'Processing parameters'),
        help_text=_(u'Processing parameters for this website. '
                    u'Can be left empty. As they are more specific, '
                    u'the website parameters take precedence over the '
                    u'processors parameters, but will be overriden by '
                    u'feed-level or item-level processing parameters, '
                    u'if any. In YAML format (see '
                    u'http://en.wikipedia.org/wiki/YAML for details).'))

    # ————————————————————————————————————————————————————————— Python & Django

    def __unicode__(self):
        """ I'm __unicode__, pep257. """

        return u'%s #%s (%s)%s' % (self.name or u'WebSite', self.id, self.url,
                                   (_(u'(dupe of #%s)') % self.duplicate_of.id)
                                   if self.duplicate_of else u'')

    # ——————————————————————————————————————————————————————————— Class methods

    @classmethod
    def get_from_url(cls, url):
        """ Will get you the ``Website`` object from an :param:`url`.

        After having striped down the path part (eg.
        ``http://test.com/my-article`` gives you the web site
        ``http://test.com``, without the trailing slash).

        It will return ``None`` if the url is really bad.

        .. note:: unlike :meth:`get_or_create_website`, this method will
            harmonize urls: ``Website.get_from_url('http://toto.com')``
            and  ``Website.get_from_url('http://toto.com/')`` will give
            you back the same result. This is intended, to avoid
            duplication.

        """
        try:
            proto, host_and_port, remaining = split_url(url)

        except:
            LOGGER.exception(u'Unable to split url “%s”', url)
            return None

        base_url = '%s://%s' % (proto, host_and_port)

        try:
            website, _ = WebSite.objects.get_or_create(url=base_url)

        except:
            LOGGER.exception('Could not get or create website from url '
                             u'“%s” (via original “%s”)', base_url, url)
            return None

        return website


# ————————————————————————————————————————————————————————————————————— Signals


def website_pre_save(instance, **kwargs):
    """ Method meant to be run from a celery task. """

    website = instance

    if not website.slug:
        if website.name is None:
            try:
                proto, host_and_port, remaining = split_url(website.url)

            except:
                website.name = u'<UNKNOWN>'

            else:
                website.name = host_and_port.replace(u'_', u' ').title()

        website.slug = slugify(website.name)


def website_post_save(instance, **kwargs):

    if kwargs.get('created', False):
        statsd.gauge('websites.counts.total', 1, delta=True)


def website_pre_delete(instance, **kwargs):

    statsd.gauge('websites.counts.total', -1, delta=True)


pre_save.connect(website_pre_save, sender=WebSite)
post_save.connect(website_post_save, sender=WebSite)
pre_delete.connect(website_pre_delete, sender=WebSite)


# ————————————————————————————————————————————————————————————— Exported things


try:
    # Having these objects handy doesn't costs and avoids a DB lookup
    # when creating a bunch of authors.
    SOCIAL_WEBSITES = {
        ORIGINS.TWITTER: WebSite.get_from_url('https://twitter.com/'),
    }
except ProgrammingError:
    # WebSite schema changed and we are running a South/Django migration…
    pass
