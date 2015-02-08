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
from django.core.urlresolvers import reverse  # , reverse_lazy
from django.shortcuts import get_object_or_404

from oneflow.core import forms, models

LOGGER = logging.getLogger(__name__)


class ChainedItemCommonViewsMixin(object):

    """ Mixin common to all ChainedItem views. """

    model = models.ChainedItem

    def get_success_url(self):
        """ Return to our chained items list. """

        return reverse('chaineditem_list_create',
                       args=(self.kwargs['chain_id'], ))


class ChainedItemListCreateView(ChainedItemCommonViewsMixin,
                                mixins.ListCreateViewMixin,
                                generic.CreateView):

    """ Mix create and list views for chained items. """

    model = models.ChainedItem
    default_sort_param = ('position', )
    default_filter_param = 'all'
    list_queryset_filter_user = False
    form_class = forms.ChainedItemForm
    template_name = 'chaineditem/list-create.html'

    def list_queryset_filter(self, qs):
        """ Filter the chained item list of the current chain only. """

        user = self.request.user

        if not user.is_staff_or_superuser_and_enabled:
            qs = qs.filter(chain__user_id=user.id)

        return qs.filter(chain_id=self.kwargs.get('chain_id'))

    def get_context_data(self, **kwargs):
        """ Add our chain to the context. """

        kwargs['chain'] = get_object_or_404(models.ProcessingChain,
                                            id=self.kwargs['chain_id'])

        return super(ChainedItemListCreateView,
                     self).get_context_data(**kwargs)

    def form_valid(self, form):
        """ Link the ChainedItem to its mail feed on the fly. """

        if form.instance.chain_id is None:
            form.instance.chain = get_object_or_404(
                models.ProcessingChain, id=self.kwargs.get('chain_id'))

        return super(ChainedItemListCreateView, self).form_valid(form)


class ChainedItemPositionUpdateView(ChainedItemCommonViewsMixin,
                                    mixins.OwnerQuerySetMixin,
                                    generic.UpdateView):

    """ Simple view to update chained item position.

    .. todo:: if possible, refactor this for any kind
        of model which as a position attribute.
    """

    form_class = forms.ChainedItemPositionForm
    ownerqueryset_filter = 'chain__user'
    superuser_gets_full_queryset = True


class ChainedItemDeleteView(ChainedItemCommonViewsMixin,
                            mixins.OwnerQuerySetMixin,
                            generic.DeleteView):

    """ Delete a chained item. """

    ownerqueryset_filter = 'chain__user'
    superuser_gets_full_queryset = True
