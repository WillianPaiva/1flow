# -*- coding: utf-8 -*-
# Django common settings for oneflow project.
# These are overridden in hostname.py specific files.
#
# Here we define the settings for the test platform.
# Production will override only the needed directives.

import os

# We need to go down 3 times because we start from
# `oneflow/settings/snippets/common.py` instead of plain `oneflow/settings.py`.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
BASE_ROOT    = os.path.dirname(PROJECT_ROOT)

ADMINS   = (('Olivier Cortès', 'oc@1flow.net'), )
MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'oneflow',
        'USER': 'oneflow',
        'PASSWORD': '8jxcWaAfPJT3mV',
        'HOST': '',
        'PORT': '',
    }
}

REDIS_DB = 0

GRAPPELLI_ADMIN_TITLE = '1flow administration'

ALLOWED_HOSTS = []
TIME_ZONE     = 'Europe/Paris'
LANGUAGE_CODE = 'en-us'

USE_I18N = True
USE_L10N = True
USE_TZ   = True

MEDIA_ROOT = os.path.join(BASE_ROOT, 'media')
MEDIA_URL  = '/media/'

STATIC_ROOT = os.path.join(BASE_ROOT, 'static')
STATIC_URL  = '/static/'

STATICFILES_DIRS = (
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

SECRET_KEY = '1!ps20!7iya1ptgluj@2u50)r!fvl*%+6qbxar2jn9y$@=eme!'

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'raven.contrib.django.raven_compat.middleware.'
    'SentryResponseErrorIdMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'oneflow.urls'

WSGI_APPLICATION = 'oneflow.wsgi.application'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT, 'templates')
)

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
    'south',
    'redisboard',
    'memcache_status',
    'widget_tweaks',
    'oneflow.core',
    'oneflow.landing',
)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyLibMCCache',
        'LOCATION': '127.0.0.1:11211',
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
        },
        # critical errors are logged to sentry
        'sentry': {
            'level': 'ERROR',
            #'filters': ['require_debug_false'],
            'class': 'raven.contrib.django.handlers.SentryHandler',
        },
    },
    'loggers': {
        # This is the "catch all" logger
        '': {
            'handlers': ['console', 'mail_admins', 'sentry'],  # 'syslog',
            'level': 'DEBUG',
            'propagate': False,
        },
    }
}
