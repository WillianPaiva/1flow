# -*- coding: utf-8 -*-
# Debug-toolbar related
"""
    Copyright 2013 Olivier Cortès <oc@1flow.io>

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

# NOTE: INSTALLED_APPS is a list (not a tuple)
# in 1flow, because of the conditional landing.
INSTALLED_APPS += [
    'debug_toolbar',

    # WARNING: user panel is not compatible with djdt 1.x
    #'debug_toolbar_user_panel',
    'template_timings_panel',
    #'debug_toolbar_mongo',
]

MIDDLEWARE_CLASSES += ('debug_toolbar.middleware.DebugToolbarMiddleware', )

DEBUG_TOOLBAR_PANELS = (
    'debug_toolbar.panels.redirects.RedirectsPanel',
    'debug_toolbar.panels.request.RequestPanel',
    'debug_toolbar.panels.headers.HeadersPanel',
    'debug_toolbar.panels.templates.TemplatesPanel',
    #'template_timings_panel.panels.TemplateTimings.TemplateTimings',
    #'debug_toolbar_mongo.panel.MongoDebugPanel',
    'debug_toolbar.panels.cache.CachePanel',
    'debug_toolbar.panels.sql.SQLPanel',
    'debug_toolbar.panels.timer.TimerPanel',
    'debug_toolbar.panels.logging.LoggingPanel',
    'debug_toolbar.panels.staticfiles.StaticFilesPanel',
    #'debug_toolbar_user_panel.panels.UserPanel',
    #'debug_toolbar.panels.signals.SignalsPanel',
    #'debug_toolbar.panels.logging.LoggingPanel',
    'debug_toolbar.panels.settings.SettingsPanel',
    'debug_toolbar.panels.versions.VersionsPanel',
)

# If it becomes too slow, activate this.
#DEBUG_TOOLBAR_MONGO_STACKTRACES = False

DEBUG_TOOLBAR_CONFIG = {
    #'INTERCEPT_REDIRECTS': False,
    'ENABLE_STACKTRACES' : False,
    #'SHOW_TOOLBAR_CALLBACK': custom_show_toolbar,
    #'EXTRA_SIGNALS': ['myproject.signals.MySignal'],
    #'HIDE_DJANGO_SQL': False,
    #'TAG': 'div',
}
