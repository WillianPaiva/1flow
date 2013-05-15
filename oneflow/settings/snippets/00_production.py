
import warnings

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    import django.conf.urls.defaults # NOQA

DEBUG = False
TEMPLATE_DEBUG = DEBUG

# Do we show all 1flow AdminModels in admin ?
# Not by default, cf. https://trello.com/c/dJoV4xZy
FULL_ADMIN = False
