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

from django.db import models
# from django.utils.translation import ugettext as _
# from django.utils.text import slugify

from sparks.django.models import ModelDiffMixin

from oneflow.base.utils.dateutils import now

from common import long_in_the_past, DjangoUser  # , REDIS

LOGGER = logging.getLogger(__name__)


class MailAccount(ModelDiffMixin):

    """ 1flow users can configure many mail accounts.

    1flow create feeds from them.
    """

    user = models.ForeignKey(DjangoUser)
    name = models.CharField(max_length=128, blank=True)

    # cf. http://en.wikipedia.org/wiki/Hostname
    hostname = models.CharField(max_length=255)

    use_ssl = models.BooleanField(default=True, blank=True)
    port = models.IntegerField(null=True, blank=True)
    username = models.CharField(max_length=255, blank=True)
    password = models.CharField(max_length=255, default=u'', blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_last_conn = models.DateTimeField(default=long_in_the_past)
    conn_error = models.CharField(max_length=255, default=u'', blank=True)
    is_usable = models.BooleanField(default=True, blank=True)

    class Meta:
        app_label       = 'core'
        unique_together = ('user', 'hostname', 'username', )

    def save(self, *args, **kwargs):
        """ Automatically add a name/username if none is given. """

        if self.username is None or self.username.strip() == u'':
            self.username = self.user.username

        if self.name is None or self.name.strip() == u'':
            self.name = u'{0}@{1}'.format(self.username, self.hostname)

        if self.password is None:
            self.password = u''

        changed_fields = self.changed_fields

        if 'hostname' in changed_fields \
            or 'username' in changed_fields \
            or 'password' in changed_fields \
            or 'use_ssl' in changed_fields \
                or 'port' in changed_fields:
            self.reset_unusable(commit=False)

        return super(MailAccount, self).save(*args, **kwargs)

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

        self.date_last_conn = now()
        self.conn_error = u''
        self.is_usable = True

        if commit:
            self.save()

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

        if self.is_usable and now() - self.date_last_conn < 3600 \
                and not force:
            return

        mail = self.imap_connect()

        self.imap_login(mail)

        self.imap_select(mail, u'INBOX')

        self.mark_usable()
