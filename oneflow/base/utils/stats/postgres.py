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

import logging

from django.db import connection


LOGGER = logging.getLogger(__name__)

PG_INDEXES_QUERY = """
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
"""

# http://www.appdesign.com/blog/2009/05/07/list-of-postres-tables-with-their-sizes-and-indexes/
# modified with c.relname → c.oid
#
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
PG_TABLE_SIZES_QUERY = """
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
"""

PG_DATABASE_SIZE_QUERY = """
SELECT
    datname, pg_database_size(datname)
FROM
    pg_database WHERE datname = %s;
"""

# ——————————————————————————————————————————————————————————————— Other queries

# ——————————————————————————————————————————— Shows pg_toast, not cool.
#
# SELECT nspname || '.' || relname AS "relation",
# pg_relation_size(C.oid) AS "size"
# FROM pg_class C
# LEFT JOIN pg_namespace N ON (N.oid = C.relnamespace)
# WHERE nspname NOT IN ('pg_catalog', 'information_schema')
# ORDER BY pg_relation_size(C.oid) DESC;
#
#
# ——————————————————————————————————————————————— NICE, but no indexes.
#
# SELECT nspname || '.' || relname AS "relation",
#     pg_size_pretty(pg_total_relation_size(C.oid)) AS "total_size"
#   FROM pg_class C
#   LEFT JOIN pg_namespace N ON (N.oid = C.relnamespace)
#   WHERE nspname NOT IN ('pg_catalog', 'information_schema')
#     AND C.relkind <> 'i'
#     AND nspname !~ '^pg_toast'
#   ORDER BY pg_total_relation_size(C.oid) DESC
#   LIMIT 50;

# ——————————————————————————————————————————————————————————————————— Functions


def pg_version_to_string(version):
    """ Cf. http://www.postgresql.org/docs/current/static/libpq-status.html#LIBPQ-PQSERVERVERSION . """  # NOQA

    version = str(version)

    minor = int(version[-2:])
    medium = int(version[-4:-2])
    major = int(version[:-4])

    return u'.'.join(unicode(x) for x in (major, medium, minor))


def postgresq_indexes():
    """ Return postgreSQL indexes sizes. """

    cursor = connection.cursor()

    cursor.execute(PG_INDEXES_QUERY)

    # table, column, type, notnull, index_name, is_index, primarykey,
    # uniquekey, default
    return cursor.fetchall()


def postgresql_activity():
    """ Return PostgreSQL activity table. """

    cursor = connection.cursor()

    # datid, datname, pid, usesysid, usename, application_name, client_addr,
    # client_hostname, client_port, backend_start, xact_start, query_start,
    # state_change, waiting, state, query
    cursor.execute('SELECT * FROM pg_stat_activity;')

    return cursor.fetchall()


def postgresql_database_size():
    """ Return PostgreSQL database size, in bytes. """

    cursor = connection.cursor()

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
    cursor.execute(PG_DATABASE_SIZE_QUERY, [cursor.db.settings_dict['NAME']])

    return cursor.fetchone()[-1]


def postgresql_relations_sizes():
    """ Return PostgreSQL relations sizes and details, in bytes. """

    cursor = connection.cursor()

    cursor.execute(PG_TABLE_SIZES_QUERY)

    return cursor.fetchall()


def postgresql_status():
    """ Return PG version, queries, indexes. """

    indexes = postgresq_indexes()

    activity = postgresql_activity()

    total_size = postgresql_database_size()

    tables_sizes = postgresql_relations_sizes()

    total_tuples = total_indices = total_data = total_total = 0

    for name, tuples, data, indices, total in tables_sizes:

        total_tuples += int(tuples)
        total_data += int(data)
        total_indices += int(indices)
        total_total += int(total)

    cursor = connection.cursor()

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
