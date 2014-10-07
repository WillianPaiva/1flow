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

import logging

from collections import OrderedDict

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.db.models.signals import pre_save, post_save, pre_delete

from sparks.django.models import ModelDiffMixin

# from django.utils.translation import ugettext as _
# from django.utils.text import slugify
# from sparks.django.models import ModelDiffMixin
# from oneflow.base.utils.dateutils import now

from common import DjangoUser  # , REDIS

LOGGER = logging.getLogger(__name__)


class MailFeed(ModelDiffMixin):

    """ Configuration of a mail-based 1flow feed. """

    MATCH_ACTION_CHOICES = OrderedDict((
        (u'store', _(u'store email in the feed')),
        (u'scrape', _(u'scrape email, extract links and fetch articles')),
        (u'scroarpe',
         _(u'do both, eg. store email and extract links / fetch articles')),
    ))

    FINISH_ACTION_CHOICES = OrderedDict((
        (u'nothing', _(u'leave e-mail untouched')),
        (u'markread', _(u'mark e-mail read')),
        (u'delete', _(u'delete e-mail')),
    ))

    name = models.CharField(max_length=255, verbose_name=_(u'Feed name'))
    user = models.ForeignKey(DjangoUser)
    is_public = models.BooleanField(verbose_name=_(u'Public'),
                                    default=True, blank=True,
                                    help_text=_(u'Can other 1flow users '
                                                u'subscribe to this feed?'))

    match_action =  models.CharField(
        verbose_name=_(u'Match action'),
        max_length=10, default=u'scrape',
        choices=tuple(MATCH_ACTION_CHOICES.items()),
        help_text=_(u'Defines a global match action '
                    u'for all rules of the feed. You '
                    u'can override this value at the '
                    u'rule level, only for the ones '
                    u'you want.'))

    finish_action =  models.CharField(
        verbose_name=_(u'Finish action'),
        max_length=10, default=u'markread',
        choices=tuple(FINISH_ACTION_CHOICES.items()),
        help_text=_(u'Defines a global finish action '
                    u'for all rules of the feed. You '
                    u'can override this value at the '
                    u'rule level, only for the ones '
                    u'you want.'))

    #
    # HEADS UP: 20141004, these fields are not used yet in the engine.
    #
    scrape_whitelist = models.CharField(
        null=True, blank=True, max_length=1024,
        verbose_name=_(u'Scrape whitelist'),
        help_text=_(u'Eventually refine URLs you want to scrape in '
                    u'the email body. Type a list of valid URLs '
                    u'patterns, and start with “re:” if you want '
                    u'to use a regular expression.'))

    scrape_blacklist = models.BooleanField(
        default=True, blank=True,
        verbose_name=_(u'Use scrape blacklist'),
        help_text=_(u'Use 1flow adblocker to avoid scrapeing '
                    u'email adds, unsubscribe links and the like.'))

    class Meta:
        app_label = 'core'

    # ——————————————————————————————————————————————————————————— Class methods

    @classmethod
    def is_stream_url(self, url):
        """ Return ``True`` if :param:`url` is a mail stream URL. """

        return url.startswith(u'https://mailstream.{0}/'.format(
                              settings.SITE_DOMAIN))

    @classmethod
    def get_from_stream_url(cls, stream_url):
        """ Return a :class:`MailFeed` instance from a stream URL.

        The purpose of this method is to rassemble the stream_url
        creation/extraction processes in the current file, without
        duplicating code elsewhere.
        """

        return cls.objects.get(pk=int(stream_url.rsplit('/', 1)[-1]))

    # —————————————————————————————————————————————————————————————— Properties

    @property
    def stream_url(self):
        """ Return an URL suitable for use in our MongoDB Feed collection.

        .. warning:: if you change the way ``stream_url`` is generated,
            please update :meth:`queryset_from_stream_url` too.
        """

        return u'https://mailstream.{1}/{0}'.format(self.pk,
                                                    settings.SITE_DOMAIN)

    @property
    def stream(self):
        """ Return the 1flow stream associated with the current mail feed. """

        # Imported here to avoid cycles.
        from ..nonrel import Feed

        return Feed.objects.get(url=self.stream_url)

    # —————————————————————————————————————————————————————————————————— Django

    def __unicode__(self):
        """ OMG, that's __unicode__, pep257. """

        return u'“{0}” of user {1}'.format(self.name, self.user)

    # ——————————————————————————————————————————————————————————————— Internals

    def get_new_entries(self, **kwargs):
        """ Return new mails from the current feed. """

        since = kwargs.get('modified')
        entries = []

        if self.account is None:
            accounts = self.user.mailaccount_set.filter(is_usable=True)

        else:
            accounts = [self.account]

        feed_rules = tuple(
            self.mailfeedrule_set.filter(is_valid=True).order_by('position')
        )

        for account in accounts:
            with account:
                # TODO: force account.update_mailboxes() ??
                # TODO: implement self.mailboxes usage

                for mailbox_name in account.mailboxes:
                    account.imap_select(mailbox_name)

                    for message in account.imap_search(since=since):
                        for rule in feed_rules:

                            if rule.match_message(message):
                                entries.append(message)
                                break


# ————————————————————————————————————————————————————————————————————— Signals


def mailfeed_pre_save(instance, **kwargs):
    """ Create a MongoDB feed if mailfeed was just created. """

    if not instance.pk:
        # We are creating a mail feed; the dirty
        # work will be handled by post_save().
        return

    feed = instance.stream

    instance_name = instance.name
    update_feed = {}
    update_subscription = False

    #
    # HEADS UP: we treat feed & subscriptions differently, because
    #           they both save() MailFeed instances. Given from where
    #           the is coming, we must decouple the processing, else
    #           the one not sending the save() will not be updated.
    #
    # HEADS UP: we use update() on MongoDB instances to avoid
    #           post_save() signals cycles between three models.
    #

    if 'name' in instance.changed_fields:
        update_subscription = True

        if instance_name != feed.name:
            update_feed['set__name'] = instance_name

    if 'is_public' in instance.changed_fields \
            and instance.is_public == feed.restricted:
        update_feed['set__restricted'] = not instance.is_public

    if update_feed:
        feed.update(**update_feed)

    if update_subscription:
        for subscription in feed.subscriptions:
            if subscription.user.django == instance.user \
                    and subscription.name != instance_name:
                # HEADS UP: we use update() to
                # avoid post_save() signals cycles.
                subscription.update(set__name=instance_name)


def mailfeed_post_save(instance, **kwargs):
    """ Create a MongoDB feed if mailfeed was just created. """

    # LOGGER.info('MailFeed post save for %s: %s', instance, kwargs)

    if kwargs.get('created', False):

        # Imported here to avoid cycles.
        from ..nonrel import Feed, Subscription

        feed = Feed(name=instance.name,
                    url=instance.stream_url,
                    site_url=u'http://' + settings.SITE_DOMAIN,
                    restricted=not instance.is_public,
                    good_for_use=True).save()

        LOGGER.info('Created Feed %s for MailFeed %s', feed, instance)

        Subscription.subscribe_user_to_feed(instance.user.mongo,
                                            feed, background=True)


def mailfeed_pre_delete(instance, **kwargs):
    """ Close Feed when mail feed is deleted. """

    feed = instance.stream

    # Deleting everything without warning users
    # seems not to be the best option for now.
    #
    # TODO: what if a creator wants to really delete
    # the feed with its history, for privacy concerns?
    #
    # for subscription in feed.subscriptions:
    #     subscription.delete()
    # feed.delete()

    feed.close(_(u'%s, creator of the mail feed, closed it.').format(
               instance.user))


post_save.connect(mailfeed_post_save, sender=MailFeed)
pre_save.connect(mailfeed_pre_save, sender=MailFeed)
pre_delete.connect(mailfeed_pre_delete, sender=MailFeed)
