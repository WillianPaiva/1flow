# -*- coding: utf-8 -*-
# Django common settings for oneflow project.
# These are overridden in hostname.py specific files.
#
# Here we define the settings for the test platform.
# Production will override only the needed directives.

import os

# We need to go down 2 times because the starting point of these settings is
# `project/settings/__init__.py`, instead of good old `project/settings.py`.
# NOTE: the `execfile()` on snippets doesn't add depth: even if the current
# file is `project/settings/snippets/common.py`, this doesn't count.
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
BASE_ROOT    = os.path.dirname(PROJECT_ROOT)

ADMINS   = (('Olivier Cortès', 'oc@1flow.net'), )
MANAGERS = ADMINS

GRAPPELLI_ADMIN_TITLE = '1flow administration'

ALLOWED_HOSTS = []
TIME_ZONE     = 'Europe/Paris'
LANGUAGE_CODE = 'en'

# dummy ugettext function, as django's docs say
ugettext = lambda s: s

# Please update ../Makefile if you add/del a language.
LANGUAGES = (
    ('en', ugettext(u'English')),
    ('en-us', ugettext(u'English (US)')),
    ('en-gb', ugettext(u'English (UK)')),
    ('fr', ugettext(u'Français')),
#    ('fr-fr', ugettext(u'Français (FR)')),
    ('es', ugettext(u'Español')),
#    ('es-es', ugettext(u'Español (ES)')),
)

# This fake language is used by translators to keep
# variants and translations notes handy in the admin interface.
TRANSMETA_LANGUAGES = LANGUAGES + (('nt', ugettext(u'Notes — variants')), )

USE_I18N = True
USE_L10N = True
USE_TZ   = True

# Activate if bandwidth is limited, at some CPU cost.
#USE_ETAGS = True

MEDIA_ROOT = os.path.join(BASE_ROOT, 'media')
MEDIA_URL  = '/media/'

STATIC_ROOT = os.path.join(BASE_ROOT, 'static')
STATIC_URL  = '/static/'

SECRET_KEY = '1!ps20!7iya1ptgluj@2u50)r!fvl*%+6qbxar2jn9y$@=eme!'

ROOT_URLCONF = 'oneflow.urls'

WSGI_APPLICATION = 'oneflow.wsgi.application'

STATICFILES_DIRS = (
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    #'ConditionalGetMiddleware',
    ('raven.contrib.django.raven_compat.middleware.'
        'SentryResponseErrorIdMiddleware'),
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    #'GZipMiddleware',
)

TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT, 'templates')
)

# Not any yet.
#TEMPLATE_CONTEXT_PROCESSORS += ('oneflow.base.context.…', )

INSTALLED_APPS = (
    'raven.contrib.django.raven_compat',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    #'grappelli.dashboard',
    'grappelli',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django_reset',
    'south',
    'transmeta',
    'redisboard',
    'markdown_deux',
    'memcache_status',
    'widget_tweaks',
    'oneflow.base',
    'oneflow.landing',
    #'oneflow.core',
)

MARKDOWN_DEUX_STYLES = {
    'default': {
        'extras': {
            'code-friendly': None,
            'cuddled-lists': None,

        },
        'safe_mode': 'escape',
    },
    'raw': {
        'extras': {
            'code-friendly': None,
            'cuddled-lists': None,

        },
        'safe_mode': False,
    }
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'formatters': {
        'verbose': {
            'format': '[contactor] %(levelname)s %(asctime)s %(message)s'
        },
    },
    'handlers': {
        # Send all messages to console
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
        # Send info messages to syslog
        # 'syslog':{
        #     'level':'INFO',
        #     'class': 'logging.handlers.SysLogHandler',
        #     'facility': SysLogHandler.LOG_LOCAL2,
        #     'address': '/dev/log',
        #     'formatter': 'verbose',
        # },
        # Warning messages are sent to admin emails
        'mail_admins': {
            'level': 'WARNING',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True,
        },
        # critical errors are logged to sentry
        'sentry': {
            'level': 'ERROR',
            #'filters': ['require_debug_false'],
            'class': 'raven.contrib.django.handlers.SentryHandler',
        },
    },
    'loggers': {
        # Don't log SQL queries, this bothers me.
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'INFO',
        },

        # This is the "catch all" logger
        '': {
            'handlers': ['console', 'mail_admins', 'sentry'],  # 'syslog',
            'level': 'DEBUG',
            'propagate': False,
        },
    }
}
