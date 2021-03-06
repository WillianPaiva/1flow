# -*- coding: utf-8 -*-
#
# Django common settings for oneflow project.
# These are overridden in hostname.py specific files.
#
# Here we define the settings for the test platform.
# Production will override only the needed directives.
#
u"""
Copyright 2013-2014 Olivier Cortès <oc@1flow.io>.

This file is part of the 1flow project.

1flow is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of
the License, or (at your option) any later version.

1flow is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with 1flow.  If not, see http://www.gnu.org/licenses/

"""

import os
import sys
import logging
import warnings

from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy

# dummy ugettext function, as django's docs say
ugettext = lambda s: s

# This is imported here to benefit to all other included snippets.
from sparks import platform  # NOQA

# We need to go down 2 times because the starting point of these settings is
# `project/settings/__init__.py`, instead of good old `project/settings.py`.
# NOTE: the `execfile()` on snippets doesn't add depth: even if the current
# file is `project/settings/snippets/common.py`, this doesn't count.
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
BASE_ROOT    = os.path.dirname(PROJECT_ROOT)

# This one is hardcoded for all admin links, to avoid the need to
# replace it everywhere when mongoadmin wants to change things…
NONREL_ADMIN = u'/admin/nonrel/'

ADMINS   = (('Olivier Cortès', 'oc@1flow.io'), )
MANAGERS = ADMINS

from oneflow import VERSION

GRAPPELLI_ADMIN_TITLE = u'1flow v%s administration%s' % (VERSION, u' — DEVEL'
                                                         if DEBUG else u'')
MONGOADMIN_OVERRIDE_ADMIN = True

ALLOWED_HOSTS = []
TIME_ZONE     = 'Europe/Paris'
LANGUAGE_CODE = 'en'

# Translation workflows:
# - in the DB: all languages variants are accessible and empty by default.
#      'en' takes precedence on 'en-US'. As translators have access to all
#       translations, this is a bit awkward, but we don't have the choice
#       because we must match the Django application languages. We could
#       manually hide the 'en-us' to avoid confusion, but this would imply
#       dirty hacking in all admin modules and I don't find it worth.
# - in the webapp: 'en' is *always* defined because the developers create
#       english strings. For translators to be able to override them
#       without needing commit access, we use the 'en-us' language, which
#       takes precedence. This is not perfect, because other 'en-*'
#       users will get the 'bare' strings which can have errors, but at
#       least our translators have access to en-US strings the same way
#       they access other languages.
LANGUAGES = (
    ('en', ugettext(u'English')),
    # We're not ready to handle a british translation (no resource…)
    # ('en-gb', ugettext(u'English (UK)')),
    ('fr', ugettext(u'Français')),

    # Activate these later when we need them.
    #    ('es', ugettext(u'Español')),
    #    ('fr-CA', ugettext(u'Français (FR)')),
    #    ('es-XX', ugettext(u'Español (ES)')),
)

TRANSMETA_LANGUAGES = LANGUAGES + (
    # The 'nt' fake language is used by translators to keep
    # variants and translations notes handy in the admin interface.
    ('nt', ugettext(u'Notes — variants')),
)

# We use oneflow.base.models.User as a drop-in replacement.
AUTH_USER_MODEL = 'base.User'

USE_I18N = True
USE_L10N = True
USE_TZ   = True

# Activate if bandwidth is limited, at some CPU cost.
# USE_ETAGS = True

MEDIA_ROOT = os.path.join(BASE_ROOT, 'media')
MEDIA_URL  = '/media/'

STATIC_ROOT = os.path.join(BASE_ROOT, 'static')
STATIC_URL  = '/static/'

SECRET_KEY = '1!ps20!7iya1ptgluj@2u50)r!fvl*%+6qbxar2jn9y$@=eme!'

ROOT_URLCONF = 'oneflow.urls'

WSGI_APPLICATION = 'oneflow.wsgi.application'

STATICFILES_DIRS = (
    ('icon-themes', '/usr/share/icons'),
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

STATICFILES_STORAGE = 'pipeline.storage.PipelineCachedStorage'

# PIPELINE_ENABLED = False

# Until our own modules are ready to be wrapped, don't use this.
PIPELINE_DISABLE_WRAPPER = True

PIPELINE_COMPILERS = (
    'pipeline.compilers.less.LessCompiler',
    # We don't use the from django-pipeline-compass compiler,
    # it breaks bootstrap-responsive.
    #       'pipeline_compass.compiler.CompassCompiler',
    #
    # Intead, we use the one from django-pipeline-compass-rubygem, which
    # runs the official 'compass' Ruby binary in a subshell.
    #
    # WARNING, though: both packages install at the same location.
    # As of 20130524, django-pipeline-compass-rubygem is itself broken,
    # because it doesn't ship the __init__.py. Thus it doesn't work alone;
    # but it doesn't depend on django-pipeline-compass, which makes the
    # whole process heavily error-prone because we need to install both,
    # but it's not issued anywhere.
    #
    # Finally, after installing 2 python packages and Ruby + the rubygem,
    # everything works as expected. I personally prefer using the official
    # 'compass' and have a working CSS, than an un-maintained python erzatz
    # which doesnt work and breaks CSSs without any error displayed.
    'pipeline_compass.compass.CompassCompiler',
    'pipeline.compilers.coffee.CoffeeScriptCompiler',
)

PIPELINE_CSS = {

    # •••••••••••••••••••••••••••••••••••••••••••••••••••••••••• vendor

    # TODO: the 'vendor-all' target.

    # ——————————————————————————————————————————————————————————————— Bootstrap

    'bootstrap': {
        'source_filenames': (
            'vendor/bootstrap/3.0.3/less/bootstrap.less',
            'vendor/scrollbars/scrollbars.css',
            'vendor/bootstrap-remote-data/css/jquery.loadmask.css',
        ),
        'output_filename': 'css/bootstrap.css',
    },

    'bootstrap-2': {
        'source_filenames': (
            'vendor/bootstrap/2.3.2/less/bootstrap.less',
        ),
        'output_filename': 'css/bootstrap-2.css',
    },

    'bootstrap-2-responsive': {
        'source_filenames': (
            'vendor/bootstrap/2.3.2/less/bootstrap.less',
            'vendor/bootstrap/2.3.2/less/responsive.less',
        ),
        'output_filename': 'css/bootstrap-2-responsive.css',
    },

    # ———————————————————————————————————————————————————————————— Font-awesome

    'font-awesome': {
        'source_filenames': (
            'vendor/font-awesome/less/font-awesome.less',
        ),
        'output_filename': 'css/font-awesome.css',
    },
    'font-awesome-ie7': {
        'source_filenames': (
            'vendor/font-awesome/less/font-awesome-ie7.less',
        ),
        'output_filename': 'css/font-awesome-ie7.css',
    },

    # —————————————————————————————————————————————————————————————— 1flow core
    # The core uses Bootstrap 3. Either Detail-Admin donated by Erick Alvarez,
    # or any bootswatch theme: just change the value in the constance config.

    'core-bootswatch': {
        'source_filenames': (
            'sass/styles-core-bootswatch.scss',
            'vendor/scrollbars/scrollbars.css',
        ),

        'output_filename': 'css/core-bootswatch.css',
    },

    'core-detail-admin': {
        'source_filenames': (
            'sass/styles-core-detail-admin.scss',
        ),
        'output_filename': 'css/core-detail-admin.css',
    },

    # —————————————————————————————————————————————————————— 1flow landing page
    # As of 201401xx, the landing page is still Bootstrap 2.

    'core-bootstrap-bare': {
        'source_filenames': (
            'sass/styles-core-bootstrap-bare.scss',
        ),
        'output_filename': 'css/core-bootstrap-bare.css',
    }
}

PIPELINE_JS = {

    # •••••••••••••••••••••••••••••••••••••••••••••••••••••••••• vendor

    'vendor-global': {
        # This one includes all external dependancies
        # (eg. non 1flow sources) for a one-file-only dep.
        'source_filenames': (
            'vendor/raven.js/1.0.8/raven.js',
            'vendor/underscorejs/1.5.1/underscore.js',
            'vendor/mousetrap/1.4.2/mousetrap.js',
            'vendor/hammerjs/1.0.5/hammer.js',
            'vendor/pnotify/1.2/jquery.pnotify.js',
            'vendor/jquery-easing/1.3/jquery.easing.js',
            'vendor/jquery-color/2.1.2/jquery.color.js',

            # WARNING: order matters: tooltip must be included before popover.
            # This order is a copy-n-paste of Bootstrap 3.0.3's Gruntfile.js.
            'vendor/bootstrap/3.0.3/js/transition.js',
            'vendor/bootstrap/3.0.3/js/alert.js',
            'vendor/bootstrap/3.0.3/js/button.js',
            'vendor/bootstrap/3.0.3/js/carousel.js',
            'vendor/bootstrap/3.0.3/js/collapse.js',
            'vendor/bootstrap/3.0.3/js/dropdown.js',
            'vendor/bootstrap/3.0.3/js/modal.js',
            'vendor/bootstrap/3.0.3/js/tooltip.js',
            'vendor/bootstrap/3.0.3/js/popover.js',
            'vendor/bootstrap/3.0.3/js/scrollspy.js',
            'vendor/bootstrap/3.0.3/js/tab.js',
            'vendor/bootstrap/3.0.3/js/affix.js',
        ),

        'output_filename': 'js/min/vendor-global.js',
    },
    #
    # TODO: find CDNs versions of these, and merge
    # the 2 vendor-* target for simplification.
    #
    'vendor-local': {
        'source_filenames': (
            'vendor/bootstrap-remote-data/js/bootstrap-remote-tabs.min.js',
            'vendor/bootstrap-remote-data/js/jquery.loadmask.js',

            'vendor/scrollbars/scrollbars.js',
            'vendor/showdown/showdown.js',
            'vendor/showdown/extensions/twitter.js',

            'vendor/moment/moment.js',
            'vendor/moment/langs/*.js',

            'vendor/other/*.js',

            # NOTE: we use or own implementation
            # of django-endless-pagination JS.
        ),
        'output_filename': 'js/min/vendor-local.js',
    },

    # NOTE: we use or own implementation
    # of django-endless-pagination JS.
    'vendor-endless-pagination': {
        'source_filenames': (
            'endless_pagination/js/endless-pagination.js',
        ),
        'output_filename': 'js/min/endless-pagination.js',
    },

    # ••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• 1flow

    'utils': {
        'source_filenames': (
            'js/utils/*.js',
            'js/common.js',
        ),
        'output_filename': 'js/min/utils.js',
    },

    'feed-selector': {
        'source_filenames': (
            'js/utils/*.js',
            'js/common.js',
            'js/feed-selector.js',
        ),
        'output_filename': 'js/min/feed-selector.js',
    },

    'read-endless': {
        'source_filenames': (
            'js/utils/*.js',
            'js/common.js',
            'js/read-one.js',
            'js/read-endless.js',
        ),
        'output_filename': 'js/min/read-endless.js',
    },

    'read-one': {
        'source_filenames': (
            'js/utils/*.js',
            'js/common.js',
            'js/read-one.js',
        ),
        'output_filename': 'js/min/read-one.js',
    },

    'core': {
        'source_filenames': (
            'js/utils/*.js',
            'js/common.js',
            'js/core-init.js',
        ),
        'output_filename': 'js/min/core.js',
    },

    'ember-core': {
        'source_filenames': (
            'js/ember-core/core.js',
            'js/ember-core/controllers/*.js',
            'js/ember-core/models/*.js',
            'js/ember-core/views/*.js',
            'js/ember-core/routes/*.js',
            'js/ember-core/helpers/*.js',
            'js/ember-core/end.js',
        ),
        'output_filename': 'js/min/ember-core.js',
    }
}

if TEMPLATE_DEBUG:
    # Because Django's cached templates doesn't use a proper caching
    # engine, it doesn't benefit from our DummyCache development setting…
    # We have to deactivate it completely for development.
    # cf. http://stackoverflow.com/a/4071488/654755
    TEMPLATE_LOADERS = (
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    )

else:
    TEMPLATE_LOADERS = (
        ('django.template.loaders.cached.Loader', (
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
        )),
    )

# We always include the *Cache* middlewares. In development &
# pre-production it's a dummy cache, allowing to keep them here.
MIDDLEWARE_CLASSES = (
    # 'ConditionalGetMiddleware',

    # Our middleware will automatically disable itself in non-DEBUG condition.
    'oneflow.base.utils.middleware.PrintExceptionMiddleware',

    ('raven.contrib.django.raven_compat.middleware.'
        'SentryResponseErrorIdMiddleware'),
    # 'raven.contrib.django.raven_compat.middleware.Sentry404CatchMiddleware',

    'django.middleware.cache.UpdateCacheMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',

    # TODO: test and activate this.
    # 'django.middleware.transaction.TransactionMiddleware',

    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'async_messages.middleware.AsyncMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
    'social.apps.django_app.middleware.SocialAuthExceptionMiddleware',

    # account's MW must come after 'auth', else they crash.
    #
    # BTW, account's LocaleMiddleware produces a strange bug
    # where /en/ doesn't exist anymore and we have two /fr/
    # entries, making / fail to load. The logout process
    # behave badly because of that. BTW again, I didn't see
    # what it brought / added to the current implementation,
    # leaving it disabled changes nothing.
    # 'account.middleware.LocaleMiddleware',
    'account.middleware.TimezoneMiddleware',

    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'maintenancemode.middleware.MaintenanceModeMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
)

if not DEBUG:
    MIDDLEWARE_CLASSES = MIDDLEWARE_CLASSES[:-1] + (
        'pipeline.middleware.MinifyHTMLMiddleware',
    ) + MIDDLEWARE_CLASSES[-1:]

# Use Django-redis as session backend.
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'sessions'

REDISBOARD_DETAIL_FILTERS = ['(uptime|db|last|total).*', ]

TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT, 'templates')
)

# cf. https://docs.djangoproject.com/en/1.5/ref/settings/#template-context-processors # NOQA
TEMPLATE_CONTEXT_PROCESSORS = (
    # NOTE: ….debug is added only if DEBUG=True, later in another snippet.
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.tz',
    'django.core.context_processors.request',
    'absolute.context_processors.absolute',
    'constance.context_processors.config',
    'django.contrib.auth.context_processors.auth',
    'account.context_processors.account',
    'django.contrib.messages.context_processors.messages',

    # Social auth
    'social.apps.django_app.context_processors.backends',
    'social.apps.django_app.context_processors.login_redirect',

    # `base` processors
    'oneflow.base.context_processors.oneflow_version',
    'oneflow.base.context_processors.django_settings',
    'oneflow.base.context_processors.maintenance_mode',

    # `core` processors
    'oneflow.core.context_processors.mongodb_user',
    'oneflow.core.context_processors.models_constants',
    'oneflow.core.context_processors.social_things',
)

# NOTE: INSTALLED_APPS is a list (not a tuple)
# in 1flow, because of the conditional landing.
INSTALLED_APPS = [
    'raven.contrib.django.raven_compat',
    'django.contrib.auth',
    'account',
    'polymorphic',
    'cacheops',
    # 'django_pickling',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    # 'django.contrib.sites',

    # We could use Django's `humanize`, it produces more
    # detailled `*delta()` than the external `humanize` module.
    #
    # BUT, our naturaldelta() tag already takes a delta, an int (seconds)
    # or even a datetime to compute the delta from now.
    #
    # 'django.contrib.humanize',

    'django.contrib.messages',
    'django.contrib.staticfiles',
    # 'grappelli.dashboard',
    'grappelli',
    'mongoadmin',
    'json_field',
    'django_extensions',
    'autocomplete_light',

    'django.contrib.admin',
    # 'django.contrib.admindocs',
    'django_reset',
    'django_shell_ipynb',
    'gunicorn',
    'south',
    'south_admin',
    # 'maintenancemode', — not needed at all, the middleware is sufficient.
    'transmeta',
    'mptt',
    'sorting_bootstrap',

    'django_file_form',
    'django_file_form.ajaxuploader',

    # Seems not working with grappelli.
    # 'django_object_actions',

    # Order matters for inplace & friends.
    'inplaceeditform_bootstrap',
    'inplaceeditform',
    # 'inplaceeditform_extra_fields',
    # 'bootstrap3_datetime',

    'logentry_admin',
    'constance',
    'overextends',
    # 'django_markdown',
    'writingfield',
    'redisboard',
    'djcelery',
    'markdown_deux',
    'djangojs',
    'django_select2',
    'pipeline',
    'absolute',
    'endless_pagination',

    # `infinite_pagination` doesn't work on MongoEngine QuerySet.
    # 'infinite_pagination',

    'mathfilters',
    'widget_tweaks',
    'simple_history',

    'oneflow.base',
    'oneflow.profiles',
    'oneflow.core',
    # OMG: order matters! as DSA depends on user model,
    # it must come after 'oneflow.base' wich contains it.
    # Without this, tests fail to create database!
    'social.apps.django_app.default',
    'tastypie',
    'tastypie_mongoengine',
]

# ———————————————————————————————————————————————————————— django-user-accounts

ACCOUNT_EMAIL_UNIQUE = True
ACCOUNT_EMAIL_CONFIRMATION_REQUIRED = True
# ACCOUNT_LOGIN_REDIRECT_URL =
ACCOUNT_LOGOUT_REDIRECT_URL = u'signin'
ACCOUNT_EMAIL_CONFIRMATION_ANONYMOUS_REDIRECT_URL = u'signin'
ACCOUNT_EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL = u'home'
ACCOUNT_PASSWORD_CHANGE_REDIRECT_URL = u'profile'
ACCOUNT_PASSWORD_RESET_REDIRECT_URL = u'signin'

# —————————————————————————————————————————————————————————— django-inplaceedit

INPLACEEDIT_EDIT_EMPTY_VALUE = ugettext_lazy(u'Click to edit')
INPLACEEDIT_AUTO_SAVE = True
INPLACEEDIT_EVENT = "click"
# INPLACEEDIT_DISABLE_CLICK = True  # For inplace edit text into a link tag
# INPLACEEDIT_EDIT_MESSAGE_TRANSLATION = 'Write a translation' # transmeta option  # NOQA
INPLACEEDIT_SUCCESS_TEXT = ugettext_lazy(u'Successfully saved')
INPLACEEDIT_UNSAVED_TEXT = ugettext_lazy(u'You have unsaved changes')
# INPLACE_ENABLE_CLASS = 'form-control'
DEFAULT_INPLACE_EDIT_OPTIONS = {
    'auto_height': 1,            # be gentle, don't try to guess anything.
    'class_inplace': 'form',     # Be a little bootstrap compatible.
    'tag_name_cover': 'span',     # Make the editables more clickable.
    '__widget_class': 'form-control',   # DOES NOT WORK, ISSUE Github #53
}
# modify the behavior of the DEFAULT_INPLACE_EDIT_OPTIONS usage, if True
# then it use the default values not specified in your template, if False
# it uses these options only when the dictionnary is empty (when you do put
# any options in your template)
# DEFAULT_INPLACE_EDIT_OPTIONS_ONE_BY_ONE = True
ADAPTOR_INPLACEEDIT_EDIT = 'oneflow.base.models.OwnerOrSuperuserEditAdaptor'
ADAPTOR_INPLACEEDIT = {
    # example: 'tiny': 'inplaceeditform_extra_fields.fields.AdaptorTinyMCEField'
    # 'date': 'inplaceeditform_bootstrap.fields.AdaptorDateBootStrapField',
    # 'datetime': 'inplaceeditform_bootstrap.fields.AdaptorDateTimeBootStrapField',  # NOQA
}
# INPLACE_GET_FIELD_URL = None # to change the url where django-inplaceedit use to get a field  # NOQA
# INPLACE_SAVE_URL = None # to change the url where django-inplaceedit use to save a field  # NOQA

# A django-inplaceedit-bootstrap setting.
INPLACEEDIT_EDIT_TOOLTIP_TEXT = ugettext_lazy(u'Click to edit')

# ———————————————————————————————————————————————————— django-endlesspagination

ENDLESS_PAGINATION_PER_PAGE = 25 if DEBUG else 50

# This is done directly in the templates.
# ENDLESS_PAGINATION_LOADING  = ugettext_lazy(u'loading more entries…')

# —————————————————————————————————————————————————————————————— django-select2

AUTO_RENDER_SELECT2_STATICS = False
GENERATE_RANDOM_SELECT2_ID = True
ENABLE_SELECT2_MULTI_PROCESS_SUPPORT = True
# See cache.py for Select2 memcache settings.

# ———————————————————————————————————————————————————— Other

JS_CONTEXT_PROCESSOR = 'oneflow.base.utils.JsContextSerializer'

try:
    RAVEN_CONFIG = {
        # We send flower bugs to a dedicated sentry project,
        # it pollutes us too much.
        'dsn': os.environ.get('RAVEN_DSN_FLOWER'
                              if 'flower' in sys.argv
                              or 'shell_ipynb' in sys.argv
                              else 'RAVEN_DSN'),
    }
except KeyError:
    # No RAVEN_DSN*, raven/sentry will not be used.
    # NOTE: it's not documented if raven will crash
    # or not at start without a DSN and at the moment
    # of this writing I have no way to test it.
    pass

STATSD_HOST = os.environ.get('STATSD_HOST', None)

if STATSD_HOST is None:
    del STATSD_HOST

else:
    STATSD_PORT   = int(os.environ.get('STATSD_PORT', 8125))
    STATSD_PREFIX = os.environ.get('STATSD_PREFIX', '1flow')

MAINTENANCE_MODE = os.path.exists(os.path.join(BASE_ROOT, 'MAINTENANCE_MODE'))

MAINTENANCE_IGNORE_URLS = (
    r'^/admin/.*',
)

MARKDOWN_DEUX_STYLES = {
    'default': {
        'extras': {
            # html2text uses _ by default for EM…
            # 'code-friendly': None,
            'cuddled-lists': None,

        },
        'safe_mode': 'escape',
    },
    'code': {
        'extras': {
            'code-friendly': None,
            'cuddled-lists': None,

        },
        'safe_mode': 'escape',
    },
    'raw': {
        'extras': {
            # html2text uses _ by default for EM…
            # 'code-friendly': None,
            'cuddled-lists': None,

        },
        'safe_mode': False,
    },
    'code-raw': {
        'extras': {
            'code-friendly': None,
            'cuddled-lists': None,

        },
        'safe_mode': False,
    }
}

# CONSTANCE_* is to be found in 'snippets/constance*'

# Defaults to ['json', 'xml', 'yaml', 'html', 'plist']
TASTYPIE_DEFAULT_FORMATS = ('json', )
API_LIMIT_PER_PAGE = 10


AUTHENTICATION_BACKENDS = (
    # WARNING: when activating Twitter, we MUST implement the email pipeline,
    # else the social-only registration will fail because user has no mail.

    # 'social.backends.open_id.OpenIdAuth',
    'django.contrib.auth.backends.ModelBackend',
)


CODEMIRROR_PATH = 'vendor/codemirror/4.11'
CODEMIRROR_MODE = 'python'
CODEMIRROR_THEME = 'monokai'
CODEMIRROR_CONFIG = {
    'tabSize': 4,
    'indentWithTabs': False,
    'lineNumbers': True,
    'rulers': [72, 80],

    # These are directly in our custom sublime keymap (in static/vendor/…)
    # 'extraKeys': {
    #     "F9": "toggleFullScreen",
    #     "Esc": "exitFullScreenIfEnabled",
    # }
}
CODEMIRROR_ADDONS_JS = (
    # 'mode/overlay',
    'edit/trailingspace',
    'edit/matchbrackets',

    'search/search',
    'search/matchesonscrollbar',
    'search/match-highlighter',

    'hint/anyword-hint',

    'fold/foldcode',
    'fold/foldgutter',

    'display/fullscreen',
    'display/rulers',
)

CODEMIRROR_ADDONS_CSS = (
    'display/fullscreen',
)
CODEMIRROR_KEYMAP = 'sublime'


# —————————————————————————————————————————————————————————————— 1flow settings


DEFAULT_USER_AGENT = u'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:21.0) Gecko/20100101 Firefox/21.0'  # NOQA


# ————————————————————————————————————————————————————————————————————— Logging

logging.getLogger('oauthlib').setLevel(
    logging.ERROR if DEBUG else logging.CRITICAL)
logging.getLogger('requests_oauthlib').setLevel(
    logging.ERROR if DEBUG else logging.CRITICAL)
logging.getLogger('redis_lock').setLevel(
    logging.ERROR if DEBUG else logging.CRITICAL)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    # 'root': {
    #     'level': 'WARNING',
    #     'handlers': ['sentry'],
    # },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(message)s'
        },
    },
    'handlers': {
        # Send all messages to console
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
        # WARNINGs and critical errors are logged to sentry
        'sentry': {
            'level': 'ERROR',
            # 'filters': ['require_debug_false'],
            'class': 'raven.contrib.django.handlers.SentryHandler',
        },
        # Send info messages to syslog
        # 'syslog':{
        #     'level':'INFO',
        #     'class': 'logging.handlers.SysLogHandler',
        #     'facility': SysLogHandler.LOG_LOCAL2,
        #     'address': '/dev/log',
        #     'formatter': 'verbose',
        # },
        # ERROR messages are sent to admin emails
        'mail_admins': {
            # We don't want any mail for every warning on earth.
            # 'level': 'WARNING',
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True,
        },
    },
    'loggers': {
        # Don't log SQL queries, this bothers me.
        'django.db.backends': {
            'handlers': ['console'],
            # 'level': 'DEBUG' if DEBUG else 'INFO',
            'level': 'INFO',
        },
        'raven': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
        'sentry.errors': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
        # This is the "catch all" logger
        '': {
            'handlers': ['console', 'mail_admins', 'sentry'],  # 'syslog',
            'level': 'DEBUG',
            'propagate': False,
        },
    }
}


# ————————————————————————————————————————————————————————————————————— iPython

if 'shell_plus' in sys.argv:
    os.environ['PYTHONPATH'] = BASE_ROOT + ':.'

# For django-extensions ipython notebook
IPYTHON_ARGUMENTS = [
    # must stay here.
    # '--ext', 'django_extensions.management.notebook_extension',
    '--InteractiveShellApp.extra_extension=django_extensions.management.notebook_extension',
    '--NotebookApp.ip="*"',
    '--NotebookApp.open_browser=False',
    '--NotebookApp.notebook_dir={0}/shell_ipynb'.format(BASE_ROOT),
    # '--debug',
]
