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
from positions import PositionField

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.db.models.signals import pre_save, post_save

from sparks.django.models import ModelDiffMixin

# from django.utils.translation import ugettext as _
# from django.utils.text import slugify
# from sparks.django.models import ModelDiffMixin
# from oneflow.base.utils.dateutils import now

from common import DjangoUser  # , REDIS
from mailaccount import MailAccount

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
        max_length=10, default=u'store',
        choices=tuple(MATCH_ACTION_CHOICES.items()),
        help_text=_(u'Defines a global match action '
                    u'for all rules of the feed. You '
                    u'can override this value at the '
                    u'rule level, only for the ones '
                    u'you want.'))

    finish_action =  models.CharField(
        verbose_name=_(u'Finish action'),
        max_length=10, default=u'nothing',
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

    @classmethod
    def is_stream_url(self, url):
        """ Return ``True`` if :param:`url` is a mail stream URL. """

        return url.startswith(u'https://mailstream.{0}/'.format(
                              settings.SITE_DOMAIN))

    @property
    def stream_url(self):
        """ Return an URL suitable for use in our MongoDB Feed collection.

        .. warning:: if you change the way ``stream_url`` is generated,
            please update :meth:`queryset_from_stream_url` too.
        """

        return u'https://mailstream.{1}/{0}'.format(self.pk,
                                                    settings.SITE_DOMAIN)

    @classmethod
    def get_from_stream_url(cls, stream_url):
        """ Return a :class:`MailFeed` instance from a stream URL.

        The purpose of this method is to rassemble the stream_url
        creation/extraction processes in the current file, without
        duplicating code elsewhere.
        """

        return cls.objects.get(pk=int(stream_url.rsplit('/', 1)[-1]))

    def __unicode__(self):
        """ OMG, that's __unicode__, pep257. """

        return u'“{0}” of user {1}'.format(self.name, self.user)


class MailFeedRule(models.Model):

    """ Mail feed rule.

    A mail feed can have one or more rule.

    Each rule can apply to one or more mail accounts.

    If the account is null, the rule will apply to all accounts.
    """

    INPLACEEDIT_PARENTCHAIN = ('mailfeed', )

    HEADER_FIELD_CHOICES = OrderedDict((
        (u'subject', _(u'Subject')),
        (u'from', _(u'Sender')),
        (u'to', _(u'Receipient (To:, Cc: or Cci:)')),
        (u'list', _(u'Mailing-list')),
        (u'other', _(u'Other header (please specify)')),
    ))

    MATCH_TYPE_CHOICES = OrderedDict((
        (u'contains', _(u'contains')),
        (u'ncontains', _(u'does not contain')),
        (u'starts', _(u'starts with')),
        (u'nstarts', _(u'does not start with')),
        (u'ends', _(u'ends with')),
        (u'nends', _(u'does not end with')),
        (u'equals', _(u'strictly equals')),
        (u'nequals', _(u'is not equal to')),
        (u're_match', _(u'Manual regular expression')),
    ))

    mailfeed = models.ForeignKey(MailFeed)
    account = models.ForeignKey(MailAccount, null=True, blank=True,
                                verbose_name=_(u'Mail account'),
                                help_text=_(u"To apply this rule to all "
                                            u"accounts, just don't choose "
                                            u"any."))
    mailbox = models.CharField(verbose_name=_(u'Mailbox'),
                               max_length=255, default=u'INBOX',
                               null=True, blank=True)
    recurse_mailbox = models.BooleanField(verbose_name=_(u'Recurse mailbox'),
                                          default=True, blank=True)
    header_field = models.CharField(verbose_name=_(u'Header'),
                                    max_length=10, default=u'any',
                                    choices=tuple(HEADER_FIELD_CHOICES.items()),
                                    help_text=_(u"E-mail field on which the "
                                                u"match type is applied."))
    other_header = models.CharField(verbose_name=_(u'Other header'),
                                    max_length=255, null=True, blank=True,
                                    help_text=_(u"Specify here if you chose "
                                                u"“Other header” in previous "
                                                u"field."))
    match_type = models.CharField(verbose_name=_(u'Match type'),
                                  max_length=10, default=u'contains',
                                  choices=tuple(MATCH_TYPE_CHOICES.items()),
                                  help_text=_(u"Operation applied on the "
                                              u"header to compare with match "
                                              u"value."))
    match_value = models.CharField(verbose_name=_(u'Match value'),
                                   default=u'', max_length=1024,
                                   help_text=_(u"Examples: “Tweet de”, "
                                               u"“Google Alert:”. Can be "
                                               u"any text."))

    match_action = models.CharField(
        verbose_name=_(u'Action when matched'),
        max_length=10, null=True, blank=True,
        choices=tuple(MailFeed.MATCH_ACTION_CHOICES.items()),
        help_text=_(u'Choose nothing to execute '
                    u'action defined at the feed level.'))

    finish_action =  models.CharField(
        verbose_name=_(u'Finish action'),
        max_length=10, null=True, blank=True,
        choices=tuple(MailFeed.FINISH_ACTION_CHOICES.items()),
        help_text=_(u'Choose nothing to execute '
                    u'action defined at the feed level.'))

    # Used to have many times the same rule in different feeds
    clone_of = models.ForeignKey('MailFeedRule', null=True, blank=True)
    position = PositionField(collection='mailfeed', default=0, blank=True)

    class Meta:
        app_label = 'core'
        ordering = ('position', )

    def __unicode__(self):
        """ OMG, that's __unicode__, pep257. """

        return _(u'Rule #{2}: {3}, applied to {0} for MailFeed {1}').format(
            _(u'all accounts') if self.account is None
            else _(u'account {0}').format(self.account),
            self.mailfeed,
            self.id,
            _(u'{0} {1} “{2}” → {3} → {4}').format(
                self.other_header
                if self.header_field == u'other'
                else self.HEADER_FIELD_CHOICES[self.header_field],
                self.MATCH_TYPE_CHOICES[self.match_type],
                self.match_value,
                MailFeed.MATCH_ACTION_CHOICES.get(self.match_action,
                                                  _(u'feed default')),
                MailFeed.FINISH_ACTION_CHOICES.get(self.finish_action,
                                                   _(u'feed default')),
            ))


def mailfeed_pre_save(instance, **kwargs):
    """ Create a MongoDB feed if mailfeed was just created. """

    if not instance.pk:
        # We are creating a mail feed; the dirty
        # work will be handled by post_save().
        return

    # Imported here to avoid cycles.
    from ..nonrel import Feed

    feed = Feed.objects.get(url=instance.stream_url)

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

post_save.connect(mailfeed_post_save, sender=MailFeed)
pre_save.connect(mailfeed_pre_save, sender=MailFeed)
