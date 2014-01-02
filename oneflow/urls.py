# -*- coding: utf-8 -*-

from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.i18n import i18n_patterns
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from .api import v1_api

# This is our ".admin" module. it runs autodiscover() automatically.
import admin
admin.autodiscover()

# We need to import this after Django's standard autodiscover().
from mongoadmin import site as admin_site

import core.views

handler404 = 'oneflow.base.views.not_found_handler'
handler500 = 'oneflow.base.views.error_handler'
handler503 = 'oneflow.base.views.maintenance_mode'

# urlpatterns = patterns('',
#     url(r'^sitemap\.xml$', 'sitemap.view', name='sitemap_xml'),
# )

urlpatterns = patterns(
    '',
    url(r'', include('oneflow.base.urls')),
    url(r'', include('social_auth.urls')),
    url(r'^robots\.txt$', TemplateView.as_view(template_name='robots.txt',
        content_type='text/plain')),
    url(r'^humans\.txt$', TemplateView.as_view(template_name='humans.txt',
        content_type='text/plain')),
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^djangojs/', include('djangojs.urls')),

    #
    # HEADS UP: this URL belongs to `core` and is not translated.
    #           This is an hard-coded exception.
    #
    url(ur'^import/contacts/success/$',
        login_required(never_cache(core.views.import_contacts_authorized)),
        name='import_contacts_authorized'),
)

urlpatterns += i18n_patterns(
    '',
    # NEVER use r'^$', this won't work as expected. Use r''.
    url(r'', include('oneflow.landing.urls')),
    url(r'', include('oneflow.core.urls')),
)

# WARNING: when sites are spread across different machines, rosetta
# must be migrated to run on only one dedicated, to avoid messing
# with partially translated .PO files on many 1flow servers.
if 'rosetta' in settings.INSTALLED_APPS:
    urlpatterns += patterns(
        '', url(r'^translate/', include('rosetta.urls')),
    )

if 'debug_toolbar_user_panel' in settings.INSTALLED_APPS:
    urlpatterns += patterns(
        '', url(r'', include('debug_toolbar_user_panel.urls')),
    )

urlpatterns += patterns(
    '',
    # Not automatically enabled.
    # cf. http://django-select2.readthedocs.org/en/latest/get_started.html#installation # NOQA
    #url(r'^select2/', include('django_select2.urls')),
    url(r'^grappelli/', include('grappelli.urls')),
    #url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin_site.urls)),
)

urlpatterns += patterns(
    '',
    url(r'^api/', include(v1_api.urls)),
)

# This will add urls only when DEBUG=True
# cf. https://docs.djangoproject.com/en/1.5/ref/contrib/staticfiles/
#           #django.contrib.staticfiles.urls.staticfiles_urlpatterns
urlpatterns += staticfiles_urlpatterns()
