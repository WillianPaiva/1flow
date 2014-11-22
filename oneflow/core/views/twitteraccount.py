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

from oneflow.core import forms, models

LOGGER = logging.getLogger(__name__)


class TwitterAccountListCreateView(mixins.ListCreateViewMixin,
                                   generic.CreateView):

    """ Mix create and list views for twitter accounts. """

    model = models.TwitterAccount
    default_sort_param = 'name'
    default_filter_param = 'all'
    form_class = forms.TwitterAccountForm
    template_name = 'twitteraccount/list-create.html'
    success_url = reverse_lazy('twitteraccount_list_create')

    def form_valid(self, form):
        """ Give the TwitterAccount to its owner on the fly. """

        form.instance.user = self.request.user
        return super(TwitterAccountListCreateView, self).form_valid(form)


class TwitterAccountDeleteView(mixins.OwnerQuerySetMixin,
                               generic.DeleteView):

    """ Delete a twitter account. """

    model = models.TwitterAccount
    # form_class = forms.TwitterAccountForm
    # template_name = 'twitteraccount/list-create.html'
    success_url = reverse_lazy('twitteraccount_list_create')
