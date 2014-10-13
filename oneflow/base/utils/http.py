# -*- coding: utf-8 -*-
"""
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

UTM_RE  = re.compile(ur'[&]?utm_[^=]+(=[^&]*)?', re.I)
XTOR_RE = re.compile(ur'[&#]?xtor(=[^&]*)?', re.I)
EQL_RE  = re.compile(ur'[#&?]=[^&]+', re.I)
LAST_RE = re.compile(ur'[?&#=]*$', re.I)
GGL_RE  = re.compile(ur'^[htps]+://[\w.]*google.com/'
                     ur'url\?[\w=&]+url=([^&]+)[\w=&]+', re.I)

__all__ = ('clean_url', 'clean_google_url', 'clean_marketing_url', )


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

    return LAST_RE.sub(
        u'', EQL_RE.sub(
            u'', UTM_RE.sub(
                u'', XTOR_RE.sub(
                    u'', url
                )
            )
        )
    )


def clean_url(url):
    """ Chain all URL cleaning functions. Expensive, but worth the result. """

    return clean_marketing_url(
        clean_google_url(url)
    )
