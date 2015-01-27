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

import os
import logging
# import simplejson as json

# from django.conf import settings
from collections import OrderedDict
from django.core import serializers
from django.core.management.base import BaseCommand
from django.core.management.commands.dumpdata import sort_dependencies
from django.db.models import Q

from sparks.django.fabfile import new_fixture_filename

from oneflow.core.models import (
    Processor,
    ProcessorCategory,
    ProcessingChain,
    ChainedItem,
)

LOGGER = logging.getLogger(__name__)


class Command(BaseCommand):

    """ Inspiration: http://stackoverflow.com/a/25469248/654755. """

    help = (
        u'Selectively dump all stock processors-related items. Use '
        u'the environment variables SELECTIVE_DUMP_1FLOW_USERS and '
        u'SELECTIVE_DUMP_1FLOW_CATEGORIES to limit the query to a '
        u'subset of items created by one or more specific users.'
    )

    def handle(self, *args, **options):
        """ Dump the objects, Luke. """

        limiting_usernames = os.environ.get('SELECTIVE_DUMP_1FLOW_USERS',
                                            u'admin').split(',')

        limiting_categories = os.environ.get('SELECTIVE_DUMP_1FLOW_CATEGORIES',
                                             u'1flow-stock').split(',')

        fixture_filename = new_fixture_filename(
            u'core', custom_suffix=u'processors-pack__{0}__{1}'.format(
                u','.join(limiting_usernames),
                u','.join(limiting_categories),
            )
        )

        limiting_query1 = (
            Q(slug__in=limiting_categories)
            | Q(user__username__in=limiting_usernames)
        )

        limiting_query2 = (
            Q(categories__slug__in=limiting_categories)
            | Q(user__username__in=limiting_usernames)
        )

        # Use OrderedDict because sort_dependencies() doesn't
        # work as expected. See original SO answer for details.
        app_list = OrderedDict()

        total_count = 0

        app_list['core.ProcessorCategory'] = \
            ProcessorCategory.objects.filter(limiting_query1)

        total_count += app_list['core.ProcessorCategory'].count()

        app_list['core.Processor'] = \
            Processor.objects.filter(limiting_query2)

        total_count += app_list['core.Processor'].count()

        app_list['core.ProcessChain'] = \
            ProcessingChain.objects.filter(limiting_query2)

        total_count += app_list['core.ProcessChain'].count()

        app_list['core.ChainedItem'] = \
            ChainedItem.objects.filter(
                chain__in=app_list['core.ProcessChain']).order_by(
                    'chain', 'position')

        total_count += app_list['core.ChainedItem'].count()

        # ——————————————————————————————————————————————————————— Serialization

        data = serializers.serialize('json',
                                     sort_dependencies(app_list.items()),
                                     indent=2, use_natural_keys=True)

        with open(fixture_filename, 'w') as f:
            f.write(data)

        self.stdout.write(u'Exported %s items in %s.'
                          % (total_count, fixture_filename))
