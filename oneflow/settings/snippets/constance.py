# -*- coding: utf-8 -*-
#
# Default constance keys, and their values.
#

import datetime

#CONSTANCE_REDIS_CONNECTION is to be found in 'snippets/databases*'
CONSTANCE_BACKEND      = 'constance.backends.redisd.RedisBackend'
CONSTANCE_REDIS_PREFIX = 'c0s1f:'

CONSTANCE_CONFIG = {

    # •••••••••••••••••••••••••••••••••••••••••••••••••••••••••• RSS feed fetch

    # SEMANTIC NOTE: we use 'disabled' (and not 'enabled') because the rss
    # refreshing is something that is enabled in normal conditions. Stopping
    # it is an unusual / rare action, so the setting is named accordingly.
    'FETCH_DISABLED': (False, ugettext(u'Set this to True for maintenance '
                       u'operations and wait for all fetchers to terminate. '
                       u'It should take at most FETCH_DEFAULT_INTERVAL '
                       u'seconds.')),

    'FETCH_DEFAULT_INTERVAL': (3600, ugettext(u'Default feed fetch interval '
                               u'in seconds. You can tune the interval for '
                               u'each feed after creation.')),

    # ••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Article parsing


    'ARTICLE_PARSING_DISABLED': (False, ugettext(u'Set this to True to '
                                 u'suspend content parsing operations. '
                                 u'Related tasks will remain in queue and '
                                 u'will be retried when you enable it again.')),

    'ARTICLE_FULL_PARSING_DISABLED': (False, ugettext(u'Like '
                                      u'ARTICLE_PARSING_DISABLED, but for '
                                      u'FULL content parsing.')),


    # •••••••••••••••••••••••••••••••••••••••••••••••••••• Google Reader Import

    # GR_LOAD_LIMIT * GR_WAVE_LIMIT must equals GR_MAX_ARTICLES:
    # In the worst case, a user could have only one feed containing all its
    # articles. In this case, if WAVE_LIMIT is too low, the import tasks will
    # stop because of waves exhaustion, but the global import will never stop
    # because neither GR_MAX_ARTICLES nor total_starred nor total_reads would
    # have been reached.
    'GR_MAX_ARTICLES': (25 if DEBUG else 500000, ugettext(u'maximum number '
                        u'of Google Reader articles imported for a user. '
                        u'WARNING: GR_LOAD_LIMIT * GR_WAVE_LIMIT must equals '
                        u'GR_MAX_ARTICLES, else you risk never-ending '
                        u'imports in some rare cases.')),

    'GR_MAX_FEEDS': (2 if DEBUG else 1000, ugettext(u'maximum number of '
                     u'articles imported from Google Reader for any user.')),

    'GR_LOAD_LIMIT': (10 if DEBUG else 500, ugettext(u'maximum number of '
                      u'articles in each wave of Google Reader feed import. '
                      u'WARNING: stop all imports before raising this, or '
                      u'some data will be missed by running tasks. No such '
                      u'problem if your lower it.')),

    'GR_WAVE_LIMIT': (10 if DEBUG else 1000, ugettext(u'maximum number of '
                      u'import waves for each Google Reader feed.')),

    'GR_IMPORT_ALLOWED': (True, ugettext(u'Are users allowed to import from '
                          u'Google Reader? Set to False if we reach limits '
                          u'too quickly.')),

    'GR_MAX_RETRIES': (5, ugettext(u'How many retries to attempt if a '
                       u'Google Reader Operation fails.')),

    # No need (constance handles dates correctly), but just in case:
    # time.mktime(datetime.date(2013,07,01).timetuple())
    'GR_END_DATE': (datetime.date(2013, 07, 01),
                    ugettext(u'Google Reader official end date')),

    # NOTE about GR_STORAGE_LIMIT:
    # It's about the physical storage limit on duncan.licorn.org. On my
    # development machine, 260K articles = 1.7Gb only of storage reported in
    # MongoHub, but 6.5Gb really occupied on disk. Duncan's maximum storage
    # availability is ~650Gb, which leads us to a neat 27000000 articles.
    'GR_STORAGE_LIMIT': (100000 if DEBUG else 27000000, ugettext(u'Maximum '
                         u'number of articles in database, after which the '
                         u'Google Reader imports will be disabled.')),

}
