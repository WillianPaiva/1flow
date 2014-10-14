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
from collections import OrderedDict
from transmeta import TransMeta
from jsonfield import JSONField

from django.db import models
from django.utils.translation import ugettext_lazy as _

from mptt.models import MPTTModel, TreeForeignKey

LOGGER = logging.getLogger(__name__)


__all__ = ['WebSite', ]


def get_website_thumbnail_upload_path(instance, filename):

    if not filename.strip():
        filename = uuid.uuid4()

    # The filename will be used in a shell command later. In case the
    # user/admin forgets the '"' in the configuration, avoid problems.
    filename = filename.replace(u' ', u'_')

    if instance:
        return 'website/{0}/thumbnails/{1}'.format(instance.id, filename)

    return u'thumbnails/%Y/%m/%d/{0}'.format(filename)


class WebSite(MPTTModel):

    """ Web site object. Used to hold options for a whole website. """

    __metaclass__ = TransMeta

    name = models.Charfield(max_length=128, verbose_name=_(u'name'))
    slug = models.Charfield(max_length=128, verbose_name=_(u'slug'))
    url  = models.URLField(unique=True, verbose_name=_(u'url'))
    parent = TreeForeignKey('self', null=True, blank=True,
                            related_name='children')

    duplicate_of = models.ForeignKey('self')

    # TODO: move this into WebSite to avoid too much parallel fetches
    # when using multiple feeds from the same origin website.
    fetch_limit_nr = models.IntegerField(
        default=config.website_FETCH_PARALLEL_LIMIT,
        verbose_name=_(u'fetch limit'),
        help_text=_(u'The maximum number of articles that can be fetched '
                    u'from the website in parallel. If less than {0}, do '
                    u'not touch: the workers have already tuned it from '
                    u'real-life results.').format(
                        config.FEED_FETCH_PARALLEL_LIMIT))

    mail_warned = JSONField(load_kwargs={'object_pairs_hook': OrderedDict})

    thumbnail = models.ImageField(
        verbose_name=_(u'Thumbnail'), null=True, blank=True,
        upload_to=get_website_thumbnail_upload_path,
        help_text=_(u'Use either thumbnail when 1flow instance hosts the '
                    u'image, or thumbnail_url when hosted elsewhere. If '
                    u'both are filled, thumbnail takes precedence.'))

    thumbnail_url  = models.URLField(
        verbose_name=_(u'Thumbnail URL'),
        help_text=_(u'Full URL of the thumbnail displayed in the feed '
                    u'selector. Can be hosted outside of 1flow.'))

    short_description = models.CharField(
        max_length=256, verbose_name=_(u'Short description'),
        help_text=_(u'Public short description of the feed, for '
                    u'auto-completer listing. Markdown text.'))

    description = models.TextField(
        verbose_name=_(u'Description'),
        help_text=_(u'Public description of the feed. Markdown text.'))

    class Meta:
        app_label = 'core'
        verbose_name = _(u'Web site')
        verbose_name_plural = _(u'Web sites')
        translate = ('short_description', 'description', )

    class MPTTMeta:
        order_insertion_by = ['name']

    def __unicode__(self):
        """ I'm __unicode__, pep257. """

        return u'%s #%s (%s)%s' % (self.name or u'<UNSET>', self.id, self.url,
                                   (_(u'(dupe of #%s)') % self.duplicate_of.id)
                                   if self.duplicate_of else u'')
