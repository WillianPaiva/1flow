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

REDIS_CACHE_DB = os.environ.get('REDIS_CACHE_DB')

CACHE_HOST, CACHE_PORT, CACHE_DB_NUM = REDIS_CACHE_DB.split(':', 3)

CACHES = {
    'default': {
        'BACKEND': 'redis_cache.cache.RedisCache',
        # Don't set any fallback, we *need* to have this configured in `.env`.
        'LOCATION': os.environ.get('REDIS_CACHE_DB'),

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
        'BACKEND': 'redis_cache.cache.RedisCache',
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

CACHEOPS = {
    # Automatically cache any User.objects.get() calls
    # for 30 minutes. This includes request.user or
    # post.author access, where Post.author is a foreign
    # key to auth.User.
    'auth.user': {'ops': 'get', 'timeout': 60 * 30},

    # Automatically cache all gets and queryset fetches
    # to other django.contrib.auth and oneflow.base models
    # for an hour.
    'auth.*': {'ops': ('fetch', 'get'), 'timeout': 60 * 60},
    'base.*': {'ops': ('fetch', 'get'), 'timeout': 60 * 60},

    # Cache gets, fetches, counts and exists to Permission
    # 'all' is just an alias for ('get', 'fetch', 'count', 'exists')
    'auth.permission': {'ops': 'all', 'timeout': 60 * 60},

    'core.processor': {'ops': 'all', 'timeout': 60 * 60},
    'core.processingchain': {'ops': 'all', 'timeout': 60 * 60},
    'core.chaineditem': {'ops': 'all', 'timeout': 60 * 60},

    # Enable manual caching on all other models with default timeout of an hour
    # Use Post.objects.cache().get(...)
    #  or Tags.objects.filter(...).order_by(...).cache()
    # to cache particular ORM request.
    # Invalidation is still automatic
    #
    # '*.*': {'ops': (), 'timeout': 60 * 60},
    #
    # And since ops is empty by default you can rewrite last line as:
    '*.*': {'timeout': 60 * 60},
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
