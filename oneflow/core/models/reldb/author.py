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

import logging

from statsd import statsd
from json_field import JSONField

# from django.conf import settings
from django.db import models
from django.db.models.signals import post_save  # , pre_save, pre_delete
from django.utils.translation import ugettext_lazy as _

# from oneflow.base.utils import register_task_method

from common import DjangoUser as User
from website import WebSite

LOGGER = logging.getLogger(__name__)


__all__ = [
    'Author',
]


class Author(models.Model):

    """ An author, gathered from a website during crawling / indexing. """

    class Meta:
        app_label = 'core'
        verbose_name = _(u'Author')
        verbose_name_plural = _(u'Authors')
        unique_together = ('origin_name', 'website', )

    name = models.CharField(max_length=7168,
                            null=True, blank=True,
                            verbose_name=_(u'Name'))

    username = models.CharField(max_length=128,
                                null=True, blank=True,
                                verbose_name=_(u'Username (nick)'))

    website = models.ForeignKey(
        WebSite, verbose_name=_(u'Web site'), null=True, blank=True,
        help_text=_(u'Web site where this author was discovered.'))

    origin_name = models.CharField(
        max_length=7168, blank=True,
        verbose_name=_(u'name at original discover'),
        help_text=_(u'When trying to guess authors, we '
                    u'have only a "fullname" equivalent. We need to '
                    u'store it for future comparisons in case '
                    u'firstname and lastname get manually modified '
                    u'after author creation.'))

    origin_id = models.BigIntegerField(
        verbose_name=_(u'Numerical ID'),
        null=True, blank=True, db_index=True,
        help_text=_(u'ID on the original website, where available (eg. '
                    u'on social networks).'),
    )

    origin_id_str = models.CharField(
        verbose_name=_(u'Alphanumeric ID'), max_length=64,
        null=True, blank=True, db_index=True,
        help_text=_(u'ID on the original website (as characters), where '
                    u'available (eg. on social networks which do not offer '
                    u'integer IDs).'),
    )

    is_unsure = models.BooleanField(
        verbose_name=_(u'unsure identity'), default=False, blank=True,
        help_text=_(u'Set to True when the author '
                    u'has been found from its origin_name and '
                    u'not via email; because origin_name can '
                    u'be duplicated, but not emails.'))

    user = models.ForeignKey(
        User, null=True, blank=True,
        verbose_name=_('Creator'))

    users = models.ManyToManyField(
        User, null=True, blank=True,
        verbose_name=_('1flow accounts'), related_name='authors',
        help_text=_('1flow accounts linked to this author'))

    identities = models.ManyToManyField(
        'self', null=True, blank=True,
        verbose_name=_('Other identities'),
        help_text=_('Other authors elsewhere that are really the same person.'))

    website_data = JSONField(default=dict, blank=True)

    # XXX: shoud vanish when inheriting from the abstract duplicate model.
    duplicate_of = models.ForeignKey('self', null=True, blank=True)

    def __unicode__(self):
        """ pep257, YOU BORING ME. """

        if u'twitter' in self.website.url:
            # Verified icons: ∗ⓥ⊛◆◈✌✓✔
            return u'{0}{1} (@{2}) #{3}'.format(
                self.name,
                u'✔' if self.website_data.get('verified', False) else u'',
                self.username, self.origin_id)

        return u'{0}{1} #{2} for website {3}'.format(
            self.name or self.origin_name,
            _(u' (unsure)') if self.is_unsure else u'',
            self.id, self.website)

    # ——————————————————————————————————————————————————————————— Class-methods

    @classmethod
    def get_authors_from_feedparser_article(cls, feedparser_article,
                                            set_to_article=None):
        """ Extract author(s) from a feedparser article. """

        if set_to_article:
            # This is an absolutized URL, hopefully.
            article_url = set_to_article.url

        else:
            article_url = getattr(feedparser_article, 'link',
                                  '').replace(' ', '%20') or None

        if article_url:
            website = WebSite.get_from_url(article_url)

        else:
            LOGGER.critical(u'NO url, cannot get any author.')
            return []

        # Use a set() internally to avoid duplicates (seen a lot in RSS feeds).
        authors = set()

        if 'authors' in feedparser_article:
            # 'authors' can be [{}], which is useless.

            for author_dict in feedparser_article['authors']:
                author = cls.get_author_from_feedparser_dict(author_dict,
                                                             website)

                if author:
                    if set_to_article:
                        set_to_article.authors.add(author)

                    authors.add(author)

        if 'author_detail' in feedparser_article:
            author = cls.get_author_from_feedparser_dict(
                feedparser_article['author_detail'], website)

            if author:
                if set_to_article:
                    set_to_article.authors.add(author)

                authors.add(author)

        if 'author' in feedparser_article:
            author = cls.get_author_from_feedparser_dict(
                {'name': feedparser_article['author']}, website)

            if author:
                if set_to_article:
                    set_to_article.authors.add(author)

                authors.add(author)

        # Always return a list, else we hit
        # http://dev.1flow.net/development/1flow-dev/group/4026/
        return list(authors)

    @classmethod
    def get_author_from_feedparser_dict(cls, author_dict, website):
        """ Guess and get an author from a feedparser dictionnary. """

        email = author_dict.get('email', None)

        if email:
            # An email is less likely to have a duplicates than
            # a standard name. It takes precedence if it exists.

            author, created = cls.objects.get_or_create(origin_name=email,
                                                        website=website)

            return author

        home_page = author_dict.get('href', None)

        if home_page:
            # A home_page is less likely to have a duplicates than a standard
            # name too. It also takes precedence after email if it exists.

            author, created = cls.objects.get_or_create(origin_name=home_page,
                                                        website=website)

            if created:
                author.is_unsure = True
                author.save()

            return author

        origin_name = author_dict.get('name', None)

        if origin_name:

            author, created = cls.objects.get_or_create(origin_name=origin_name,
                                                        website=website)

            if created:
                author.is_unsure = True
                author.save()

            return author

        return None

    @classmethod
    def get_author_from_twitter_user(cls, twitter_user):
        """ Get or create an author from a Twitter user JSON structure. """

        # u'user': {
        #     u'contributors_enabled': False,
        #     u'created_at': u'Tue Nov 11 09:08:21 +0000 2014',
        #     u'default_profile': True,
        #     u'default_profile_image': True,
        #     u'description': None,
        #     u'favourites_count': 0,
        #     u'follow_request_sent': None,
        #     u'followers_count': 1,
        #     u'following': None,
        #     u'friends_count': 2,
        #     u'geo_enabled': False,
        #     u'id': 2872004451,
        #     u'id_str': u'2872004451',
        #     u'is_translation_enabled': False,
        #     u'is_translator': False,
        #     u'lang': u'fr',
        #     u'listed_count': 0,
        #     u'location': u'',
        #     u'name': u'1flow.io data stream',
        #     u'notifications': None,
        #     u'profile_background_color': u'C0DEED',
        #     u'profile_background_image_url':
        #       u'http://abs.twimg.com/images/themes/theme1/bg.png',
        #     u'profile_background_image_url_https':
        #       u'https://abs.twimg.com/images/themes/theme1/bg.png',
        #     u'profile_background_tile': False,
        #     u'profile_image_url':
        #       u'http://abs.twimg.com/sticky/default_profile_images/default_profile_1_normal.png',  # NOQA
        #     u'profile_image_url_https':
        #       u'https://abs.twimg.com/sticky/default_profile_images/default_profile_1_normal.png',  # NOQA
        #     u'profile_link_color': u'0084B4',
        #     u'profile_location': None,
        #     u'profile_sidebar_border_color': u'C0DEED',
        #     u'profile_sidebar_fill_color': u'DDEEF6',
        #     u'profile_text_color': u'333333',
        #     u'profile_use_background_image': True,
        #     u'protected': False,
        #     u'screen_name': u'1flow_io_data',
        #     u'statuses_count': 6,
        #     u'time_zone': u'Paris',
        #     u'url': None,
        #     u'utc_offset': 3600,
        #     u'verified': False
        # }

        twitter_ws = WebSite.get_from_url(u'https://twitter.com')

        username = twitter_user.get('screen_name', twitter_user['id_str'])

        # Sometimes 'name' is not available (seen 20141127)
        # http://dev.1flow.net/development/1flow-dev/group/48650/
        name = twitter_user.get('name', username)

        author, created = cls.objects.get_or_create(
            origin_id=twitter_user['id'],
            website=twitter_ws,
            defaults={
                'name': name,
                'username': username,
                'website_data': twitter_user,
                'is_unsure': False,

                # For index uniqueness purposes only.
                'origin_name': twitter_user['id_str'],
            }
        )

        if created:
            LOGGER.info(u'Created Twitter author %s.', author)

        return author


# ————————————————————————————————————————————————————————————————————— Signals


def author_post_save(instance, **kwargs):

    if not kwargs.get('created', False):
        return

    statsd.gauge('authors.counts.total', 1, delta=True)


post_save.connect(author_post_save, sender=Author)
