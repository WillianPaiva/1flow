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

# import itertools
# import requests
# import simplejson as json

from collections import OrderedDict, namedtuple

from celery import Celery
from celery.events.state import State
from celery.task.control import inspect, revoke

from django.conf import settings
from django.db import connection

from sparks.fabric import is_localhost


LOGGER = logging.getLogger(__name__)


disk_ntuple = namedtuple('partition', 'device mountpoint fstype')
usage_ntuple = namedtuple('usage', 'total used free percent')


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


def disk_partitions(all=False):
    """Return all mountd partitions as a nameduple.

    If all == False return phyisical partitions only.
    """

    phydevs = []
    f = open("/proc/filesystems", "r")

    for line in f:
        if not line.startswith("nodev"):
            phydevs.append(line.strip())

    retlist = []
    f = open('/etc/mtab', "r")
    dev_done = []

    for line in f:
        if not all and line.startswith('none'):
            continue

        fields = line.split()
        device = fields[0]
        mountpoint = fields[1]
        fstype = fields[2]

        if (not all and fstype not in phydevs) or device in dev_done:
            continue

        if device == 'none':
            device = ''

        retlist.append(disk_ntuple(device, mountpoint, fstype))

        # Avoid doing devices twice. This happens in LXCs with bind mounts.
        # All we need is that / is mounted before other for it to show
        # instead of them. Hoppefully, it should always be the case ;-)
        dev_done.append(device)

    return retlist


def disk_usage(path):
    """Return disk usage associated with path."""
    st = os.statvfs(path)
    free = (st.f_bavail * st.f_frsize)
    total = (st.f_blocks * st.f_frsize)
    used = (st.f_blocks - st.f_bfree) * st.f_frsize
    try:
        percent = (float(used) / total) * 100

    except ZeroDivisionError:
        percent = 0

    # NB: the percentage is -5% than what shown by df due to
    # reserved blocks that we are currently not considering:
    # http://goo.gl/sWGbH
    return usage_ntuple(total, used, free, round(percent, 1))


def find_mount_point(path):
    """ Find the mount point of a given path. """

    path = os.path.abspath(path)
    while not os.path.ismount(path):
        path = os.path.dirname(path)
    return path


def memory():
    """ Return memory usage for local machine. """

    # svmem(total=8289701888L, available=1996591104L, percent=75.9,
    #       used=8050712576L, free=238989312L, active=6115635200,
    #       inactive=1401483264, buffers=40718336L, cached=1716883456)

    psutil_vm = psutil.virtual_memory()

    memory = {
        'raw': psutil_vm,
        'active_pct': psutil_vm.active * 100.0 / psutil_vm.total,
        'inactive_pct': psutil_vm.inactive * 100.0 / psutil_vm.total,
        'buffers_pct': psutil_vm.buffers * 100.0 / psutil_vm.total,
        'cached_pct': (psutil_vm.cached * 100.0 / psutil_vm.total),
    }

    memory['used_pct'] = (
        memory['active_pct']
        + memory['inactive_pct']
        + memory['buffers_pct']
        + memory['cached_pct']
    )

    if memory['used_pct'] > 100:
        # Sometimes, the total is > 100 (I've
        # seen 105.xxx many times while developing).
        memory['cached_pct'] = memory['cached_pct'] - (
            memory['used_pct'] - 100.0)

    return memory


# —————————————————————————————————————————————————————————————————————— Celery


def celery_tasks_names(inspect):
    """ Return a set() of Celery tasks names. """

    tasks_names = set()

    for k, v in inspect.registered_tasks().iteritems():
        for tn in v:
            if not (tn.startswith('celery') or tn.startswith('raven')):
                tasks_names.add(tn)

    return tasks_names


def celery_workers_status():

    print ',\n'.join('%s: %s scheduled task(s)' % (k, len(v)) for (k,v) in sorted(i.scheduled().iteritems()))


# from flower.app import Flower
# from flower.command import options, define
# from flower.models import TaskModel
# options.broker_api = settings.BROKER_URL
# app = Flower(options=options)
# app.start()


def celery_active_queues(inspect):
    """ Return a set of celery active queues. """

    active_queues = {}

    for wname, wattr in inspect.active_queues().iteritems():
        for queue_info in wattr:
            qname = queue_info['name']
            if qname in active_queues:
                active_queues[qname].append(wname)

            else:
                active_queues[qname] = [wname]

    return active_queues


def celery_status():
    """ Full set of celery status. """

    def ftot(x):
        return '\n'.join('    %s: %s' % (l, w) for (l, w)
                         in sorted(x.iteritems()))

    i = inspect()

    return {
        'tasks_names': sorted(celery_tasks_names(i)),
        'active_queues': celery_active_queues(i),
    }


# —————————————————————————————————————————————————————————————————— PostgreSQL


def pg_version_to_string(version):
    """ Cf. http://www.postgresql.org/docs/current/static/libpq-status.html#LIBPQ-PQSERVERVERSION . """  # NOQA

    version = str(version)

    minor = int(version[-2:])
    medium = int(version[-4:-2])
    major = int(version[:-4])

    return u'.'.join(unicode(x) for x in (major, medium, minor))


def postgresql_status():
    """ Return PG version, queries, indexes. """

    cursor = connection.cursor()

    cursor.execute("""
SELECT
    c.relname AS table,
    f.attname AS column,
    pg_catalog.format_type(f.atttypid,f.atttypmod) AS type,
    f.attnotnull AS notnull,
    i.relname as index_name,
CASE
    WHEN i.oid<>0 THEN 'Y'
    ELSE ''
END AS is_index,
CASE
    WHEN p.contype = 'p' THEN 'Y'
    ELSE ''
END AS primarykey,
CASE
    WHEN p.contype = 'u' THEN 'Y'
    WHEN p.contype = 'p' THEN 'Y'
    ELSE ''
END AS uniquekey,
CASE
    WHEN f.atthasdef = 'Y' THEN d.adsrc
END AS default  FROM pg_attribute f
JOIN pg_class c ON c.oid = f.attrelid
JOIN pg_type t ON t.oid = f.atttypid
LEFT JOIN pg_attrdef d ON d.adrelid = c.oid AND d.adnum = f.attnum
LEFT JOIN pg_namespace n ON n.oid = c.relnamespace
LEFT JOIN pg_constraint p ON p.conrelid = c.oid AND f.attnum = ANY (p.conkey)
LEFT JOIN pg_class AS g ON p.confrelid = g.oid
LEFT JOIN pg_index AS ix ON f.attnum = ANY(ix.indkey)
    and c.oid = f.attrelid and c.oid = ix.indrelid
LEFT JOIN pg_class AS i ON ix.indexrelid = i.oid

WHERE c.relkind = 'r'::char
AND n.nspname = 'public'   -- Replace with Schema name
--AND c.relname = 'nodes'  -- Replace with table name, or Comment this
                           -- for get all tables
AND f.attnum > 0
ORDER BY c.relname,f.attname;
""")

    # table, column, type, notnull, index_name, is_index, primarykey,
    # uniquekey, default
    indexes = cursor.fetchall()

    # datid, datname, pid, usesysid, usename, application_name, client_addr,
    # client_hostname, client_port, backend_start, xact_start, query_start,
    # state_change, waiting, state, query
    cursor.execute('SELECT * FROM pg_stat_activity;')
    activity = cursor.fetchall()

    # Cf. http://dba.stackexchange.com/a/14624/51426
    # SELECT spcname, pg_size_pretty(pg_tablespace_size(spcname))
    # FROM pg_tablespace;
    #
    # SELECT spcname, pg_tablespace_size(spcname)
    # FROM pg_tablespace;

    # SELECT datname, pg_size_pretty(pg_database_size(datname))
    # FROM pg_database;
    #
    #
    cursor.execute("""
SELECT
    datname, pg_database_size(datname)
FROM
    pg_database WHERE datname = %s;
    """, [cursor.db.settings_dict['NAME']])
    total_size = cursor.fetchone()[-1]

    # Shows pg_toast, not cool.
    # SELECT nspname || '.' || relname AS "relation",
    # pg_relation_size(C.oid) AS "size"
    # FROM pg_class C
    # LEFT JOIN pg_namespace N ON (N.oid = C.relnamespace)
    # WHERE nspname NOT IN ('pg_catalog', 'information_schema')
    # ORDER BY pg_relation_size(C.oid) DESC;

    # NICE, but no indexes.
    # SELECT nspname || '.' || relname AS "relation",
    #     pg_size_pretty(pg_total_relation_size(C.oid)) AS "total_size"
    #   FROM pg_class C
    #   LEFT JOIN pg_namespace N ON (N.oid = C.relnamespace)
    #   WHERE nspname NOT IN ('pg_catalog', 'information_schema')
    #     AND C.relkind <> 'i'
    #     AND nspname !~ '^pg_toast'
    #   ORDER BY pg_total_relation_size(C.oid) DESC
    #   LIMIT 50;

    # http://www.appdesign.com/blog/2009/05/07/list-of-postres-tables-with-their-sizes-and-indexes/
    # modified with c.relname → c.oid
    cursor.execute("""
SELECT
    c.relname AS Name,
    c.reltuples AS Tuples,
    pg_relation_size(c.oid) AS Data,
    pg_total_relation_size(c.oid)
        - pg_relation_size(c.oid) AS Indices,
    pg_total_relation_size(c.oid) AS Total
  FROM pg_class c
  LEFT JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE c.relkind IN ('r','')
   AND n.nspname NOT IN ('pg_catalog', 'pg_toast')
   AND pg_table_is_visible(c.oid)
 ORDER BY pg_total_relation_size(c.oid) DESC;
""")

    #             name              | tuples |  data   | indices  |  total
    # -------------------------------+--------+---------+----------+----------
    #  core_article                  |   5556 | 6070272 | 12271616 | 18341888
    #  core_originaldata             |   5357 | 7176192 |   811008 |  7987200
    #  core_simpletag                |    334 |  466944 |  4653056 |  5120000
    #  core_baseitem                 |   5556 | 1245184 |  3178496 |  4423680
    #  core_baseitem_tags            |   6574 |  319488 |   917504 |  1236992
    #  core_read                     |   3337 |  327680 |   860160 |  1187840
    #  core_website                  |    111 |  114688 |  1040384 |  1155072
    #  core_basefeed_items           |   5854 |  303104 |   811008 |  1114112
    #  core_read_tags                |   5127 |  253952 |   753664 |  1007616
    #
    tables_sizes = cursor.fetchall()

    total_tuples = total_indices = total_data = total_total = 0

    for name, tuples, data, indices, total in tables_sizes:

        total_tuples += int(tuples)
        total_data += int(data)
        total_indices += int(indices)
        total_total += int(total)

    db = cursor.db

    return {
        'database_alias': db.alias,
        'psycopg_version': u'.'.join(unicode(x) for x in db.psycopg2_version),
        'pg_version': pg_version_to_string(db.pg_version),
        'params': db.settings_dict,
        'indexes': indexes,
        'queries': activity,
        'total_size': total_size,
        'total_tuples': total_tuples,
        'total_data': total_data,
        'total_indices': total_indices,
        'total_total': total_total,
        'tables_sizes': tables_sizes,
    }

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
