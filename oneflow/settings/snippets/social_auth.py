# -*- coding: utf-8 -*-
# See snippets/api_keys_*.py for API keys.
""" Oh My, that's social-auth settings. """

from django.core.urlresolvers import reverse_lazy

# NO NEED, social-auth will use “USER_MODEL” from Django
# SOCIAL_AUTH_USER_MODEL = 'base.User'

SOCIAL_AUTH_ADMIN_USER_SEARCH_FIELDS = ['username', 'first_name',
                                        'last_name', 'email']

# http://psa.matiasaguirre.net/docs/configuration/settings.html#settings-name
# http://psa.matiasaguirre.net/docs/configuration/settings.html#urls-options
LOGIN_URL          = reverse_lazy('signin')
LOGOUT_URL         = reverse_lazy('signout')
LOGIN_REDIRECT_URL = reverse_lazy('home')
LOGIN_ERROR_URL    = reverse_lazy('signin_error')
# SOCIAL_AUTH_BACKEND_ERROR_URL = reverse_lazy('signin_error')

# SOCIAL_AUTH_PROTECTED_USER_FIELDS = ['email', ]
SOCIAL_AUTH_FORCE_POST_DISCONNECT = True
SOCIAL_AUTH_EXTRA_DATA = True
SOCIAL_AUTH_SESSION_EXPIRATION = False

# Doesn't help #444
# SOCIAL_AUTH_AUTHENTICATION_BACKENDS = AUTHENTICATION_BACKENDS  # NOQA
# SOCIAL_AUTH_SANITIZE_REDIRECTS = False
# FACEBOOK_AUTH_EXTRA_ARGUMENTS = {'display': 'touch'}
# SOCIAL_AUTH_REDIRECT_IS_HTTPS = False
# SOCIAL_AUTH_<BACKEND_NAME>_WHITELISTED_DOMAINS = ['foo.com', 'bar.com']
# SOCIAL_AUTH_RAISE_EXCEPTIONS = True

# ———————————————————————————————————————————————————————————————————— PIPELINE

SOCIAL_AUTH_PIPELINE_BLAHBLAH = (

    # Get the information we can about the user and return it in a simple
    # format to create the user instance later. On some cases the details are
    # already part of the auth response from the provider, but sometimes this
    # could hit a provider API.
    'social.pipeline.social_auth.social_details',

    # Get the social uid from whichever service we're authing thru. The uid is
    # the unique identifier of the given user in the provider.
    'social.pipeline.social_auth.social_uid',

    # Verifies that the current auth process is valid within the current
    # project, this is were emails and domains whitelists are applied (if
    # defined).
    'social.pipeline.social_auth.auth_allowed',

    # Checks if the current social-account is already associated in the site.
    'social.pipeline.social_auth.social_user',

    # Make up a username for this person, appends a random string at the end if
    # there's any collision.
    'social.pipeline.user.get_username',

    # Send a validation email to the user to verify its email address.
    # Disabled by default.
    # 'social.pipeline.mail.mail_validation',

    # Associates the current social details with another user account with
    # a similar email address. Disabled by default.
    'social.pipeline.social_auth.associate_by_email',

    # Create a user account if we haven't found one yet.
    'social.pipeline.user.create_user',

    # Create the record that associated the social account with this user.
    'social.pipeline.social_auth.associate_user',

    # Populate the extra_data field in the social record with the values
    # specified by settings (and the default ones like access_token, etc).
    'social.pipeline.social_auth.load_extra_data',

    # Update the user record with any changed info from the auth service.
    'social.pipeline.user.user_details',

    # Get an avatar from the backend, if
    # user hasn't set one in his/her profile.
    'oneflow.base.social_pipeline.get_social_avatar',

    # Check & pre-populate accounts & feeds from the backend.
    'oneflow.core.social_pipeline.check_feeds',

    # Given the configuration, we do allow any user to register, or not.
    # In both cases, we create the account, but if registration is disabled
    # this pipeline function will deactivate the account right after creation,
    # to be sure the user doesn't log in.
    'oneflow.base.social_pipeline.throttle_new_user_accounts',
)

# if DEBUG:
#     SOCIAL_AUTH_PIPELINE = (
#         'oneflow.base.social_pipeline.debug',
#     ) + SOCIAL_AUTH_PIPELINE

# import sys
# sys.stdout.write('>>>\n')
# sys.stdout.write('>>> %s\n' % (SOCIAL_AUTH_PIPELINE, ))
# sys.stdout.write('>>>\n')
# sys.stdout.flush()

# —————————————————————————————————————————————————————————————————— EXTRA DATA

GITHUB_EXTRA_DATA = [
    ('created_at', 'date_created'),
    ('avatar_url', 'avatar_url'),
    ('login', 'username'),
    ('name', 'fullname'),
    # 'email': 'john@example.com',
]

TWITTER_EXTRA_DATA = [
    ('created_at', 'date_created'),
    ('profile_image_url', 'avatar_url'),
    ('screen_name', 'username'),
    ('name', 'fullname'),
    ('location', 'location'),

    ('statuses_count', 'statuses_count'),       # Number of tweets I made
    ('friends_count', 'friends_count'),         # Who I follow
    ('followers_count', 'followers_count'),     # Who follows me
    ('favourites_count', 'favourites_count'),
    ('retweets_count', 'retweets_count'),       # ??
    ('retweet_count', 'retweet_count'),         # ??
    ('listed_count', 'listed_count'),

    ('lang', 'language'),
    ('profile_background_image_url', 'profile_background_image_url'),
    ('profile_background_image_url_https',
     'profile_background_image_url_https'),
    ('profile_background_color', 'profile_background_color'),
    ('verified', 'verified'),
    ('geo_enabled', 'geo_enabled'),
    ('time_zone', 'time_zone'),
    ('description', 'description'),
    # ('', ''),
]

# ——————————————————————————————————————————————————————————————— Google Oauth2

# Get the google reader scope.
# from libgreader.auth import OAuth2Method
# GOOGLE_OAUTH_EXTRA_SCOPE = OAuth2Method.SCOPE

# TODO:
# SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE
# We need this to be able to refresh tokens
# See http://stackoverflow.com/a/10857806/654755 for notes.
SOCIAL_AUTH_GOOGLE_OAUTH2_EXTRA_ARGUMENTS = {'access_type': 'offline'}
SOCIAL_AUTH_GOOGLE_OAUTH2_CONTACTS_SCOPE = 'https://www.google.com/m8/feeds'
SOCIAL_AUTH_GOOGLE_OAUTH2_CONTACTS_REDIRECT_URI = \
    reverse_lazy('import_contacts_authorized')


# —————————————————————————————————————————————————————————————————————— SCOPES

SOCIAL_AUTH_FACEBOOK_SCOPE = [
    'email',
    'user_friends',
    'user_birthday',
    'friends_location',
]
