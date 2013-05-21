
DATABASES['default'] = dj_database_url.config(
    'postgres://oneflow:8jxcWaAfPJT3mV@localhost/oneflow_dev')

mongoengine.connect('oneflow_dev')

