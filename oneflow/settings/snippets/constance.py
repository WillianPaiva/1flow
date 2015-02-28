# -*- coding: utf-8 -*-
#
# Default constance keys, and their values.
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

import datetime

ugettext = lambda s: s

# CONSTANCE_REDIS_CONNECTION is to be found in 'snippets/databases*'
CONSTANCE_BACKEND      = 'constance.backends.redisd.RedisBackend'
CONSTANCE_REDIS_PREFIX = 'c0s1f:'

# This setting is available only in our own constance fork.
CONSTANCE_CHANGE_LIST_TEMPLATE = u'admin/constance_change_list.html'

# SEMANTIC NOTE: we use '_DISABLED' (and not 'enabled') because everything
# should be enabled in normal conditions, unless specified otherwise. Stopping
# things is an unusual / rare action, so the setting is named accordingly.

#    /!\    HEADS UP: don't forget to update
#    /!\              oneflow/base/admin.py::ConstanceAdmin.fieldsets
#    /!\              to get the new values sorted in the admin.

CONSTANCE_CONFIG = {

    # ————————————————————————————————————————————————————————————— Staff stuff

    'PROCESSING_FINE_GRAINED_TRANSACTIONS': (
        False, ugettext(u'Use transactions at all levels of processing chains.'
                        u'Activating this could allow processors to get '
                        u'farther during items processing. Beware that '
                        u'enabling this could hammer your database with a '
                        u'huge lot of transactions. Disabled by default.')),

    'STAFF_HAS_FULL_ACCESS': (False, ugettext(u'Allow staff to have full '
                              u'access to anything. We use this mostly for '
                              u'debugging purposes, but this can be dangerous '
                              u'and liberticide in some conditions. NOTE: '
                              u'disabling this does not prevent any malicious '
                              u'code which bypasses this configuration flag.')),

    '404_USES_NOTFOUND_ORG': (
        False, ugettext(
            u'Display the lost children photos from http://notfound.org/ '
            u'on the 404 page.')),

    # ————————————————————————————————————————————————————————— Plain documents

    'DOCUMENTS_ARCHIVING_DISABLED': (False, ugettext(u'Set this to True to '
                            u'disable maintenance archiving operations. '
                            u'Useful for archive database migrations (BUT '
                            u'NOT SUFFICIENT, because of `original_data` that '
                            u'must be disabled too, via `*_FETCH_DISABLED`).')),
}

# ————————————————————————————————————————————————————————————— Interface stuff

CONSTANCE_CONFIG.update({

    'INTERFACE_SHOW_EXPORT_IDS': (False, ugettext(u'Show IDs everywhere for '
                                  u'easy export links creation.')),
})

# ———————————————————————————————————————————————————————— System announcements

CONSTANCE_CONFIG.update({

    'ANNOUNCEMENT_USER': (u'', ugettext(u'Announcement for all users. '
                          u'Markdown accepted. Leave empty for none.')),

    'ANNOUNCEMENT_USER_PREFIX': (ugettext('*Announcement:* '),
                                 ugettext(u'User announcement '
                                 u'prefix. Set to whatever you want. '
                                 u'Markdown accepted.')),

    'ANNOUNCEMENT_USER_PRIORITY': (u'', ugettext(u'User announcement '
                                   u'priority. Accepted values: info, '
                                   u'success, error or nothing at all.')),

    'ANNOUNCEMENT_USER_START': (datetime.date(1970, 01, 01),
                                ugettext(u'User announcement start '
                                u'date. Leave in the past for immediate '
                                u'display.')),

    'ANNOUNCEMENT_USER_END': (datetime.date(2099, 12, 31),
                              ugettext(u'User announcement end '
                              u'date. Leave in the far future for endless '
                              u'display.')),

    'ANNOUNCEMENT_STAFF': (u'', ugettext(u'Announcement for staff members '
                           u'only. Markdown accepted. Leave empty for none.')),

    'ANNOUNCEMENT_STAFF_PREFIX': (ugettext('*STAFF:* '),
                                 ugettext(u'Staff announcement '
                                 u'prefix. Set to whatever you want. '
                                 u'Markdown accepted.')),

    'ANNOUNCEMENT_STAFF_PRIORITY': (u'', ugettext(u'Staff announcement '
                                   u'priority. Accepted values: info, '
                                   u'success, error or nothing at all.')),

    'ANNOUNCEMENT_STAFF_START': (datetime.date(1970, 01, 01),
                                 ugettext(u'Staff announcement start '
                                 u'date. Leave in the past for immediate '
                                 u'display.')),

    'ANNOUNCEMENT_STAFF_END': (datetime.date(2099, 12, 31),
                               ugettext(u'Staff announcement end '
                               u'date. Leave in the far future for endless '
                               u'display.')),
})

# ——————————————————————————————————————————————————————————— Site theme & CDNs

CONSTANCE_CONFIG.update({

    'WEB_CDNS_ENABLED': (False, ugettext(u'Enable This to use public CDNs for '
                         u'common JS and CSS (jQuery, bootstrap...). Disabled '
                         u'by default to avoid tracking and allow autonomous '
                         u'run.')),

    'WEB_BOOTSWATCH_THEME': (u'', ugettext(u'Choose your bootswatch '
                             u'theme here. If you have CDNs enabled, you '
                             u'must choose a public theme. Default: no '
                             u'bootswatch theme, meaning that 1flow uses its '
                             u'original detail-admin. Possible values include '
                             u'"flatly", "yeti", and all other bootswatch '
                             u'themes, including your own if you deactivate '
                             u'the CDN utilization.')),

    'WEB_THEME_NAVBAR_INVERSE': (True, ugettext(u'Does the bootstrap navbar '
                                 u'uses inverse colors. Default: true, for '
                                 u'detail-admin theme.')),
})

# ———————————————————————————————————————————————————————————————— User support
# HEADS UP: the 3 next are translatable, to allow providing
#           different addresses for multi-language support.

CONSTANCE_CONFIG.update({

    'SUPPORT_EMAIL_ADDRESS': (ugettext(u'supportREMOVETHIS@1flow.io'),
                              ugettext(u'Support email address. Set empty '
                                       u'to disable displaying it in the '
                                       u'support text message.')),

    'IRC_SUPPORT_CHANNEL': (ugettext(u'#1flow'), ugettext(u'Support IRC '
                            u'channel. Set empty to disable displaying it '
                            u'in the support text message.')),

    'IRC_SUPPORT_SERVER': (ugettext(u'irc.freenode.net'),
                            ugettext(u'Support IRC server.')),
})

# ——————————————————————————————————————————————————————— Logins & registration

CONSTANCE_CONFIG.update({

    'SOCIAL_LOGIN_ENABLED': (True, ugettext(u'Already known users are allowed '
                             u'to sign in via social network accounts. '
                             u'Default: True. See SOCIAL_REGISTRATION_ENABLED '
                             u'for new accounts.')),

    'SOCIAL_REGISTRATION_ENABLED': (True, ugettext(u'New users are allowed to '
                                    u'auto-register accounts via social '
                                    u'networks signins. Default: False.')),

    'LOCAL_LOGIN_ENABLED': (True, ugettext(u'Already known users are allowed '
                            u'to sign in via local accounts. Default: True. '
                            u'You can disable this to allow only social '
                            u'signins.')),

    'LOCAL_REGISTRATION_ENABLED': (True, ugettext(u'New users are allowed to '
                                    u'register local accounts. Default: '
                                    u'False. NOTE2: the underlying code does '
                                    u'not currently use this dynamic '
                                    u'configuration. We have to contribute a '
                                    u'patch, but the configuration directive '
                                    u'exists, at least.')),
})

# ——————————————————————————————————————————————————————————————— Reading lists

CONSTANCE_CONFIG.update({


    'READ_INFINITE_AUTOSCROLL_ENABLED': (True, ugettext(u'Make the read view '
                                         u'(either list or tiles) '
                                         u'automatically load new content '
                                         u'when reaching end of page.')),

    'READ_INFINITE_ITEMS_PER_FETCH': (ENDLESS_PAGINATION_PER_PAGE,
                                      ugettext(u'Number of items per ajax '
                                      u'fetch on infinite pagination pages.')),

    'READ_ARTICLE_MIN_LENGTH': (24, ugettext(u'Minimum length of an article '
                                u'content. Set to 0 to always display '
                                u'Markdown content to users, whatever it is.')),

    # Cf. http://mindbluff.com/askread.htm
    'READ_AVERAGE_READING_SPEED': (200, ugettext(u'The average number of '
                                   u'words per minutes that an adult can '
                                   u'read. When the user has not configured '
                                   u'his/her own, this one will be used.')),
})

# ——————————————————————————————————————————————————————————————— Subscriptions

CONSTANCE_CONFIG.update({


    'SUBSCRIPTIONS_ITEMS_UNREAD_DAYS': (2, ugettext(u'When a user '
                                           u'subscribes to a feed, how many '
                                           u'days from now are marked unread? '
                                           u'(the remaining history is still '
                                           u'available but marked auto_read).')
                                           ),

})

# ————————————————————————————————————————————————————————— RSS feed refreshing

CONSTANCE_CONFIG.update({

    'FEED_FETCH_DISABLED': (False, ugettext(u'Set this to True on '
                            u'maintenance operations. After setting, wait '
                            u'for all fetchers to terminate. It should take at '
                            u'most FEED_FETCH_DEFAULT_INTERVAL seconds.')),

    'FEED_FETCH_RSSATOM_DISABLED': (False, ugettext(u'Disable all RSS/Atom '
                                    u'feed operations.')),

    'FEED_FETCH_EMAIL_DISABLED': (False, ugettext(u'Disable all email '
                                    u'feed operations.')),

    'FEED_FETCH_TWITTER_DISABLED': (False, ugettext(u'Disable all email '
                                    u'feed operations.')),

    'FEED_FETCH_FACEBOOK_DISABLED': (False, ugettext(u'Disable all email '
                                    u'feed operations.')),

    'FEED_FETCH_GOOGLE_DISABLED': (False, ugettext(u'Disable all email '
                                    u'feed operations.')),

    'FEED_FETCH_GHOST_ENABLED': (False, ugettext(u'Enable Ghost fetching or '
                                 u'not. Disabled by default, make OSX Python '
                                 u'crash.')),

    'FEED_FETCH_MAX_ERRORS': (90, ugettext(u'The maximum number of errors '
                              u'a feed can meet before beiing automatically '
                              u'closed.')),

    'FEED_GLOBAL_REFRESH_INTERVAL': (2, ugettext(u'Interval for the '
                                     u'refresh_all_feeds() global task. '
                                    u'expressed in minutes. Celery beat '
                                    u'launches the task every minute. Tuning '
                                    u'this value allows dynamic adaptation.')),

    'FEED_FETCH_DEFAULT_INTERVAL': (43200, ugettext(u'Default feed fetch '
                                    u'interval in seconds. You can tune the '
                                    u'interval for each feed after creation.')),

    'FEED_FETCH_MIN_INTERVAL': (300, ugettext(u'The minimum interval between '
                                u'fetches of the same feed. Warning: anything '
                                u'under 60 will not be taken in account.')),

    'FEED_FETCH_MAX_INTERVAL': (259200, ugettext(u'The maximum interval between '
                                u'fetches of the same feed. Warning: anything '
                                u'more than 7 days (expressed in seconds) will '
                                u'not be taken in account.')),

    'FEED_FETCH_RAISE_THRESHOLD': (10, ugettext(u'If this feed produces more '
                                   u'new articles than this number, it will '
                                   u'be fetched more fast than a feed that '
                                   u'produces less. Minimum value: 5.')),

    'FEED_FETCH_PARALLEL_LIMIT': (16, ugettext(u'Default number of articles '
                                  u'fetchable from the same feed at the same '
                                  u'time. Workers should adjust the value '
                                  u'automatically as time passes.')),

    'FEED_ADMIN_LIST_PER_PAGE': (100, ugettext(u'How many feeds per page in '
                                 u'the Django admin. Increase only if '
                                 u'performance is acceptable; do NOT abuse!')),

    'FEED_ADMIN_MEANINGFUL_DELTA': (6 * 365 / 12, ugettext(u'We see how many '
                                    u'articles feeds have produced during this '
                                    u'delta (in days), to see if we can close '
                                    u'them or not (if they got 0 new '
                                    u'articles).')),

    'FEED_CLOSED_WARN_LIMIT': (5, ugettext(u'Number of days during which a '
                               u'just closed feed will be warned about to '
                               u'site managers via mail.')),
})

# —————————————————————————————————————————————————— Article fetching & parsing

CONSTANCE_CONFIG.update({

    # TODO: mark obsolete / disable with processors architecture ?
    # Every processing category can be individually disabled, and with
    # cacheops its equivalent to a constance config.

    'ARTICLE_REPROCESSING_DISABLED': (False, ugettext(u'Disable or not '
                                  u'the reprocessing operations that could '
                                  u'repair failed articles. Default: '
                                  u'enabled in normal conditions.')),

    'ARTICLE_ABSOLUTIZING_DISABLED': (False, ugettext(u'Disable or not the '
                                      u'article URL absolutization. Default: '
                                      u'enabled in normal conditions (and '
                                      u'without it we will have a lot of '
                                      u'duplicate content that will need '
                                      u'post-processing).')),

    'ARTICLE_FETCHING_DEBUG': (False, ugettext(u'Enable this to log '
                               u'intermediate article versions. Default: '
                                  u'not enabled in normal conditions. Kept '
                                  u'for mongodb code.')),

    'ARTICLE_FETCHING_DISABLED': (False, ugettext(u'Disable or not '
                                  u'global fetching operations for all '
                                  u'content types. Default: '
                                  u'enabled in normal conditions. Kept '
                                  u'for mongodb code.')),

    'ARTICLE_FETCHING_TEXT_DISABLED': (False, ugettext(u'Disable or not '
                                       u'text fetching operations. Default: '
                                       u'enabled in normal conditions.')),

    'ARTICLE_FETCHING_VIDEO_DISABLED': (False, ugettext(u'Disable or not '
                                        u'video fetching operations. Default: '
                                        u'enabled in normal conditions.')),

    'ARTICLE_FETCHING_IMAGE_DISABLED': (False, ugettext(u'Disable or not '
                                        u'image fetching operations. Default: '
                                        u'enabled in normal conditions.')),

    'ARTICLE_MARKDOWN_DISABLED': (False, ugettext(u'Disable or not the HTML '
                                  u'to Markdown internal conversion. '
                                  u'Default: enabled in normal conditions.')),



    'ARTICLE_ARCHIVE_BATCH_SIZE': (100 if DEBUG else 50000,
                                   ugettext(u'how much articles will be '
                                   u'archived at each archive task run.')),

    'ARTICLE_ARCHIVE_OLDER_THAN': (62, ugettext(u'Only articles older than '
                                   u'that will be archived, regarding their '
                                   u'`date_published` field. This delta is '
                                   u'expressed in days. Set to 0 to archive '
                                   u'everything without mercy.')),

    'EXCERPT_PARAGRAPH_MIN_LENGTH': (64, ugettext(u'Number of characters '
                                     u'below which a paragraph does not '
                                     u'have enough data (words) to be '
                                     u'considered informational.')),
})

# ——————————————————————————————————————————————————————————— Accounts (global)

CONSTANCE_CONFIG.update({

    'ACCOUNT_REFRESH_DISABLED': (False, ugettext(u'Disable or not the '
                                      u'periodic check of all unusable '
                                      u'accounts (any type).')),


    'ACCOUNT_REFRESH_PERIOD_DEFAULT': (3600*1, ugettext(u'Default period '
                                       u'after which accounts will be '
                                       u'tested again for connection and '
                                       u'listing.')),

})

# ———————————————————————————————————————————————————————————— Twitter accounts

CONSTANCE_CONFIG.update({

    'TWITTER_ACCOUNT_REFRESH_DISABLED': (False, ugettext(u'Disable or not the '
                                      u'periodic check of unusable Twitter '
                                      u'accounts.')),

    'TWITTER_ACCOUNT_REFRESH_PERIOD': (3600*1, ugettext(u'Default period '
                                       u'after which Twitter accounts will be '
                                       u'tested again for connection and '
                                       u'listing.')),

    'TWITTER_FEEDS_RELAUNCH_INTERVAL': (
        48,
        ugettext(u'Average idle period between 2 refreshes of the same '
                 u'twitter feed. Minimum value: 12, because of Twitter\'s '
                 u'180 API calls / 15 min.')),


    'TWITTER_ACCOUNT_FETCH_OWNED_LISTS': (
        True,
        ugettext(u'Enable or disable to set the default value for '
                 u'auto-following and fetching the lists owned by a '
                 u'Twitter account. WARNING: this could be quite '
                 u'expensive, depending the global number of twitter '
                 u'accounts of your 1flow node.')),

    'TWITTER_ACCOUNT_FETCH_SUBSCRIBED_LISTS': (
        True,
        ugettext(u'Enable or disable to set the default value for '
                 u'auto-following and fetching the lists a Twitter account '
                 u'is subscribed to. NOTE: if '
                 u'TWITTER_ACCOUNT_FETCH_OWNED_LISTS is disabled, only the '
                 u'lists not owned by the user will be followed. WARNING: '
                 u'this could be quite expensive, depending the global '
                 u'number of twitter accounts of your 1flow node.')),

    'TWITTER_FEEDS_BACKFILL_ENABLED_DEFAULT': (
        False,
        ugettext(u'Enable or disable twitter-based feeds to be backfilled '
                 u'upon creation. WARNING: this could be quite expensive, '
                 u'depending the global number of twitter accounts of your '
                 u'1flow node, and their creation date. You could also '
                 u'exhaust your API rate quickly.')),

    'TWITTER_BACKFILL_ALLOWED_REWIND_RANGE': (
        5,
        ugettext(u'Specify the maximum backfill allowed on twitter feeds, '
                 u'expressed in weeks, as an integer. If you you want to '
                 u'backfill until the creation of Twitter, set it to zero '
                 u'(0), and prepare to see your machine work a lot, and '
                 u'exhaust all its Twitter quotas.')),

    'TWITTER_DEFAULT_CACHE_EXPIRY': (
        3600 * 24 * 2,
        ugettext(u'Make twitter cached objects expire after this amount of '
                 u' seconds. Concerns all twitter objects that have no '
                 u'dedicated cache settings.')),


    'TWITTER_LISTS_CACHE_EXPIRY': (
        3600 * 24 * 7,
        ugettext(u'Make cached lists expire after this amount of seconds. '
                 u'Set to 0 to use default cache expiry delay.')),


})

# ——————————————————————————————————————————————————————————————— Mail accounts

CONSTANCE_CONFIG.update({

    'MAIL_ACCOUNT_REFRESH_DISABLED': (False, ugettext(u'Disable or not the '
                                      u'periodic check of all unusable mail '
                                      u'accounts.')),


    'MAIL_ACCOUNT_REFRESH_PERIOD': (3600*6, ugettext(u'Period after which '
                                    u'IMAP accounts will be tested again '
                                    u'for connection and mailbox listing.')),


    'MAIL_IMAP_FETCH_MAX': (25, ugettext(u'When fetching e-mails from IMAP '
                            u'accounts, how many should be downloaded at '
                            u'each call.')),


    'MAIL_IMAP_CACHE_MESSAGES': (True, ugettext(u'Cache all downloaded '
                                 u'e-mails in Redis to speed up further '
                                 u'fetches and mail feeds refreshes.')),


    'MAIL_IMAP_CACHE_EXPIRY': (3600*24, ugettext(u'Make cached e-mails '
                               u'expire after this amount of seconds.')),

    'MAIL_IMAP_CACHE_IDS_EXPIRY': (3600*4, ugettext(u'Make cached e-mails '
                                   u'IDs after this amount of seconds.')),

    'MAIL_IMAP_DECODE_FALLBACK': (u'iso8859-15, iso8859-1', ugettext(u'a list '
                                  u'of comma separated encodings to try when '
                                  u'email headers cannot be decoded. “utf-8” '
                                  u'is always added to the list, and tried '
                                  u'first.')),

    'MAIL_RULES_GROUPS_MAX': (25, ugettext(u'When fetching e-mails from IMAP '
                            u'accounts, how many should be downloaded at '
                            u'each call.')),
})

# ————————————————————————————————————————————————————————————————— Check tasks

CONSTANCE_CONFIG.update({

    'CHECK_DATABASE_MIGRATION_DISABLED': (
        False, ugettext(u'Disable or not the global database migration '
                        u'/ synchronization task.')),

    'CHECK_DATABASE_MIGRATION_DEFINIVE_RUN': (
        False, ugettext(u'Enable it to mark items migrated and avoid '
                        u're-migrate them on next migration run.')),

    'CHECK_DATABASE_MIGRATION_VACUUM_ENABLED': (
        True, ugettext(u'Disable to avoid regular VACUUM ANALYZE runs '
                       u'during the migration.')),

    'CHECK_SUBSCRIPTIONS_DISABLED': (False, ugettext(u'Disable or not the '
                                     u'night subscription check that will '
                                     u'check_reads() all subscriptions that '
                                     u'do not have the same number of '
                                     u'articles than the feed they belong '
                                     u'to. Default: enabled.')),

    'CHECK_DUPLICATES_DISABLED': (False, ugettext(u'Disable or not the '
                                  u'night duplicates check that will '
                                  u'ensure all duplicate articles have '
                                  u'no read left in the system. Default: '
                                  u'let it run (=enabled).')),

    'CHECK_DUPLICATES_PURGE_AFTER_WEEKS': (
        10, ugettext(u'Remove duplicates items after this period of time, '
                     u'expressed in weeks. Accepted interval between 1 and '
                     u'52. Purging too recent items will raise global '
                     u' workers / database / network load; not purging '
                     u'them enough will cause spikes in workers load and '
                     u'periods during which no new item is created. This '
                     u'is a tradeoff to choose, depending on your duplicates '
                     u'number, and thus on what your server fetches.')),

    'CHECK_ORPHANED_DISABLED': (False, ugettext(u'Disable or not the '
                                  u'night orphaned check that will '
                                  u'ensure all orphaned articles are '
                                  u'as unique as possible across the '
                                  u'system. Default: let it run (=enabled).')),

    'CHECK_READS_DISABLED': (False, ugettext(u'Disable or not the night '
                             u'reads check that will switch on-and-off their '
                             u'`is_good` attribute. Default: let it run '
                             u'(=enabled).')),

    'CHECK_USERS_DISABLED': (False, ugettext(u'Disable or not the night '
                             u'users check. Default: let it run (=enabled).')),
})

# ———————————————————————————————————————————————————————————————— Next section

# CONSTANCE_CONFIG.update({
#
# })

# ———————————————————————————————————————————————————————— Google Reader Import
#                                              (OBSOLETE but kept for memories)

CONSTANCE_CONFIG.update({

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

    # WARNING: keep this a date(), which is neither naive nor TZ aware.
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
})
