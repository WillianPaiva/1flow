
CACHES['default']['BACKEND']  = 'django.core.cache.backends.dummy.DummyCache'
CACHES['default']['LOCATION'] = '127.0.0.1:11211'

# Put the development / test contents not in the production DB (which is 0).
REDIS_DB = 1
