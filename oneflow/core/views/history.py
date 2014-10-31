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

from sparks.django.views import mixins

from django.views import generic
from django.core.urlresolvers import reverse_lazy

from oneflow.core import models

LOGGER = logging.getLogger(__name__)


class HistoryEntryListView(mixins.ListCreateViewMixin,
                           generic.CreateView):

    """ List views for user history entries. """

    model = models.HistoryEntry
    default_sort_param = '-date_created'
    default_filter_param = 'all'
    template_name = 'history/list.html'
    success_url = reverse_lazy('historyentry_list')


class HistoryEntryDeleteView(mixins.OwnerQuerySetMixin,
                             generic.DeleteView):

    """ Delete an history entry. """

    model = models.HistoryEntry
    # form_class = forms.MailFeedForm
    # template_name = 'mailfeed/list-create.html'
    success_url = reverse_lazy('historyentry_list')
    # ownerqueryset_filter = 'mailfeed__user'
