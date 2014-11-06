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

import logging

from django.conf import settings
from django.db.models import Q

from ...base.utils import word_match_consecutive_once

LOGGER = logging.getLogger(__name__)

from django_select2.views import Select2View


class FeedsCompleterView(Select2View):

    """ Complete feeds from name / URLs. """

    def get_results(self, request, term, page, context):
        """ Return feed completions. """

        matching_Q = (
            Q(BaseFeed___name__icontains=term)
            | Q(RssAtomFeed___url__icontains=term)
            | Q(RssAtomFeed___website__name__icontains=term)
            | Q(RssAtomFeed___website__url__icontains=term)
        )

        for lang_code, lang_name in settings.LANGUAGES:
            matching_Q |= (
                Q(**{'BaseFeed___short_description_{0}__icontains'.format(
                    lang_code): term})
                # | Q(**{'BaseFeed___description_{0}__icontains'.format(
                # lang_code): term})
                | Q(**{'RssAtomFeed___website__short_description_{0}__icontains'.format(
                    lang_code): term})
                # | Q(**{'RssAtomFeed___website__description_{0}__icontains'.format(
                # lang_code): term})
            )

        matching_feeds = request.user.unsubscribed_feeds.filter(matching_Q)

        return (
            'nil',
            False,
            #
            # NOTE: this query is replicated in the form,
            #       to get the count() in the placeholder.
            #
            # we use unicode(id) to avoid
            # “ObjectId('51c8a0858af8069f5bafbb5a') is not JSON serializable”
            [(unicode(f.id), f.name) for f in matching_feeds]
        )


class UserAddressBookView(Select2View):

    """ Complete email addresses from current user address book. """

    def get_results(self, request, term, page, context):
        """ Return address book completions. """

        term = term.lower()

        return (
            'nil',
            False,
            [r for r in request.user.mongo.relations
             if word_match_consecutive_once(term, r[1].lower())]
        )
