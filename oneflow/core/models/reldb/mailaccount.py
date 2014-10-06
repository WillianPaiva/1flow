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

import imaplib
import logging

from collections import OrderedDict
from constance import config

from django.db import models
from django.utils.translation import ugettext_lazy as _
# from django.utils.text import slugify

from ....base.fields import TextRedisDescriptor
from ....base.utils import register_task_method

from sparks.django.models import ModelDiffMixin

from oneflow.base.utils.dateutils import now, timedelta

from common import long_in_the_past, DjangoUser  # , REDIS

LOGGER = logging.getLogger(__name__)

__all__ = [
    'mailaccount_mailboxes_default',
    'MailAccount',
]


def mailaccount_mailboxes_default(mailaccount):
    """ Build a MailAccount mailboxes default value. """

    try:
        return mailaccount.imap_list_mailboxes(as_text=True)

    except:
        return u''


class MailAccount(ModelDiffMixin):

    """ 1flow users can configure many mail accounts.

    1flow create feeds from them.
    """

    MAILBOXES_STRING_SEPARATOR = u'~|~'

    MAILBOXES_BLACKLIST = (
        'INBOX.Drafts',
        'INBOX.Trash',
        'INBOX.Sent Messages',
        'INBOX.Sent',
        'INBOX.Spam',
        'INBOX.Junk',
        'INBOX.INBOX.Junk',
        'INBOX.Deleted Messages',

        _(u'INBOX.Drafts'),
        _(u'INBOX.Trash'),
        _(u'INBOX.Sent Messages'),
        _(u'INBOX.Sent'),
        _(u'INBOX.Spam'),
        _(u'INBOX.Junk'),
        _(u'INBOX.INBOX.Junk'),
        _(u'INBOX.Deleted Messages'),

    )

    MAILBOXES_COMMON = OrderedDict((
        (u'INBOX', _(u'Inbox')),
    ))

    # NOTE: MAILBOXES_BLACKLIST is in MailAccount.

    user = models.ForeignKey(DjangoUser)
    name = models.CharField(verbose_name=_(u'Account name'),
                            max_length=128, blank=True)

    # cf. http://en.wikipedia.org/wiki/Hostname
    hostname = models.CharField(verbose_name=_(u'Server hostname'),
                                max_length=255)

    use_ssl = models.BooleanField(verbose_name=_(u'Use SSL/TLS?'),
                                  default=True, blank=True)
    port = models.IntegerField(verbose_name=_(u'Service port'),
                               null=True, blank=True)
    username = models.CharField(verbose_name=_(u'Username'),
                                max_length=255, blank=True)
    password = models.CharField(verbose_name=_(u'Password'),
                                max_length=255, default=u'', blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_last_conn = models.DateTimeField(default=long_in_the_past)
    conn_error = models.CharField(max_length=255, default=u'', blank=True)
    is_usable = models.BooleanField(default=True, blank=True)

    _mailboxes_ = TextRedisDescriptor(
        attr_name='ma.mb', default=mailaccount_mailboxes_default,
        set_default=True)

    class Meta:
        app_label       = 'core'
        unique_together = ('user', 'hostname', 'username', )

    @property
    def mailboxes(self):
        """ Return a list of mailboxes of the account.

        If it was refreshed too long in the past, rebuild the list.
        """
        _mailboxes_ = self._mailboxes_

        if not self.recently_usable or not _mailboxes_:
            # HEADS UP: this task name will be registered later
            # by the register_task_method() call.
            mailaccount_update_mailboxes_task.delay(self.pk)

        if not _mailboxes_:
            return []

        return _mailboxes_.split(self.MAILBOXES_STRING_SEPARATOR)

    @property
    def recently_usable(self):
        """ Return True if the account has been tested/connected recently. """

        return self.is_usable and (
            now() - self.date_last_conn
            < timedelta(seconds=config.MAIL_ACCOUNT_REFRESH_PERIOD))

    def update_mailboxes(self):
        """ Simply update the remote mailboxes names.

        .. note:: this method is registered as a task in Celery.
        """

        self._mailboxes_ = mailaccount_mailboxes_default(self)

        LOGGER.info(u'%s mailboxes list updated.', self)

    def save(self, *args, **kwargs):
        """ Automatically add a name/username if none is given. """

        if self.username is None or self.username.strip() == u'':
            self.username = self.user.username

        if self.name is None or self.name.strip() == u'':
            self.name = u'{0}@{1}'.format(self.username, self.hostname)

        if self.password is None:
            self.password = u''

        # Keep them before save(), they will reset
        changed_fields = self.changed_fields
        previous_pk = self.pk

        if 'hostname' in changed_fields \
            or 'username' in changed_fields \
            or 'password' in changed_fields \
            or 'use_ssl' in changed_fields \
                or 'port' in changed_fields:
            self.reset_unusable(commit=False)

        super(MailAccount, self).save(*args, **kwargs)

        # We must test the PK *after* save(), else the task
        # in reset_unusable() will be run with pk = None…
        if previous_pk is None:
            self.reset_unusable()

    def __unicode__(self):
        """ OMG, that's __unicode__, pep257. """

        return u'Mail account “{0}” of user {1}'.format(self.name, self.user)

    def get_port(self):
        """ Return the IMAP connection port, with default values if unset. """

        if self.port is None:
            if self.use_ssl:
                return 993
            return 143
        return self.port

    def reset_unusable(self, commit=True):
        """ Mark the current instance needing to test usability.

        This is called typically when a connection parameter has changed,
        and the current account connectivity needs to be tested again to
        validate them all.
        """

        self.date_last_conn = long_in_the_past()
        self.is_usable = False

        if commit:
            self.save()

        # HEADS UP: this task name will be registered later
        # by the register_task_method() call.
        mailaccount_test_connection_task.apply_async(args=(self.pk, ),
                                                     countdown=3)

    def mark_unusable(self, message, args=(), exc=None, commit=True):
        """ Mark account unsable with date & message, log exception if any. """

        if exc is not None:
            if args:
                message = message % args

            message = u'{0} ({1})'.format(message, unicode(exc))
            LOGGER.exception(u'%s unusable: %s', self, message)

        self.date_last_conn = now()
        self.conn_error = message
        self.is_usable = False

        if commit:
            self.save()

    def mark_usable(self, commit=True):
        """ Mark the account usable and clear error. """

        LOGGER.info(u'%s is now usable.', self)

        if self.is_usable:
            start_task = False

        else:
            start_task = True

        self.date_last_conn = now()
        self.conn_error = u''
        self.is_usable = True

        if commit:
            self.save()

        if start_task:
            # HEADS UP: this task name will be registered later
            # by the register_task_method() call.
            mailaccount_update_mailboxes_task.delay(self.pk)

    def imap_connect(self):
        """ Return an IMAP mail connection, either SSL or not. """

        try:
            if self.use_ssl:
                return imaplib.IMAP4_SSL(self.hostname, self.get_port())

            else:
                return imaplib.IMAP4(self.hostname, self.get_port())

        except Exception as e:
            self.mark_unusable(u'Could not connect to IMAP server', exc=e)
            raise

    def imap_login(self, mail):
        """ Perform the IMAP authentication. """

        try:
            mail.login(self.username, self.password)

        except Exception as e:
            self.mark_unusable(u'Could not authenticate to IMAP server', exc=e)
            raise

    def imap_select(self, mail, mailbox_name):
        """ Select a mailbox on the remote server. """

        try:
            mail.select(mailbox_name)

        except Exception as e:
            self.mark_unusable(u'Could not select mailbox %s',
                               args=(mailbox_name, ), exc=e)
            raise

    def test_connection(self, force=False):
        """ test connection and report any error. """

        if self.recently_usable and not force:
            return

        LOGGER.info(u'Testing connection of %s', self)

        mail = self.imap_connect()

        self.imap_login(mail)

        self.imap_select(mail, u'INBOX')

        self.mark_usable()

    def imap_list_mailboxes(self, mail=None, as_text=False):
        """ List remote IMAP mailboxes.

        .. note:: This method always connect,
            regardless of :attr:`recently_usable`.
        """

        if mail is None:
            mail = self.imap_connect()

        self.imap_login(mail)

        try:
            result, data = mail.list()

        except Exception as e:
            self.mark_unusable(u'Could not list account mailboxes', exc=e)
            raise

        mailboxes = []

        if result == 'OK':
            for line in data:
                mailbox = line.split(' "." ')[1].replace('"', '')

                if mailbox not in self.MAILBOXES_BLACKLIST:
                    mailboxes.append(mailbox)

            if as_text:
                return self.MAILBOXES_STRING_SEPARATOR.join(mailboxes)

            self.mark_usable()

            return mailboxes


register_task_method(MailAccount, MailAccount.test_connection,
                     globals(), u'swarm')
register_task_method(MailAccount, MailAccount.update_mailboxes,
                     globals(), u'low')
