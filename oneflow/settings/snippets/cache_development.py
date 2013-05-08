
CACHES['default']['BACKEND']  = 'django.core.cache.backends.dummy.DummyCache'

# Put the development / test contents not in the production DB (which is 0).
REDIS_DB = 1
