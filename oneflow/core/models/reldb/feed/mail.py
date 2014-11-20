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
import json
import logging

from statsd import statsd
from constance import config

# from django.conf import settings
from django.db import models
from django.db.models.signals import pre_save, post_save, pre_delete
from django.utils.translation import ugettext_lazy as _
# from django.utils.text import slugify

from ..account import MailAccount

from base import (
    BaseFeedQuerySet,
    BaseFeedManager,
    BaseFeed,
    basefeed_pre_save,
)

from common import (
    MAIL_MATCH_ACTIONS,
    MAIL_FINISH_ACTIONS,
    MAIL_RULES_OPERATIONS,

    MAIL_MATCH_ACTION_DEFAULT,
    MAIL_FINISH_ACTION_DEFAULT,
    MAIL_RULES_OPERATION_DEFAULT,
)

LOGGER = logging.getLogger(__name__)


# —————————————————————————————————————————————————————————— Manager / QuerySet


def BaseFeedQuerySet_mail_method(self):
    """ Patch BaseFeedQuerySet to know how to return Twitter accounts. """

    return self.instance_of(MailFeed)

BaseFeedQuerySet.mail = BaseFeedQuerySet_mail_method


# ——————————————————————————————————————————————————————————————————————— Model


class MailFeed(BaseFeed):

    """ Configuration of a mail-based 1flow feed. """

    class Meta:
        app_label = 'core'
        verbose_name = _(u'e-mail feed')
        verbose_name_plural = _(u'e-mail feeds')

    objects = BaseFeedManager()

    #
    # HEADS UP: `.user` is inherited from BaseFeed.
    #

    account = models.ManyToManyField(
        MailAccount, null=True, blank=True,
        verbose_name=_(u'Mail accounts'), related_name='mail_feeds',
        help_text=_(u"To apply this rule to all accounts, "
                    u"just don't choose any."))

    #
    # TODO: implement mailboxes.
    #
    # mailbox = models.CharField(verbose_name=_(u'Mailbox'),
    #                            max_length=255, default=u'INBOX',
    #                            null=True, blank=True)
    # recurse_mailbox = models.BooleanField(verbose_name=_(u'Recurse mailbox'),
    #                                       default=True, blank=True)

    match_action = models.IntegerField(
        verbose_name=_(u'Match action'),
        default=MAIL_MATCH_ACTION_DEFAULT,
        choices=MAIL_MATCH_ACTIONS.get_choices(),
        help_text=_(u'Defines a global match action '
                    u'for all rules of the feed. You '
                    u'can override this value at the '
                    u'rule level, only for the ones '
                    u'you want.'))

    finish_action = models.IntegerField(
        verbose_name=_(u'Finish action'),
        default=MAIL_FINISH_ACTION_DEFAULT,
        choices=MAIL_FINISH_ACTIONS.get_choices(),
        help_text=_(u'Defines a global finish action '
                    u'for all rules of the feed. You '
                    u'can override this value at the '
                    u'rule level, only for the ones '
                    u'you want.'))

    rules_operation = models.IntegerField(
        verbose_name=_(u'Rules operation'),
        default=MAIL_RULES_OPERATION_DEFAULT,
        choices=MAIL_RULES_OPERATIONS.get_choices(),
        help_text=_(u'Condition between rules or rules groups.'))

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

    # ——————————————————————————————————————————————————————————— Class methods

    # —————————————————————————————————————————————————————————————— Properties

    # —————————————————————————————————————————————————————————————————— Django

    def __unicode__(self):
        """ OMG, that's __unicode__, pep257. """

        return u'MailFeed “{0}” of user {1} (#{2})'.format(
            self.name, self.user, self.id)

    # ——————————————————————————————————————————————————————————————— Internals

    def build_refresh_kwargs(self):
        """ Return a kwargs suitable for Email feed refreshing method. """

        return {
            'since': self.date_last_fetch
        }

    def process_email(self, email):
        """ Process an email as configured in the feed. """

        # store email
        #
        # hde it if configured to only parse content.
        #
        # parse content and fetch links

        return

    def refresh_must_abort_internal(self):
        """ Specific conditions where an e-mail feed should not refresh. """

        if config.FEED_FETCH_EMAIL_DISABLED:
            LOGGER.info(u'Email feed %s refresh disabled by dynamic '
                        u'configuration.', self)
            return True

        return False

    def refresh_feed_internal(self, force=False):
        """ Refresh a mail feed. """

        LOGGER.info(u'Refreshing mail feed %s…', self)

        feed_kwargs = self.build_refresh_kwargs()

        new_emails = 0
        duplicates = 0
        mutualized = 0

        for email in self.get_new_entries(**feed_kwargs):
            created = self.process_email(email)

            if created:
                new_emails += 1

            elif created is False:
                duplicates += 1

            else:
                mutualized += 1

        if new_emails == duplicates == mutualized  == 0:
            LOGGER.info(u'No new content in mail feed %s.', self)

        return new_emails, duplicates, mutualized

    def get_new_entries(self, **kwargs):
        """ Return new mails from the current feed. """

        def prepare_message(message, rules):

            # if __debug__:
            #     LOGGER.debug(u'>>> MATCH #%s FOUND '
            #                  u'by rule #%s:\n'
            #                  u'   Subject: %s\n'
            #                  u'      From: %s\n'
            #                  u'      Date: %s\n'
            #                  u'      Body: %s…\n'
            #                  u'  %s\n',
            #                  mailbox_matched + 1,
            #                  rule.pk,
            #                  message.get('subject'),
            #                  message.get('from'),
            #                  message.get('date'),
            #                  email_get_first_text_block(
            #                      message).strip().replace(
            #                      '\r', '').replace(
            #                      '\n', ' ')[:80],
            #                  rule)

            return {
                'email': message,
                'date': message.get('date', None),
                'meta': {
                    'processing': self.match_action,
                    # (rule.match_action or self.match_action)
                    'matched_rules': json.dumps([r.repr_for_json()
                                                for r in rules]),
                }
            }

        since = kwargs.get('since')

        # Freeze the QuerySet as tuple() for current run.
        # This avoids having a moving set of rules for each account.
        feed_rules = tuple(
            self.rules.filter(is_valid=True).order_by('group', 'position')
        )

        usable_accounts = self.user.accounts.mail().usable()

        rules_operation_any = self.rules_operation == MAIL_RULES_OPERATIONS.ANY

        total_matched   = 0
        total_unmatched = 0

        for account in usable_accounts:

            with account:
                account.update_mailboxes()

                #
                # TODO: implement feed.account.mailboxes specific usage here
                #

                account_matched   = 0
                account_unmatched = 0

                for mailbox_name in account.mailboxes:

                    account.imap_select(mailbox_name=mailbox_name)

                    mailbox_matched   = 0
                    mailbox_unmatched = 0

                    for message in account.imap_search_since(since=since):

                        matched = False
                        seen_groups = []

                        for rule in feed_rules:

                            if rule.group:
                                if rule.group in seen_groups:
                                    # The rule will return the match
                                    # result for its whole group. No
                                    # need to try others of the same.
                                    continue

                                else:
                                    seen_groups.append(rule.group)

                            if rule.match_message(message):

                                if rules_operation_any:

                                    yield prepare_message(message, [rule])
                                    matched = True
                                    break

                                else:
                                    matched = True
                                    # but continue, we need to match all

                            else:
                                if rules_operation_any:
                                    # nothing to do, next
                                    # rule will perhaps match.
                                    pass

                                else:
                                    # One rule/group of a “AND” set()
                                    # didn't match. Don't bother trying
                                    # others, it's dead pal.
                                    matched = False
                                    break

                        if matched:
                            mailbox_matched += 1
                            if not rules_operation_any:
                                yield prepare_message(message, feed_rules)

                            #
                            # TODO: implement final action
                            #       via generator send back.
                            #

                        else:
                            mailbox_unmatched += 1

                    account_matched   += mailbox_matched
                    account_unmatched += mailbox_unmatched

                    account.imap_close()

                    LOGGER.debug(u'Mailfeed %s: %s/%s email(s) matched in '
                                 u'mailbox %s of %s', self.name,
                                 mailbox_matched,
                                 mailbox_matched + mailbox_unmatched,
                                 mailbox_name, account)

                # end with account

            total_matched   += account_matched
            total_unmatched += account_unmatched

            LOGGER.info(u'Mailfeed %s: %s/%s email(s) matched in %s',
                        self.name, account_matched,
                        account_matched + account_unmatched,
                        account)

        LOGGER.info(u'Mailfeed %s: %s/%s email(s) matched in all accounts.',
                    self.name, total_matched,
                    total_matched + total_unmatched)


# ————————————————————————————————————————————————————————————————————— Signals
#
# HEADS UP: see subscription.py for other signals.
#


def mailfeed_pre_save(instance, **kwargs):
    """ Update owner's subscription name when mailfeed name changes. """

    mailfeed = instance

    if not mailfeed.pk:
        # The feed is beeing created.
        # The subscription doesn't exist yet.
        return

    if 'name' in mailfeed.changed_fields:
        # Push the name update from the mailfeed
        # to the owner's corresponding subscription.
        #
        # HEADS UP: we use filter()/update(), and not get()
        # even if are sure there is only one subscription,
        # to avoid a post_save() signal loop.
        #
        # TODO: refactor/merge this in BaseFeed, with a test
        # on feed.user to avoid crashing on feeds types other
        # than twitter/mail that are user-created.
        mailfeed.subscriptions.filter(
            user=mailfeed.user).update(name=mailfeed.name)


def mailfeed_post_save(instance, **kwargs):
    """ Increment stats. """

    if kwargs.get('created', False):
        statsd.gauge('feeds.counts.mail', 1, delta=True)


def mailfeed_pre_delete(instance, **kwargs):
    """ Decrement stats. """

    statsd.gauge('feeds.counts.mail', -1, delta=True)


# Because http://stackoverflow.com/a/24624838/654755 doesn't work.
pre_save.connect(basefeed_pre_save, sender=MailFeed)

pre_save.connect(mailfeed_pre_save, sender=MailFeed)
post_save.connect(mailfeed_post_save, sender=MailFeed)
pre_delete.connect(mailfeed_pre_delete, sender=MailFeed)
