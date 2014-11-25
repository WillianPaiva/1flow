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

from django.http import HttpResponseRedirect
from django.views import generic
from django.core.urlresolvers import reverse_lazy
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _

from oneflow.core import models
from oneflow.core.models.reldb.userimport import (
    IMPORT_STATUS,
    userimport_run_task,
)
LOGGER = logging.getLogger(__name__)


class HistoryEntryListView(mixins.ListCreateViewMixin,
                           generic.CreateView):

    """ List views for user history entries. """

    model = models.HistoryEntry
    default_sort_param = '-date_created'
    default_filter_param = 'all'
    template_name = 'history/list.html'
    success_url = reverse_lazy('historyentry_list')


class HistoryEntryActionView(mixins.OwnerQuerySetMixin,
                             generic.DetailView):

    """ Retry an history entry. """

    model = models.HistoryEntry
    # form_class = forms.MailFeedForm
    # template_name = 'mailfeed/list-create.html'
    success_url = reverse_lazy('historyentry_list')
    # ownerqueryset_filter = 'mailfeed__user'

    def get_queryset(self):
        """ Filter only the user history entries. """

        return self.model.objects.filter(user=self.request.user)

    def get(self, request, *args, **kwargs):
        """ override the get method to run any action. """

        history_entry = self.get_object()

        return getattr(self, 'action_{0}'.format(
                       kwargs.get('action')))(history_entry)

    def action_retry(self, history_entry):
        """ Retry an import if it failed. """

        if not (
            history_entry.status == IMPORT_STATUS.FAILED
            or history_entry.running_old
        ):
            messages.error(self.request, _(u'Import #{0} is not in failed '
                           u'state; thus not restarted.').format(
                           history_entry.id), extra_tags='sticky safe')
        else:
            try:
                userimport_run_task.delay(history_entry.id)

            except Exception, e:
                messages.warning(self.request, _(u'Could not retry import: '
                                 u'<code>{0}</code>.').format(
                                 e), extra_tags='sticky safe')
            else:
                messages.success(self.request, _(u'Import #{0} successfully '
                                 u'relaunched.').format(history_entry.id))

        return HttpResponseRedirect(self.success_url)


class HistoryEntryDeleteView(mixins.OwnerQuerySetMixin,
                             generic.DeleteView):

    """ Delete an history entry. """

    model = models.HistoryEntry
    # form_class = forms.MailFeedForm
    # template_name = 'mailfeed/list-create.html'
    success_url = reverse_lazy('historyentry_list')
    # ownerqueryset_filter = 'mailfeed__user'
