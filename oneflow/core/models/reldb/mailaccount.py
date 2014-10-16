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
import operator

from datetime import datetime
from email import message_from_string
from email.header import decode_header

import imaplib
import logging

from collections import OrderedDict
from constance import config

from django.db import models
from django.utils.translation import ugettext_lazy as _
# from django.utils.text import slugify

from ....base.fields import TextRedisDescriptor
from ....base.utils import register_task_method, list_chunks

from sparks.django.models import ModelDiffMixin

from oneflow.base.utils.dateutils import (now, timedelta,
                                          email_date_to_datetime_tz)

from common import REDIS, long_in_the_past, DjangoUser
import mail_common as common

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
        'Drafts',
        'Trash',
        'Sent Messages',
        'Sent',
        'Spam',
        'Junk',
        'Deleted Messages',
        'Archive',
        'Archives',

        'INBOX.Drafts',
        'INBOX.Trash',
        'INBOX.Sent Messages',
        'INBOX.Sent',
        'INBOX.Spam',
        'INBOX.Junk',
        'INBOX.Deleted Messages',
        'INBOX.Archive',
        'INBOX.Archives',

        'INBOX.INBOX.Junk',
        'INBOX.INBOX.Drafts',
        'INBOX.INBOX.Sent',
        'INBOX.INBOX.Trash',
        'INBOX.INBOX.Sent Messages',
        'INBOX.INBOX.Spam',
        'INBOX.INBOX.Deleted Messages',
        'INBOX.INBOX.Archive',
        'INBOX.INBOX.Archives',

        _(u'Drafts'),
        _(u'Trash'),
        _(u'Sent Messages'),
        _(u'Sent'),
        _(u'Spam'),
        _(u'Junk'),
        _(u'Deleted Messages'),
        _(u'Archive'),
        _(u'Archives'),

        _(u'INBOX.Drafts'),
        _(u'INBOX.Trash'),
        _(u'INBOX.Sent Messages'),
        _(u'INBOX.Sent'),
        _(u'INBOX.Spam'),
        _(u'INBOX.Junk'),
        _(u'INBOX.Deleted Messages'),
        _(u'INBOX.Archive'),
        _(u'INBOX.Archives'),

        _(u'INBOX.INBOX.Junk'),
        _(u'INBOX.INBOX.Drafts'),
        _(u'INBOX.INBOX.Sent'),
        _(u'INBOX.INBOX.Trash'),
        _(u'INBOX.INBOX.Sent Messages'),
        _(u'INBOX.INBOX.Spam'),
        _(u'INBOX.INBOX.Deleted Messages'),
        _(u'INBOX.INBOX.Archive'),
        _(u'INBOX.INBOX.Archives'),
    )

    MAILBOXES_COMMON = OrderedDict((
        (u'INBOX', _(u'Inbox')),
    ))

    # NOTE: MAILBOXES_BLACKLIST is in MailAccount.

    user = models.ForeignKey(DjangoUser, verbose_name=_(u'Creator'))
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

    # —————————————————————————————————————————————————————————————— Properties

    @property
    def mailboxes(self):
        """ Return a list of mailboxes of the account.

        If it was refreshed too long in the past, rebuild the list.
        """
        _mailboxes_ = self._mailboxes_

        # LOGGER.debug(u'IMAP %s: mailboxes are %s in Redis.',
        #              self, _mailboxes_)

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

    @property
    def common_headers(self):
        try:
            return self._common_headers_

        except AttributeError:
            self._common_headers_ = reduce(operator.add,
                                           common.BASE_HEADERS.values())

            return self._common_headers_

    # —————————————————————————————————————————————————————————————————— Django

    def __unicode__(self):
        """ OMG, that's __unicode__, pep257. """

        return u'Mail account “{0}” of user {1}'.format(self.name, self.user)

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

    # —————————————————————————————————————————————————————————————————— Python

    def __enter__(self, *args, **kwargs):

        if not hasattr(self, '_imap_connection_'):
            self._imap_connection_ = self.imap_connect()

        self.imap_login()

    def __exit__(self, e_typ, e_val, trcbak):

        if hasattr(self, '_imap_connection_') \
                and self._imap_connection_ is not None:

            self.imap_logout()
            self._imap_connection_ = None

        # if all((e_typ, e_val, trcbak)):
        #    raise e_typ, e_val, trcbak

    # ——————————————————————————————————————————————————————————————— Internals

    def redis_key(self, thing):
        """ Create a unique key for the current account and a message UID. """

        if isinstance(thing, datetime):
            return u'ma:{0}:{1}:{2}'.format(self.pk,
                                            self._selected_mailbox_,
                                            unicode(thing))

        return u'ma:{0}:{1}'.format(self.pk, thing)

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

    def test_connection(self, force=False):
        """ Test connection and report any error.

        This function does everything manually and independantly,
        outside of the context processor, to be able to test
        everything eventually while anything else is already running.
        """

        if self.recently_usable and not force:
            return

        LOGGER.info(u'Testing connection of %s', self)

        conn = self.imap_connect()

        self.imap_login(conn)

        self.imap_select(conn, u'INBOX')

        self.imap_close(conn)

        self.imap_logout(conn)

        self.mark_usable()

    def update_mailboxes(self):
        """ Simply update the remote mailboxes names.

        .. note:: this method is registered as a task in Celery.
        """

        self._mailboxes_ = mailaccount_mailboxes_default(self)

        LOGGER.debug(u'IMAP %s: mailboxes list updated → %s',
                     self, u', '.join(self.mailboxes))

    # ——————————————————————————————————————————————————————————— IMAP wrappers

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

    def imap_login(self, imap_conn=None):
        """ Perform the IMAP authentication. """

        if imap_conn is None:
            imap_conn = self._imap_connection_

        if imap_conn is None:
            raise RuntimeError('Not connected!')

        try:
            imap_conn.login(self.username, self.password)

        except Exception as e:
            self.mark_unusable(u'Could not authenticate to IMAP server', exc=e)
            raise

        LOGGER.debug(u'IMAP %s: successful login with username %s',
                     self, self.username)

    def imap_select(self, imap_conn=None, mailbox_name=None):
        """ Select a mailbox on the remote server. """

        if imap_conn is None:
            imap_conn = self._imap_connection_

        if imap_conn is None:
            raise RuntimeError('Not connected!')

        if mailbox_name is None:
            mailbox_name = u'INBOX'

        try:
            # OMG o_O http://bugs.python.org/issue13940
            result, data = imap_conn.select('"' + mailbox_name + '"')

        except Exception as e:
            self.mark_unusable(u'Could not select mailbox %s',
                               args=(mailbox_name, ), exc=e)
            raise

        if result == 'OK':
            # LOGGER.debug(u'IMAP %s: selected mailbox %s with %s mail(s)',
            #             self, mailbox_name, data[0])

            self._selected_mailbox_ = mailbox_name

    def imap_close(self, imap_conn=None):

        if imap_conn is None:
            imap_conn = self._imap_connection_

        if imap_conn is None:
            raise RuntimeError('Not connected!')

        imap_conn.close()

        self._selected_mailbox_ = None

    def imap_logout(self, imap_conn=None):

        if imap_conn is None:
            imap_conn = self._imap_connection_

        if imap_conn is None:
            # raise RuntimeError('Not connected!')
            return

        try:
            imap_conn.close()

        except:
            # There was no mailbox open.
            pass

        imap_conn.logout()

        LOGGER.debug(u'IMAP %s: successful logout.', self)

    def imap_list_mailboxes(self, imap_conn=None, as_text=False):
        """ List remote IMAP mailboxes.

        .. note:: This method always connect,
            regardless of :attr:`recently_usable`.
        """

        if imap_conn is None:
            imap_conn = self._imap_connection_

        if imap_conn is None:
            raise RuntimeError('Not connected!')

        try:
            result, data = imap_conn.list()

        except Exception as e:
            self.mark_unusable(u'Could not list account mailboxes', exc=e)
            raise

        mailboxes = []

        if result == 'OK':
            for line in data:
                mailbox = line.split(' "." ')[1].replace('"', '')

                if mailbox not in self.MAILBOXES_BLACKLIST:

                    subfolder = False

                    for blacklisted in self.MAILBOXES_BLACKLIST:
                        if mailbox.startswith(blacklisted + u'.'):
                            subfolder = True
                            break

                    if not subfolder:
                        mailboxes.append(mailbox)

            self.mark_usable()

            if as_text:
                return self.MAILBOXES_STRING_SEPARATOR.join(sorted(mailboxes))

            return sorted(mailboxes)

    def imap_search_since(self, imap_conn=None, since=None):
        """ Search for messages in the currently selected mailbox.

        If :param:`since` is ``None``, all mails will be returned. Prepare
        yourself for an expensive operation.
        """

        if imap_conn is None:
            imap_conn = self._imap_connection_

        if imap_conn is None:
            raise RuntimeError('Not connected!')

        def search_since(since):

            if since is None:
                # We have no date, search for all mail.
                result, data = imap_conn.uid('search', None, "ALL")

            else:
                result, data = imap_conn.uid(
                    'search', None, '(SENTSINCE {date})'.format(
                        date=since.strftime("%d-%b-%Y")))

            if result == 'OK':
                if data == ['']:
                    # No new mail since ``since``…
                    LOGGER.debug(u'IMAP %s: no new mail since %s', self, since)
                    return

                else:
                    return data[0]

            else:
                LOGGER.error(u'IMAP %s: could not search '
                             u'emails since %s (%s)',
                             self, since, data)
                return

        cache_expiry_time = config.MAIL_IMAP_CACHE_EXPIRY

        if config.MAIL_IMAP_CACHE_MESSAGES:

            redis_key = self.redis_key(since)

            email_ids_as_string = REDIS.get(redis_key)

            if email_ids_as_string is None:

                email_ids_as_string = search_since(since)

                if email_ids_as_string is None:
                    return

                else:
                    REDIS.setex(redis_key,
                                cache_expiry_time,
                                email_ids_as_string)

        else:
            email_ids_as_string = search_since(since)

            if email_ids_as_string is None:
                return

        email_ids = list(list_chunks(email_ids_as_string.split(),
                                     config.MAIL_IMAP_FETCH_MAX))

        if not config.MAIL_IMAP_CACHE_MESSAGES:
            LOGGER.debug(u'IMAP %s: %s emails to fetch in %s.', self,
                         sum(len(x) for x in email_ids),
                         self._selected_mailbox_)

        for emails_ids_chunk in email_ids:

            if config.MAIL_IMAP_CACHE_MESSAGES:

                for msg_uid in emails_ids_chunk:
                    redis_key = self.redis_key(msg_uid)
                    message   = REDIS.get(redis_key)

                    if message is None:
                        result, data = imap_conn.uid('fetch',
                                                     msg_uid,
                                                     '(RFC822)')
                        if result == 'OK':
                            if len(data) == 1 and data[0] is None:
                                # Cached message ID corresponds
                                # to nothing on the server.
                                continue

                            for raw_data in data:

                                if len(raw_data) == 1:
                                    continue

                                message = raw_data[1]

                                REDIS.setex(redis_key,
                                            cache_expiry_time,
                                            message)
                                break

                        else:
                            LOGGER.error(u'IMAP %s: could not fetch '
                                         u'email with UID %s (%s)',
                                         self, msg_uid, data)

                    yield self.email_prettify_raw_message(message)

            else:
                # Without the cache, we fetch in
                # chunks to lower network overhead.

                result, data = imap_conn.uid('fetch',
                                             ','.join(emails_ids_chunk),
                                             '(RFC822)')

                if result == 'OK':
                    for raw_data in data:
                        if len(raw_data) == 1:
                            continue

                        yield self.email_prettify_raw_message(raw_data[1])

    # —————————————————————————————————————————————————————————————————— E-mail

    def email_prettify_raw_message(self, raw_message):
        """ Make a raw IMAP message usable from Python code.

        Eg. decode headers and prettify everything that can be.
        """

        email_message = message_from_string(raw_message)

        for header in self.common_headers:
            try:
                value = email_message[header]

            except KeyError:
                continue

            if value is None or not value:
                continue

            header_values = decode_header(value)

            if len(header_values) > 1:
                decoded_header = []

                for string, charset in header_values:
                    if charset:
                        decoded_header.append(string.decode(charset))

                    else:
                        decoded_header.append(string)

            else:
                string, charset = header_values[0]

                if charset:
                    decoded_header = string.decode(charset)

                else:
                    decoded_header = string

            email_message.replace_header(header, decoded_header)

            # Now, prettify the date.
            email_datetime = email_message.get('date', None)

            if not isinstance(email_datetime, datetime):
                msg_datetime = email_date_to_datetime_tz(email_datetime)
                email_message.replace_header('date', msg_datetime)

        return email_message

register_task_method(MailAccount, MailAccount.test_connection,
                     globals(), u'swarm')
register_task_method(MailAccount, MailAccount.update_mailboxes,
                     globals(), u'low')
