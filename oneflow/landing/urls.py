# -*- coding: utf-8 -*-
from django.conf.urls import patterns, url

import views

urlpatterns = patterns(
    'oneflow.landing',
    url(r'^$', views.home, name='landing_home'),
    url(r'^thanks/(?P<already_registered>\w+)?$', views.thanks,
        name='landing_thanks'),
)
