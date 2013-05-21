
DATABASES['default'] = dj_database_url.config(
    'postgres://oneflow:8jxcWaAfPJT3mV@10.0.3.1/oneflow_test')

mongoengine.connect('oneflow_test', host='10.0.3.1')
