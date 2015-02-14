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
# import simplejson as json

# from django.conf import settings
from django.core import serializers
from django.core.management.base import BaseCommand
from django.db import connection

from sparks.django.fabfile import get_all_fixtures


LOGGER = logging.getLogger(__name__)


class Command(BaseCommand):

    """ Inspiration: http://stackoverflow.com/a/25469248/654755. """

    help = (
        u'Load the most recent stock processors pack if present.'
    )

    def handle(self, *args, **options):
        """ Deserialize the objects, Luke. """

        fixture_filename = None

        for fixture_name in get_all_fixtures(order_by='date'):
            if 'processors-pack' in fixture_name:
                fixture_filename = fixture_name
                break

        if fixture_filename is None:
            LOGGER.error(u'No processors-pack fixture found.\n'
                         u'  - Did you export it with `dump_processors` '
                         u'management command?\n'
                         u'  - Did you copy it on the local machine?')
            raise SystemExit(1)

        total_count = 0
        failed_count = 0

        # ————————————————————————————————————————————————————— Deserialization

        for obj in serializers.deserialize('json',
                                           open(fixture_filename).read(),
                                           use_natural_keys=True):
            try:
                obj.save()

            except:
                LOGGER.exception(u'Could not import %s', obj)
                failed_count += 1

            else:
                LOGGER.info(u'Succesfully imported %s.', obj)
                total_count += 1

                #
                # HEADS UP: how ugly this is, not to have a Django model
                #           method to do this cleanly. What is the purpose
                #           of forcing the admin to do this manually by
                #           copy-n-pasting this, instead of allowing the
                #           developer to run it on demand.
                #

        reset_sql = '''
SELECT setval(pg_get_serial_sequence('"core_processorcategory"','id'),
      coalesce(max("id"), 1), max("id") IS NOT null)
FROM "core_processorcategory";
SELECT setval(pg_get_serial_sequence('"core_processor_languages"','id'),
      coalesce(max("id"), 1), max("id") IS NOT null)
FROM "core_processor_languages";
SELECT setval(pg_get_serial_sequence('"core_processor_categories"','id'),
      coalesce(max("id"), 1), max("id") IS NOT null)
FROM "core_processor_categories";
SELECT setval(pg_get_serial_sequence('"core_processor"','id'),
      coalesce(max("id"), 1), max("id") IS NOT null)
FROM "core_processor";
SELECT setval(pg_get_serial_sequence('"core_processingchain_languages"','id'),
      coalesce(max("id"), 1), max("id") IS NOT null)
FROM "core_processingchain_languages";
SELECT setval(pg_get_serial_sequence('"core_processingchain_categories"','id'),
      coalesce(max("id"), 1), max("id") IS NOT null)
FROM "core_processingchain_categories";
SELECT setval(pg_get_serial_sequence('"core_processingchain_applies_on"','id'),
      coalesce(max("id"), 1), max("id") IS NOT null)
FROM "core_processingchain_applies_on";
SELECT setval(pg_get_serial_sequence('"core_processingchain"','id'),
      coalesce(max("id"), 1), max("id") IS NOT null)
FROM "core_processingchain";
SELECT setval(pg_get_serial_sequence('"core_processingerror"','id'),
      coalesce(max("id"), 1), max("id") IS NOT null)
FROM "core_processingerror";
        '''
        cursor = connection.cursor()
        cursor.execute(reset_sql)
        cursor.close()

        LOGGER.info(u'Sucessfully reset database sequences.')

        LOGGER.info(u'Imported %s items from %s (failed: %s).',
                    total_count, fixture_filename, failed_count)
