# -*- coding: utf-8 -*-
from django.conf.urls import patterns, url
from django.utils.translation import ugettext_lazy as _

urlpatterns = patterns(
    'oneflow.core.views',
    url(_(r'^home/$'), 'home', name='home'),
)
