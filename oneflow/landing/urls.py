# -*- coding: utf-8 -*-
from django.conf.urls import patterns, url
from django.utils.translation import ugettext_lazy as _

import views

urlpatterns = patterns(
    'oneflow.landing',
    url(r'^$', views.home, name='landing_home'),
    url(_(r'^thanks/(?P<already_registered>\w+)?$'), views.thanks,
        name='landing_thanks'),
)
