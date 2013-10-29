
import datetime

SITE_ID     = 1
SITE_DOMAIN = '1flow.io'
SITE_NAME   = '1flow'

# WARNING: keep this a date(), which is neither naive nor TZ aware.
LANDING_BETA_DATE = datetime.date(2013, 07, 01)
LANDING_BETA_INVITES = 100

# We now need full access to content editors in production for fast fixes.
# This is not definitive, but will help making content more user-friendly
# without hassling back-and-forth between development and production via CLI.
FULL_ADMIN = True
