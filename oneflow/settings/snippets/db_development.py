
DATABASES['default'] = dj_database_url.config(
    default='postgres://oneflow:8jxcWaAfPJT3mV@localhost/oneflow_dev')

mongoengine.connect('oneflow_dev')

SESSION_REDIS_HOST = 'localhost'
SESSION_REDIS_DB = 2
