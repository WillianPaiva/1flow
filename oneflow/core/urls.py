# -*- coding: utf-8 -*-

from django.conf.urls import patterns, url
from django.views.generic import TemplateView
from django.views.decorators.cache import never_cache
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required

from .models.nonrel import Read

from .views import (home, read_with_endless_pagination,
                    help, toggle, read_one,
                    register, profile,
                    set_preference,
                    feed_closed_toggle,
                    google_reader_import,
                    google_reader_import_stop,
                    google_reader_import_status,
                    google_reader_can_import_toggle)


readpatterns = tuple(
    url(attrval.get('list_url'),
        login_required(never_cache(
            read_with_endless_pagination)),
        name=u'read_' + attrval.get('view_name'),
        kwargs={attrkey: True})
    for attrkey, attrval
        in Read.status_data.items()
        if 'list_url' in attrval
)

urlpatterns = patterns(
    'oneflow.core.views',
    url(_(r'^home/$'), login_required(never_cache(home)), name='home'),

    url(_(r'^preference/(?P<base>\w+)[\./](?P<sub>\w+)/(?P<value>\w+)/?$'),
        login_required(never_cache(set_preference)), name='set_preference'),

    url(_(r'^profile/$'), login_required(never_cache(profile)), name='profile'),


    # This one is not activated to the public yet.
    url(_(r'^read/all/$'), staff_member_required(never_cache(
        read_with_endless_pagination)), name='read_all',
        kwargs={'all': True}),

    url(_(r'^read/$'), login_required(never_cache(
        read_with_endless_pagination)), name='read'),

    url(_(r'^read/([0-9a-f]{24,24})/$'),
        login_required(read_one),
        name='read_one'),

    url(_(r'^(?P<klass>\w+)/(?P<oid>\w+)/toggle/(?P<key>\w+.\w+)/?$'),
        login_required(never_cache(toggle)), name='toggle'),

    url(_(r'^help/$'), login_required(help), name='help'),

    url(_(r'^register/$'), register, name='register'),
    url(_(r'^signin_error/$'), TemplateView.as_view(
        template_name='signin_error.html'), name='signin_error'),

    # •••••••••••••••••••••••••••••••••••••••••••••••••••••••••••  Google Reader

    url(_(r'^grimport/(?:(?P<user_id>\d+)/)?$'),
        login_required(google_reader_import),
        name='google_reader_import'),
    url(_(r'^grstop/(?P<user_id>\d+)/$'),
        staff_member_required(google_reader_import_stop),
        name='google_reader_import_stop'),
    url(_(r'^grtoggle/(?P<user_id>\d+)/$'),
        staff_member_required(google_reader_can_import_toggle),
        name='google_reader_can_import_toggle'),
    url(_(r'^grstatus/$'), login_required(google_reader_import_status),
        name='google_reader_import_status'),

    # •••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Staff only

    url(_(r'^feed/(?P<feed_id>\w+)/close/toggle/$'),
        staff_member_required(feed_closed_toggle),
        name='feed_closed_toggle'),

    *readpatterns
)

urlpatterns += patterns(
    'django.contrib.auth.views',
    url(_(r'^signin/$'), 'login',
        {'template_name': 'signin.html'}, name='signin'),
    url(_(r'^signout/$'), 'logout',
        {'template_name': 'signout.html'}, name='signout'),
)
