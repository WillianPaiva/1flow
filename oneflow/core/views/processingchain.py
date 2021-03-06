# -*- coding: utf-8 -*-
u"""
Copyright 2015 Olivier Cortès <oc@1flow.io>.

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

# from django.db.models import Q
from django.views import generic
from django.core.urlresolvers import reverse_lazy

from oneflow.core import models, forms


LOGGER = logging.getLogger(__name__)


class ProcessingChainListCreateView(mixins.ListCreateViewMixin,
                                    generic.CreateView):

    """ Mix create and list views for processing chains. """

    model = models.ProcessingChain
    default_sort_param = 'name'
    default_filter_param = 'not:dupe'
    form_class = forms.ProcessingChainForm
    template_name = 'processingchain/list-create.html'
    success_url = reverse_lazy('processingchain_list_create')

    # This is conditionnal in get_queryset()
    list_queryset_filter_user = False

    def get_queryset(self):
        """ If user is not staff, return only his/her processing chains. """

        if self.request.user.is_staff_or_superuser_and_enabled:
            return self.model.objects.all()

        return self.model.objects.filter(user=self.request.user)

    def filter_queryset(self, qs, filter_param):
        """ Filter the QS as much as possible, given parameter. """

        if filter_param is None:
            return qs

        filters = filter_param.split()

        filters_fields = {
            'active': ('is_active', True),
            'inactive': ('is_active', False),
        }

        for a_filter in filters:

            params = None
            a_filter = a_filter.lower()

            if a_filter.startswith(u'is:'):
                if a_filter.endswith(u':dupe') \
                        or a_filter.endswith(u':duplicate'):
                    qs = qs.exclude(duplicate_of_id=None)

                else:
                    filter_name = a_filter.split(':', 1)[1]
                    field_name, field_value = filters_fields[filter_name]
                    params = {field_name: field_value}

            elif a_filter.startswith(u'not:') \
                    or a_filter.startswith(u'isnot:'):

                if a_filter.endswith(u':dupe') \
                        or a_filter.endswith(u':duplicate'):
                    params = {'duplicate_of_id': None}

                else:
                    filter_name = a_filter.split(':', 1)[1]
                    field_name, field_value = filters_fields[filter_name]
                    params = {field_name: not field_value}

            else:
                params = {'name__icontains': a_filter}
                # params = [
                #     Q(name__icontains=a_filter)
                #     | Q(short_description_en__icontains=a_filter)
                # ]

            if params is not None:
                if isinstance(params, dict):
                    qs = qs.filter(**params)

                else:
                    qs = qs.filter(*params)

        return qs

    def form_valid(self, form):
        """ Give the ProcessingChain to its creator on the fly. """

        if form.instance.user is None:
            # Don't override the creator if we are
            # a staff user updating the object.
            form.instance.user = self.request.user

        return super(ProcessingChainListCreateView, self).form_valid(form)


class ProcessingChainDeleteView(mixins.OwnerQuerySetMixin,
                                generic.DeleteView):

    """ Delete a processing chain. """

    model = models.ProcessingChain
    # form_class = forms.ProcessingChainForm
    # template_name = 'processing chain/list-create.html'
    success_url = reverse_lazy('processingchain_list_create')
