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
from django.core.urlresolvers import reverse  # , reverse_lazy
from django.shortcuts import get_object_or_404

from oneflow.core import forms, models

LOGGER = logging.getLogger(__name__)


class MailFeedRuleListCreateView(mixins.ListCreateViewMixin,
                                 generic.CreateView):

    """ Mix create and list views for mail feeds. """

    model = models.MailFeedRule
    default_sort_param = 'account'
    default_filter_param = 'all'
    form_class = forms.MailFeedRuleForm
    template_name = 'mailfeedrule/list-create.html'
    list_queryset_filter = {'mailfeed': ('mailfeed_pk', models.MailFeed, None)}

    def get_success_url(self):
        """ Return to our mail feed rules list. """

        return reverse('mailfeedrule_list_create',
                       args=(self.kwargs['mailfeed_pk'], ))

    def get_context_data(self, **kwargs):
        """ Add our mailfeed to the context. """

        kwargs['mailfeed'] = get_object_or_404(models.MailFeed,
                                               pk=self.kwargs['mailfeed_pk'])

        return super(MailFeedRuleListCreateView,
                     self).get_context_data(**kwargs)

    def form_valid(self, form):
        """ Give the MailFeedRule to its owner on the fly. """

        form.instance.mailfeed = get_object_or_404(
            models.MailFeed, pk=self.kwargs.get('mailfeed_pk'))

        return super(MailFeedRuleListCreateView, self).form_valid(form)


# No need, we've got inplace-edit for this purpose.
# class MailFeedRuleUpdateView(generic.UpdateView):
#     """ Hey pep257, this is a mail account update view. """
#     model = models.MailFeedRule
#     form_class = forms.MailFeedRuleForm
#     template_name = 'mailfeed/form.html'
#     success_url = reverse_lazy('mailfeed_index')


class MailFeedRuleDeleteView(generic.DeleteView):

    """ Delete a mail account. """

    model = models.MailFeedRule

    def get_success_url(self):
        """ Return to our mail feed rules list. """

        return reverse('mailfeedrule_list_create',
                       args=(self.kwargs['mailfeed_pk'], ))
