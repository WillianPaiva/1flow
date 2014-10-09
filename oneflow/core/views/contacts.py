# -*- coding: utf-8 -*-
"""
Copyright 2013-2014 Olivier Cortès <oc@1flow.io>.

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

import gdata.gauth

from django.http import HttpResponseRedirect

from django.conf import settings
from django.shortcuts import render
from django.contrib.auth import get_user_model

LOGGER = logging.getLogger(__name__)
User = get_user_model()


def import_contacts(request):
    """ Import Google Contacts.

    Reference, as of 20140102:
        http://stackoverflow.com/a/14161012/654755
    """

    auth_token = gdata.gauth.OAuth2Token(
        client_id=settings.GOOGLE_OAUTH2_CLIENT_ID,
        client_secret=settings.GOOGLE_OAUTH2_CLIENT_SECRET,
        scope=settings.GOOGLE_OAUTH2_CONTACTS_SCOPE,
        user_agent=settings.DEFAULT_USER_AGENT)

    authorize_url = auth_token.generate_authorize_url(
        redirect_uri='http://{0}{1}'.format(
            settings.SITE_DOMAIN,
            settings.GOOGLE_OAUTH2_CONTACTS_REDIRECT_URI
        )
    )

    return HttpResponseRedirect(authorize_url)


def import_contacts_authorized(request):
    """ Import Google contacts, when authorized by user via Google WWW.

    Reference, as of 20140102:
        https://developers.google.com/google-apps/contacts/v3/
    """

    import gdata.contacts.client

    user          = request.user.mongo
    dupes         = 0
    imported      = 0
    address_book  = set(a.rsplit(u' ', 1)[1] for a in user.address_book)

    current_mails = address_book.copy()
    current_mails |= [f.email for f in user.friends]

    auth_token = gdata.gauth.OAuth2Token(
        client_id=settings.GOOGLE_OAUTH2_CLIENT_ID,
        client_secret=settings.GOOGLE_OAUTH2_CLIENT_SECRET,
        scope=settings.GOOGLE_OAUTH2_CONTACTS_SCOPE,
        user_agent=settings.DEFAULT_USER_AGENT)

    auth_token.redirect_uri = 'http://{0}{1}'.format(
        settings.SITE_DOMAIN,
        settings.GOOGLE_OAUTH2_CONTACTS_REDIRECT_URI
    )

    # Heads UP: as of 20130104, "service" seems to be broken.
    # Google invites to use "client" instead.
    # Ref: https://code.google.com/p/gdata-python-client/issues/detail?id=549
    # client = gdata.contacts.service.ContactsService(source='1flow.io')
    client = gdata.contacts.client.ContactsClient(source='1flow.io')

    auth_token.get_access_token(request.GET['code'])
    auth_token.authorize(client)

    query = gdata.contacts.client.ContactsQuery()
    # query.updated_min = '2008-01-01'
    query.max_results = 1000

    feed = client.GetContacts(q=query)

    # The "all contacts" way, but it only return a limited subset of them.
    # feed = client.GetContacts()

    for entry in feed.entry:

        full_name = first_name = last_name = u''

        try:
            full_name = u'{0} {1}'.format(
                entry.name.given_name.text,
                entry.name.family_name.text
            )

        except AttributeError:
            try:
                full_name = entry.name.full_name.text

            except:
                pass

            else:
                try:
                    first_name, last_name = full_name.split(u' ', 1)

                except:
                    pass
        else:
            first_name = entry.name.given_name.text
            last_name  = entry.name.family_name.text

        for email in entry.email:

            if email.primary and email.primary == 'true':

                if email.address in current_mails:
                    if email.address in address_book:
                        user.ab_remove(email.address)

                        # NOTE: User is the Django User model here.
                        User.get_or_create_friend(
                            email=email.address,
                            first_name=first_name,
                            last_name=last_name
                        )

                    else:
                        dupes += 1

                else:
                    user.address_book.append(
                        u'{0} {1}'.format(full_name or email.address,
                                          email.address))
                    imported += 1

        # for group in entry.group_membership_info:
        #    print '    Member of group: %s' % (group.href)

    if imported:
        user.save()

    return render(request, 'import-contacts.html', {
        'imported': imported, 'dupes': dupes
    })
