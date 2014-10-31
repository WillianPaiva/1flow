# -*- coding: utf-8 -*-
u"""
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


class FeedIsHtmlPageException(Exception):

    """ Raised when the parsed feed gives us an HTML content.

    instead of an XML (RSS/Atom) one.
    """

    pass


class FeedFetchException(Exception):

    """ Raised when an RSS/Atom feed cannot be fetched, for any reason. """

    pass


class NotTextHtmlException(Exception):

    """ Raised when the content of an article is not text/html.

    To switch to other parsers, without re-requesting the actual content.
    """

    def __init__(self, message, response):
        """ OMG, pep257, please. """

        # Call the base class constructor with the parameters it needs
        Exception.__init__(self, message)
        self.response = response
