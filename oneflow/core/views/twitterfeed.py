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


class TwitterFeedListCreateView(mixins.ListCreateViewMixin,
                                generic.CreateView):

    """ Mix create and list views for twitter feeds. """

    model = models.TwitterFeed
    default_sort_param = 'name'
    default_filter_param = 'all'
    form_class = forms.TwitterFeedForm
    template_name = 'twitterfeed/list-create.html'
    success_url = reverse_lazy('twitterfeed_list_create')

    def list_queryset_filter(self, qs):
        """ Exclude the local instance from the nodes list. """

        return qs.filter(user=self.request.user)

    def form_valid(self, form):
        """ Give the TwitterFeed to its owner on the fly. """

        form.instance.user = self.request.user
        return super(TwitterFeedListCreateView, self).form_valid(form)


class TwitterFeedDeleteView(mixins.OwnerQuerySetMixin,
                            generic.DeleteView):

    """ Delete a twitter feed. """

    model = models.TwitterFeed
    # form_class = forms.TwitterFeedForm
    # template_name = 'twitterfeed/list-create.html'
    success_url = reverse_lazy('twitterfeed_list_create')

    def list_queryset_filter(self, qs):
        """ Exclude the local instance from the nodes list. """

        return qs.user_made().filter(user=self.request.user)
