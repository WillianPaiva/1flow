
from django.conf import settings
from django.conf.urls import patterns, include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib import admin

admin.autodiscover()


if settings.SITE_ID == 1:
    urlpatterns = patterns(
        '',

        # NEVER use r'^$', this won't work as expected. Use r''.
        url(r'', include('oneflow.landing.urls')),

    )

else:
    urlpatterns = patterns(
        '',

        # NEVER use r'^$', this won't work as expected. Use r''.
        #url(r'', include('oneflow.core.urls')),

        # url(r'^api/', include('oneflow.api.urls')),

    )

urlpatterns += patterns(
    '',
    url(r'^grappelli/', include('grappelli.urls')),
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),
)

# This will add urls only when DEBUG=True
# cf. https://docs.djangoproject.com/en/1.5/ref/contrib/staticfiles/
#           #django.contrib.staticfiles.urls.staticfiles_urlpatterns
urlpatterns += staticfiles_urlpatterns()
