# -*- coding: utf-8 -*-
u"""
Copyright 2013 Olivier Cortès <oc@1flow.io>.

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

# Don't get any fallback, we *need* to have this configured in `.env`.
REDIS_CACHE_DB = os.environ.get('REDIS_CACHE_DB')

CACHE_HOST, CACHE_PORT, CACHE_DB_NUM = REDIS_CACHE_DB.split(':', 3)

CACHES = {
    'default': {

        # This uses redis_cache internally.
        # see https://pypi.python.org/pypi/python-redis-lock
        'BACKEND': 'redis_lock.django_cache.RedisCache',

        'LOCATION': REDIS_CACHE_DB,

        # This is the default timeout, reasonably sane to
        # keep the DB uncluterred. Some particular keys have
        # infinite or less-than-default timeouts.
        # Please keep https://github.com/niwibe/django-redis/issues/56 in mind.
        'TIMEOUT:': int(os.environ.get('REDIS_CACHE_TIMEOUT', 3600 * 24 * 7)),

        'OPTIONS': {

            # 'CLIENT_CLASS': 'redis_cache.client.HerdClient',
            # CACHE_HERD_TIMEOUT
            'CLIENT_CLASS': 'redis_cache.client.DefaultClient',
            'PARSER_CLASS': 'redis.connection.HiredisParser',
        }
    },
    'sessions': {
        'BACKEND': 'django_redis.cache.RedisCache',
        # Don't set any fallback, we *need* to have this configured in `.env`.
        'LOCATION': os.environ.get('REDIS_SESSIONS_DB'),

        # Please keep https://github.com/niwibe/django-redis/issues/56 in mind.
        'TIMEOUT:': int(os.environ.get('REDIS_SESSIONS_TIMEOUT',
                                       3600 * 24 * 7)),

        'OPTIONS': {
            'CLIENT_CLASS': 'redis_cache.client.DefaultClient',
            'PARSER_CLASS': 'redis.connection.HiredisParser',
        }
    }
}

CACHEOPS_REDIS = {
    'host': CACHE_HOST,
    'port': int(CACHE_PORT),
    'db': int(CACHE_DB_NUM),
    'socket_timeout': 3,
}

CACHEOPS_USE_LOCK = True

CACHE_ONE_HOUR = 60 * 60
CACHE_ONE_DAY = CACHE_ONE_HOUR * 24
CACHE_ONE_WEEK = CACHE_ONE_DAY * 7
CACHE_ONE_MONTH = CACHE_ONE_DAY * 31

CACHEOPS = {
    # Automatically cache any User.objects.get() calls
    # for 30 minutes. This includes request.user or
    # post.author access, where Post.author is a foreign
    # key to auth.User.
    'auth.user': {'ops': 'get', 'timeout': CACHE_ONE_WEEK},
    'core.usercounters': {'ops': 'all', 'timeout': CACHE_ONE_WEEK},

    # Automatically cache all gets and queryset fetches
    # to other django.contrib.auth and oneflow.base models
    # for an hour.
    'auth.*': {'ops': ('fetch', 'get'), 'timeout': CACHE_ONE_DAY},
    'base.*': {'ops': ('fetch', 'get'), 'timeout': CACHE_ONE_DAY},

    # Cache gets, fetches, counts and exists to Permission
    # 'all' is just an alias for ('get', 'fetch', 'count', 'exists')
    'auth.permission': {'ops': 'all', 'timeout': CACHE_ONE_DAY},

    'contenttypes.contenttype': {'ops': 'all', 'timeout': CACHE_ONE_WEEK},

    'core.processor': {'ops': 'all', 'timeout': CACHE_ONE_DAY},
    'core.processingchain': {'ops': 'all', 'timeout': CACHE_ONE_DAY},
    'core.chaineditem': {'ops': 'all', 'timeout': CACHE_ONE_DAY},
    'core.processorcategory': {'ops': 'all', 'timeout': CACHE_ONE_WEEK},

    'core.language': {'ops': 'all', 'timeout': CACHE_ONE_WEEK},
    'core.simpletag': {'ops': 'all', 'timeout': CACHE_ONE_WEEK},
    'core.website': {'ops': 'all', 'timeout': CACHE_ONE_WEEK},
    'core.author': {'ops': 'all', 'timeout': CACHE_ONE_WEEK},

    'core.folder': {'ops': 'all', 'timeout': CACHE_ONE_DAY},

    'core.basefeed': {'ops': 'all', 'timeout': CACHE_ONE_HOUR},
    'core.rssatomfeed': {'ops': 'all', 'timeout': CACHE_ONE_HOUR},
    'core.twitterfeed': {'ops': 'all', 'timeout': CACHE_ONE_HOUR},
    'core.emailfeed': {'ops': 'all', 'timeout': CACHE_ONE_HOUR},

    'core.subscription': {'ops': 'all', 'timeout': CACHE_ONE_DAY},
    'core.usersubscriptions': {'ops': 'all', 'timeout': CACHE_ONE_DAY},
    'core.userfeeds': {'ops': 'all', 'timeout': CACHE_ONE_DAY},

    # Other objects only use MANUAL caching, not automatic. Read
    # https://github.com/Suor/django-cacheops#performance-tips to
    # understand why. Anyway, even on 1flow.io we don't need that
    # level of 'all-things' cached.
    '*.*': {'timeout': CACHE_ONE_DAY},
}

# In development, I now use a cache for enhanced reading speed
# and production-like behaviour check. But in case I need to
# disable it, just uncomment the next two lines.
#
# if DEBUG:
#    CACHES['default']['BACKEND']  = \
#       'django.core.cache.backends.dummy.DummyCache'

SELECT2_MEMCACHE_HOST = '127.0.0.1'
SELECT2_MEMCACHE_PORT = '11211'

# Be sure our multiple sites don't collide,
# but keep the prefix as short as possible.
CACHE_MIDDLEWARE_KEY_PREFIX = '%02d' % SITE_ID
