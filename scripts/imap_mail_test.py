# -*- coding: utf-8 -*-
""" Oh GOSH. This is a test. Please, PEP257, stop bothering me. """
import os
import re
import imaplib
import email
import datetime


def get_first_text_block(email_message_instance):
    """ Get the first block of a mail.

    This will always return the text/plain part,
    even in the case of a multipart/form email.
    """

    maintype = email_message_instance.get_content_maintype()

    if maintype == 'multipart':
        for part in email_message_instance.get_payload():
            if part.get_content_maintype() == 'text':
                return part.get_payload()

    elif maintype == 'text':
        return email_message_instance.get_payload()


account = {
    'host': os.environ['PYTHON_IMAP_TEST_HOSTNAME'],
    'username': os.environ['PYTHON_IMAP_TEST_USERNAME'],
    'password': os.environ['PYTHON_IMAP_TEST_PASSWORD'],
}

mail = imaplib.IMAP4_SSL(account['host'])
mail.login(account['username'], account['password'])

# print mail.list()

mail.select("INBOX")

# result, data = mail.search(None, "ALL")
# ids = data[0] # data is a list.
# id_list = ids.split() # ids is a space separated string
# latest_email_id = id_list[-1] # get the latest
# # fetch the email body (RFC822) for the given ID
# result, data = mail.fetch(latest_email_id, "(RFC822)")
# raw_email = data[0][1] # here's the body, which is raw text of the whole email
# including headers and alternate payloads

# search and return uids
# result, data = mail.uid('search', None, "ALL")

# result, data = mail.uid('search', None, '(HEADER Subject "My Search Term")')
# result, data = mail.uid('search', None, '(HEADER Received "localhost")')

# Fetch by date.
# date = (feed.last_fetch.the_day()
#         - datetime.timedelta(1)).strftime("%d-%b-%Y")
date = (datetime.date.today() - datetime.timedelta(1)).strftime("%d-%b-%Y")
result, data = mail.uid('search', None, '(SENTSINCE {date})'.format(date=date))

if data == ['']:
    result, data = mail.uid('search', None, "ALL")

# print data

# MIX:
# result, data = mail.uid(
#   'search', None,
#   '(SENTSINCE {date} HEADER Subject '
#   '"My Subject" NOT FROM "yuji@grovemade.com")'.format(date=date))

# result, data = mail.uid('fetch', uid, '(X-GM-THRID X-GM-MSGID)')
# re.search('X-GM-THRID (?P<X-GM-THRID>\d+) '
#           'X-GM-MSGID (?P<X-GM-MSGID>\d+)', data[0]).groupdict()
# this becomes an organizational lifesaver once you have many results returned.

# Get a header key only
# result, data = mail.uid('fetch', uid, '(BODY[HEADER.FIELDS (DATE SUBJECT)]])')

# latest_email_uid = data[0].split()[-1]
# result, data = mail.uid('fetch', latest_email_uid, '(RFC822)')

# print result
# print data
#
result, data = mail.uid('fetch', data[0].replace(' ', ','), '(RFC822)')

# print data

for raw_data in data:

    if len(raw_data) == 1:
        continue

    raw_email = raw_data[1]

    email_message = email.message_from_string(raw_email)

    print '>> To:', email_message['To']

    email_cc = email_message.get('Cc', '')

    if email_cc:
        print '>> Cc:', email_cc

    email_list = email_message.get('List-Id', '')

    if email_list:
        print '>> List-Id:', email_list

    print '>> Subject: ', email_message['Subject'].replace('\r\n ', '')
    print '>> From:', email_message['From']
    # print '>> From:', email.utils.parseaddr(email_message['From'])

    # print all headers
    print '>> Headers: ', ', '.join(sorted(set(email_message.keys())))
    print '>> Body:\n', get_first_text_block(email_message)[:50], '…'
    print ">> —————————————————————————————————————————————————————————————— <<"
