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

from django.views import generic
from django.core.urlresolvers import reverse_lazy

from oneflow.core import models  # forms,

LOGGER = logging.getLogger(__name__)


class StaffWebSiteListCreateView(mixins.ListCreateViewMixin,
                                 generic.CreateView):

    """ Mix create and list views for websites, for staff users.

    .. note:: as of 20150112, the create part is not implemented.
    """

    model = models.WebSite
    default_sort_param = 'name'
    default_filter_param = 'not:dupe'
    # form_class = forms.WebSiteForm
    template_name = 'staff/website/list-create.html'
    success_url = reverse_lazy('staff_website_list_create')
    list_queryset_filter_user = False

    def filter_queryset(self, qs, filter_param):
        """ Filter the QS as much as possible, given parameter. """

        if filter_param is None:
            return qs

        filters = filter_param.split()

        filters_fields = {
            'open': ('is_active', True),
            'closed': ('is_active', False),
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

            if params is not None:
                qs = qs.filter(**params)

        return qs

    def list_queryset_filter(self, qs):
        """ Exclude the local instance from the nodes list. """

        if not self.request.user.is_staff_or_superuser_and_enabled:
            return qs.none()

        return qs


class StaffWebSiteDeleteView(mixins.OwnerQuerySetMixin,
                             generic.DeleteView):

    """ Delete a website. """

    model = models.WebSite
    # form_class = forms.ProcessorForm
    # template_name = 'processor/list-create.html'
    success_url = reverse_lazy('staff_website_list_create')
    superuser_gets_full_queryset = True
