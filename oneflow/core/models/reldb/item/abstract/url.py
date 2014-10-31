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

import logging

import requests

from bs4 import BeautifulSoup
from statsd import statsd
from constance import config

# from json_field import JSONField
# from celery import chain as tasks_chain

# from django.conf import settings
from django.db import models, IntegrityError
from django.utils.translation import ugettext_lazy as _
# from django.utils.text import slugify

from oneflow.base.utils import register_task_method
from oneflow.base.utils.http import clean_url
# from oneflow.base.utils.dateutils import now

from ...common import REQUEST_BASE_HEADERS
from ...website import split_url

from ..base import BaseItem

LOGGER = logging.getLogger(__name__)


__all__ = [
    'UrlItem',

    # tasks will be added by register_task_method()
]


# ————————————————————————————————————————————————————————————————————— Classes

class DuplicateUrl(models.Model):

    """ A simple model to store duplicates URLs pointing to real ones. """

    # We can have extremely long URLs, notably via
    # google which wraps the entire world in their URLs.
    url = models.URLField(max_length=784,
                          verbose_name=_(u'URL'),
                          primary_key=True)

    real_url = models.URLField(max_length=512,
                               verbose_name=_(u'Real URL'))

    @classmethod
    def resolve(cls, url, clean=False):
        """ return the real URL of :param:`url` if it is a dupe.

        Return ``None`` if not registered as duplicate.
        """

        if clean:
            url = clean_url(url)

        try:
            return cls.objects.get(url=url).values('real_url')

        except:
            return None

    @classmethod
    def record_duplicate(cls, dupe, real):
        """ Register :param:`dupe` as pointing to :param:`real`. """

        url = cls(url=dupe, real_url=real)
        url.save()


class UrlItem(models.Model):

    """ Abstract Item that knows how to handle an URL. """

    class Meta:
        abstract = True
        app_label = 'core'
        verbose_name = _(u'URL item')
        verbose_name_plural = _(u'URL items')

    url = models.URLField(unique=True,
                          max_length=512,
                          verbose_name=_(u'Public URL'))

    url_absolute = models.BooleanField(
        verbose_name=_(u'Absolute URL'),
        default=False, blank=True,
        help_text=_(u'The article URL has been successfully absolutized '
                    u'to its unique and final location.'))

    url_error = models.TextField(
        verbose_name=_(u'URL fetch error'),
        null=True, blank=True,
        help_text=_(u'Error when absolutizing the URL'))

    is_orphaned = models.BooleanField(
        verbose_name=_(u'Orphaned'),
        default=False, blank=True,
        help_text=_(u'This article has no public URL anymore, or is '
                    u'unfetchable for some reason.'))

    # —————————————————————————————————————————————————————————————— Properties

    @property
    def is_good(self):
        """ Return True if the current item is considered good. """

        #
        # NOTE: sync the conditions with @Feed.good_articles
        #       and core.views.read_with_endless_pagination::search
        #

        if self.is_orphaned:
            return False

        if not self.url_absolute:
            return False

        return True

    def absolutize_url_must_abort(self, force=False, commit=True):

        if config.ARTICLE_ABSOLUTIZING_DISABLED:
            LOGGER.info(u'Absolutizing disabled by configuration, aborting.')
            return True

        if self.url_absolute and not force:
            LOGGER.info(u'URL of article %s is already absolute!', self)
            return True

        if self.is_orphaned and not force:
            LOGGER.warning(u'Item %s is orphaned, absolutization aborted.',
                           self)
            return True

        if self.url_error:
            if force:
                self.url_error = u''

                if commit:
                    self.save()
            else:
                LOGGER.warning(u'Item %s already has an URL error, '
                               u'aborting absolutization (currently: %s).',
                               self, self.url_error)
                return True

        return False

    def absolutize_url_post_process(self, requests_response):

        url = requests_response.url

        try:
            proto, host_and_port, remaining = split_url(url)

        except ValueError:
            return url

        if 'da.feedsportal.com' in host_and_port:
            # Sometimes the redirect chain breaks and gives us
            # a F*G page with links in many languages "click here
            # to continue".
            bsoup = BeautifulSoup(requests_response.content)

            for anchor in bsoup.findAll('a'):
                if u'here to continue' in anchor.text:
                    return clean_url(anchor['href'])

            # If we come here, feed portal template has probably changed.
            # Developers should be noticed about it.
            LOGGER.critical(u'Feedsportal post-processing failed '
                            u'for article %s (no redirect tag found '
                            u'at address %s)!', self, url)

        # if nothing matched before, just clean the
        # last URL we got. Better than nothing.
        return clean_url(requests_response.url)

    def absolutize_url(self, requests_response=None, force=False, commit=True):
        """ Make the current article URL absolute.

        Eg. transform:

        http://feedproxy.google.com/~r/francaistechcrunch/~3/hEIhLwVyEEI/

        into:

        http://techcrunch.com/2013/05/18/hell-no-tumblr-users-wont-go-to-yahoo/ # NOQA
            ?utm_source=feeurner&utm_medium=feed&utm_campaign=Feed%3A+francaistechcrunch+%28TechCrunch+en+Francais%29 # NOQA

        and then remove all these F*G utm_* parameters to get a clean
        final URL for the current article.

        Returns ``True`` if the operation succeeded, ``False`` if the
        absolutization pointed out that the current article is a
        duplicate of another. In this case the caller should stop its
        processing because the current article will be marked for deletion.

        Can also return ``None`` if absolutizing is disabled globally
        in ``constance`` configuration.
        """

        # Another example: http://rss.lefigaro.fr/~r/lefigaro/laune/~3/7jgyrQ-PmBA/story01.htm # NOQA

        if self.absolutize_url_must_abort(force=force, commit=commit):
            return

        if requests_response is None:
            try:
                requests_response = requests.get(self.url,
                                                 headers=REQUEST_BASE_HEADERS)

            except requests.ConnectionError as e:
                statsd.gauge('articles.counts.url_errors', 1, delta=True)
                self.url_error = str(e)
                self.save()

                LOGGER.error(u'Connection failed while absolutizing URL or %s.',
                             self)
                return

        if not requests_response.ok or requests_response.status_code != 200:

            message = u'HTTP Error %s (%s) while resolving %s.'
            args = (requests_response.status_code, requests_response.reason,
                    requests_response.url)

            with statsd.pipeline() as spipe:
                spipe.gauge('articles.counts.orphaned', 1, delta=True)
                spipe.gauge('articles.counts.url_errors', 1, delta=True)

            self.is_orphaned  = True
            self.url_error = message % args
            self.save()

            LOGGER.error(message, *args)
            return

        #
        # NOTE: we could also get it eventually from r.headers['link'],
        #       which contains '<another_url>'. We need to strip out
        #       the '<>', and re-absolutize this link, because in the
        #       example it's another redirector. Also r.links is a good
        #       candidate but in the example I used, it contains the
        #       shortlink, which must be re-resolved too.
        #
        #       So: as we already are at the final address *now*, no need
        #       bothering re-following another which would lead us to the
        #       the same final place.
        #

        final_url = self.absolutize_url_post_process(requests_response)

        if final_url != self.url:

            # Just for displaying purposes, see below.
            old_url = self.url

            if self.url_error:
                statsd.gauge('articles.counts.url_errors', -1, delta=True)

            # Even if we are a duplicate, we came until here and everything
            # went fine. We won't need to lookup again the absolute URL.
            statsd.gauge('articles.counts.absolutes', 1, delta=True)
            self.url_absolute = True
            self.url_error    = u''

            self.url = final_url

            try:
                self.save()

            except IntegrityError as e:
                # LOGGER.exception(u'IntegrityError occured while saving %s',
                #                  final_url)

                original = self.objects.get(url=final_url)

                # Just to display the right "old" one in sentry errors and logs.
                self.url = old_url

                LOGGER.info(u'Item %s is a duplicate of %s, '
                            u'registering as such.', self, original)

                original.register_duplicate(self)
                return False

            # Any other exception will raise. This is intentional.
            else:
                LOGGER.info(u'Item %s (#%s) successfully absolutized URL '
                            u'from %s to %s.', self.title, self.id,
                            old_url, final_url)

        else:
            # Don't do the job twice.
            if self.url_error:
                statsd.gauge('articles.counts.url_errors', -1, delta=True)

            statsd.gauge('articles.counts.absolutes', 1, delta=True)
            self.update(set__url_absolute=True, set__url_error='')

        return True


# ———————————————————————————————————————————————————————————————— Celery Tasks

# HEADS UP: we need to register against BaseItem, because UrlItem is abstract
#           and cannot run .objects.get() in register_task_method().
register_task_method(BaseItem, UrlItem.absolutize_url,
                     globals(), queue=u'swarm', default_retry_delay=3600)
