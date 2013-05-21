
DATABASES['default'] = dj_database_url.config(
    'postgres://oneflow:8jxcWaAfPJT3mV@10.0.3.1/oneflow')

mongoengine.connect('oneflow', host='10.0.3.1')
