# -*- coding: utf-8 -*-
from django.conf.urls import patterns, url
from django.views.generic import TemplateView
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.decorators import login_required

from .views import (home, register,
                    google_reader_import,
                    google_reader_import_stats,
                    google_reader_import_status)

urlpatterns = patterns(
    'oneflow.core.views',
    url(_(r'^home/$'), login_required(home), name='home'),
    url(_(r'^register/$'), register, name='register'),
    url(_(r'^signin_error/$'), TemplateView.as_view(
        template_name='signin_error.html'), name='signin_error'),
    url(_(r'^grimport/$'), login_required(google_reader_import),
        name='google_reader_import'),
    url(_(r'^grstats/$'), login_required(google_reader_import_stats),
        name='google_reader_import_stats'),  # SHOULD VANISH in favor of status.
    url(_(r'^grstatus/$'), login_required(google_reader_import_status),
        name='google_reader_import_status'),
)

urlpatterns += patterns(
    'django.contrib.auth.views',
    url(_(r'^signin/$'), 'login',
        {'template_name': 'signin.html'}, name='signin'),
    url(_(r'^signout/$'), 'logout',
        {'template_name': 'signout.html'}, name='signout'),
)
