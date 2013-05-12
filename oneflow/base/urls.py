# -*- coding: utf-8 -*-
from django.conf.urls import patterns, url

urlpatterns = patterns(
    'oneflow.base.views',
    url(r'^500/?$', 'error_handler',
        name='view_500', kwargs={'raise_exception': False}),
    url(r'^500/sentry$', 'error_handler', name='view_500'),
    url(r'^crash/?$', 'crash', name='crash'),
)
