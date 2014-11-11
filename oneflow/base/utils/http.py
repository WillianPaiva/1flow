# -*- coding: utf-8 -*-
u"""
Copyright 2012-2014 Olivier Cortès <oc@1flow.io>.

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

import re

from collections import namedtuple

UTM_RE    = re.compile(ur'[&]?utm_[^=]+(=[^&]*)?', re.I)
XTOR_RE   = re.compile(ur'[&#]?xtor(=[^&]*)?', re.I)
EQL_RE    = re.compile(ur'[#&?]=[^&]+', re.I)
LAST_RE   = re.compile(ur'[?&#=]*$', re.I)
TUMBLR_RE = re.compile(ur'#_=_$', re.I)
GGL_RE    = re.compile(ur'^[htps]+://[\w.]*google.com/(?:news/)?'
                       ur'url\?[\w=&]+url=([^&]+)[\w=&]*', re.I)

__all__ = ('clean_url', 'clean_google_url', 'clean_marketing_url', )


url_tuple = namedtuple('url', ['scheme', 'host_and_port', 'remaining', ])
url_port_tuple = namedtuple('url_port',
                            ['scheme', 'hostname', 'port', 'remaining', ])

FEEDSPORTAL_REPLACEMENTS = {
    u'A': u'0',
    u'B': u'.',
    u'C': u'/',
    u'D': u'?',
    u'E': u'-',
    u'I': u'_',
    u'L': u'http://',
    u'S': u'www.',
    u'N': u'.com',
    u'O': u'.co.uk',
}


class SplitUrlException(Exception):

    """ Raised when an URL is reaaaaally bad. """

    pass


def split_url(url, split_port=False):
    u""" Split an URL into a named tuple for easy manipulations.

    Eg. “http://test.com/toto becomes:
    ('scheme'='http', 'host_and_port'='test.com', 'remaining'='toto').

    if :param:`split_port` is ``True``, the returned namedtuple is of the form:

    ('scheme'='http', 'hostname'='test.com', 'port'=80, 'remaining'='toto').

    In this case, ``port`` will be an integer. All other attributes are strings.

    In case of an error, it will raise a :class:`SplitUrlException` exception.
    """

    try:
        proto, remaining = url.split('://', 1)

    except:
        raise SplitUrlException(u'Unparsable url “{0}”'.format(url))

    try:
        host_and_port, remaining = remaining.split('/', 1)

    except ValueError:
        host_and_port = remaining
        remaining     = u''

    if split_port:
        try:
            hostname, port = host_and_port.split(':')

        except ValueError:
            hostname = host_and_port
            port = '80' if proto == 'http' else '443'

        return url_port_tuple(proto, hostname, int(port), remaining)

    return url_tuple(proto, host_and_port, remaining)


def clean_google_url(url):
    """ Return the real article URL from a Google [Alert] URL.

    Because obviously, Google Alert URLs don't return correct 30x redirects.
    """

    match = GGL_RE.match(url)

    if match:
        return match.group(1)

    return url


def clean_marketing_url(url):
    """ Remove all ``utm_*`` ad-related stuff, and more. """

    return TUMBLR_RE.sub(
        u'', LAST_RE.sub(
            u'', EQL_RE.sub(
                u'', UTM_RE.sub(
                    u'', XTOR_RE.sub(
                        u'', url.replace('?source=ehesitrf0000001', '')
                    )
                )
            )
        )
    )


def clean_feedsportal_url(url):
    """ Get RID of those damn feedsportal shitty URLs. """

    try:
        url_start = url[:32]

    except:
        # the URL is definitely too short to contain a feedsportal thing.
        return url

    if '.feedsportal.com' in url_start:
        # Cf. http://www.pictuga.com/fiche-1125.html

        match = re.search('/([0-9a-zA-Z]{20,})/\w+\.htm$', url)

        if match:
            url = match.groups()[0].split('0')

            return u''.join([
                (FEEDSPORTAL_REPLACEMENTS[s[0]]
                 if s[0] in FEEDSPORTAL_REPLACEMENTS
                 else u'=') + s[1:] for s in url[1:]
            ])


def clean_url(url):
    """ Chain all URL cleaning functions. Expensive, but worth the result. """

    return clean_marketing_url(
        clean_google_url(
            clean_feedsportal_url(
                url
            )
        )
    )
