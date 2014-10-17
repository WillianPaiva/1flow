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

from collections import OrderedDict

from django.utils.translation import ugettext_lazy as _

# No fear. See http://bit.ly/smtp-headers
OTHER_VALID_HEADERS = (
    'DL-Expansion-History',
    'Path',
    'Received',
    'Return-Path',
    'NNTP-Posting-Host',
    'Also-Control',
    'Alternate-Recipient',
    'Content-Disposition',
    'Message-Context',
    'Control',
    'Disclose-Recipients',
    'MIME-Version',
    'Apparently-To',
    'Approved',
    'Approved-By',
    'bcc',
    'cc',
    'Distribution',
    'Fax',
    'Telefax',
    'For-Approval',
    'For-Comment',
    'For-Handling',
    'Newsgroups',
    'Originator',
    'Originator-Info',
    'Phone',
    'Sender',
    'To',
    'X-Envelope-From',
    'X-Envelope-To',
    'Envelope-To',
    'X-Face',
    'X-RCPT-TO',
    'X-Sender',
    'X-X-Sender',
    'Posted-To',
    'X-Admin',
    'Content-Return',
    'Disposition-Notification-Options',
    'Disposition-Notification-To',
    'Errors-To',
    'Return-Receipt-To',
    'Read-Receipt-To',
    'X-Confirm-reading-to',
    'Return-Receipt-Requested',
    'Registered-Mail-Reply-Requested-By',
    'Followup-To',
    'Generate-Delivery-Report',
    'Original-Recipient',
    'Prevent-NonDelivery-Report',
    'Reply-To',
    'Mail-Followup-To',
    'Mail-Reply-To',
    'Abuse-Reports-To',
    'X-Complaints-To',
    'X-Report-Abuse-To',
    'Mail-Copies-To',
    'X400-Content-Return',
    'Article-Names',
    'Article-Updates',
    'Content-Alias',
    'Content-Base',
    'Content-ID',
    'Content-Location',
    'Delivered-To',
    'X-Loop',
    'In-Reply-To',
    'Message-ID',
    'Obsoletes',
    'References',
    'Replaces',
    'See-Also',
    'Supersedes',
    'Translated-By',
    'Translation-Of',
    'X-UIDL',
    'X-URI',
    'X-URL',
    'X-IMAP',
    'Comments',
    'Content-Description',
    'Content-Identifier',
    'Keywords',
    'Organisation',
    'Organization',
    'Subject',
    'Summary',
    'Date',
    'Delivery-Date',
    'Expires',
    'Expiry-Date',
    'Reply-By',
    'X-OriginalArrivalTime',
    'Importance',
    'Incomplete-Copy',
    'PICS-Label',
    'Precedence',
    'Priority',
    'Sensitivity',
    'X-MSMail-Priority',
    'X-Priority',
    'Content-Language',
    'Language',
    'Content-Length',
    'Lines',
    'Content-Alternative',
    'Content-Conversion',
    'Conversion',
    'Conversion-With-Loss',
    'Content-Class',
    'Content-Features',
    'Content-SGML-Entity',
    'Content-Transfer-Encoding',
    'Content-Type',
    'Encoding',
    'Message-Type',
    'X-MIME-Autoconverted',
    'Resent-Reply-To:,',
    'Resent-From',
    'Resent-Sender',
    'Resent-Date',
    'Resent-To',
    'Resent-Cc',
    'Resent-Bcc',
    'Resent-Message-ID',
    'Content-MD5',
    'Xref',
    'Cancel-Lock',
    'Cancel-Key',
    'List-Archive',
    'List-Digest',
    'List-Help',
    'List-ID',
    'Mailing-List',
    'X-Mailing-List',
    'List-Owner',
    'List-Post',
    'List-Software',
    'List-Subscribe',
    'List-Unsubscribe',
    'List-URL',
    'X-Listserver',
    'X-List-Host',
    'Autoforwarded',
    'Discarded-X400-IPMS-Extensions',
    'Discarded-X400-MTS-Extensions',
    'Fcc',
    'Speech-Act',
    'Status',
    'X-No-Archive',
)

OTHER_VALID_HEADERS_lower = (x.lower() for x in OTHER_VALID_HEADERS)

BASE_HEADERS = {
    u'subject': ('Subject', ),
    u'from': ('From', 'Sender', 'X-Envelope-From',
              'X-Sender', 'X-X-Sender',
              'Reply-To', 'Mail-Reply-To',
              'Mail-Followup-To', 'Resent-From', ),
    u'to': ('To', 'Cc', 'Bcc', 'Delivered-To', 'X-Loop',
            'Resent-To', 'Resent-Cc', 'Resent-Bcc', ),
    u'list': ('Mailing-list', 'List-ID',
              'X-Mailing-List', 'List-URL', ),
}

BASE_HEADERS[u'common'] = (
    BASE_HEADERS[u'subject']
    + BASE_HEADERS[u'to']
    + BASE_HEADERS[u'from']
)

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


def email_get_first_text_block(email_message):
    """ Get the first block of a mail.

    This will always return the text/plain part,
    even in the case of a multipart/form email.
    """

    maintype = email_message.get_content_maintype()

    if maintype == 'multipart':
        for part in email_message.get_payload():
            if part.get_content_maintype() == 'text':
                return part.get_payload()

    elif maintype == 'text':
        return email_message.get_payload()
