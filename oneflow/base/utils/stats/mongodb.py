# -*- coding: utf-8 -*-
u"""
Copyright 2012-2014 Olivier Cortès <oc@1flow.io>.

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
import psutil
import pymongo
import logging
import platform

from collections import OrderedDict

from django.conf import settings

from sparks.fabric import is_localhost

from storage import find_mount_point

LOGGER = logging.getLogger(__name__)


def host_infos(mongo_connection=None):
    """ Return basic host informations (hostname, cpu, count, distro). """

    if mongo_connection:
        host_infos = mongo_connection.command('hostInfo')

    else:

        host_infos = {
            'system': {
                'hostname': platform.node(),
                'cpuArch': platform.machine(),
                'numCores': psutil.cpu_count(),
            },
            'os': {
                'name': platform.system(),
                'version': platform.release(),
            }
        }

    if host_infos['os']['name'].startswith('NAME="'):
        host_infos['os']['name'] = host_infos['os']['name'][6:-1]

    return host_infos


# ————————————————————————————————————————————————————————————————————— MongoDB

main_client = pymongo.MongoClient(settings.MONGODB_HOST,
                                  settings.MONGODB_PORT)

mongodb = getattr(main_client, settings.MONGODB_NAME)
admin_maindb = main_client.admin

if settings.MONGODB_HOST != settings.MONGODB_HOST_ARCHIVE:
    archive_client = pymongo.MongoClient(settings.MONGODB_HOST_ARCHIVE,
                                         settings.MONGODB_PORT_ARCHIVE)
    admin_archivedb = archive_client.admin
else:
    archive_client = main_client
    admin_archivedb = None

archivedb = getattr(archive_client, settings.MONGODB_NAME_ARCHIVE)


def mongodbstats():

    return mongodb.command('dbstats')


def mongodbcollstats():

    return OrderedDict(
        (collname, mongodb.command('collStats', collname))
        for collname in sorted(mongodb.collection_names())
    )


def archivedbstats():

    return archivedb.command('dbstats')


def archivedbcollstats():

    return OrderedDict(
        (collname, archivedb.command('collStats', collname))
        for collname in sorted(archivedb.collection_names())
    )


def host_infos_mongodb_main():

    if is_localhost(settings.MONGODB_HOST):
        return None

    else:
        return host_infos(admin_maindb)


def server_status_main():

    return admin_maindb.command('serverStatus')


def cmd_line_ops_main():

    return admin_maindb.command('getCmdLineOpts')


def host_infos_mongodb_archive():

    if admin_archivedb is None:
        return None

    return admin_archivedb.command('hostInfo')


def server_status_archive():

    if admin_archivedb is None:
        return None

    return admin_archivedb.command('serverStatus')


def cmd_line_ops_archive():

    if admin_archivedb is None:
        return None

    return admin_archivedb.command('serverStatus')


def mongo_statvfs():

    # TODO: rework for multiple hosts —————————————————————————————————————————

    clom = cmd_line_ops_main()

    try:
        # MongoDB 2.6
        mongo_mount_point = find_mount_point(
            clom['parsed']['storage']['dbPath']
        )

    except KeyError:
        # MongoDB 2.4
        mongo_mount_point = find_mount_point(
            clom['parsed']['dbpath']
        )

    tmp_statvfs = os.statvfs(mongo_mount_point)

    return {
        # Size of filesystem in bytes
        'f_blocks': tmp_statvfs.f_frsize * tmp_statvfs.f_blocks,

        # Actual number of free bytes
        'f_bfree': tmp_statvfs.f_frsize * tmp_statvfs.f_bfree,

        # Number of free bytes that ordinary users
        'f_bavail': tmp_statvfs.f_frsize * tmp_statvfs.f_bavail,
    }
