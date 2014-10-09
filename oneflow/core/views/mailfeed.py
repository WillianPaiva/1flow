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

from sparks.django.views import mixins

from django.views import generic
from django.core.urlresolvers import reverse_lazy

from oneflow.core import forms, models

LOGGER = logging.getLogger(__name__)


class MailFeedListCreateView(mixins.ListCreateViewMixin,
                             generic.CreateView):

    """ Mix create and list views for mail feeds. """

    model = models.MailFeed
    default_sort_param = 'name'
    default_filter_param = 'all'
    form_class = forms.MailFeedForm
    template_name = 'mailfeed/list-create.html'
    success_url = reverse_lazy('mailfeed_list_create')

    def form_valid(self, form):
        """ Give the MailFeed to its owner on the fly. """

        form.instance.user = self.request.user
        return super(MailFeedListCreateView, self).form_valid(form)


# No need, we've got inplace-edit for this purpose.
# class MailFeedUpdateView(generic.UpdateView):
#     """ Hey pep257, this is a mail account update view. """
#     model = models.MailFeed
#     form_class = forms.MailFeedForm
#     template_name = 'mailfeed/form.html'
#     success_url = reverse_lazy('mailfeed_index')


class MailFeedDeleteView(generic.DeleteView):

    """ Delete a mail account. """

    model = models.MailFeed
    # form_class = forms.MailFeedForm
    # template_name = 'mailfeed/list-create.html'
    success_url = reverse_lazy('mailfeed_list_create')
