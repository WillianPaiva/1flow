#
# Put production machines hostnames here.
#

# ADMINS += (('Matthieu Chaignot', 'mc@1flow.net'), )

if SITE_ID == 1:
    ALLOWED_HOSTS += [
        '1flow.io',
        'app.1flow.io',
        'api.1flow.io',
    ]

else:
    ALLOWED_HOSTS += [
        '1flow.net',
        'app.1flow.net',
        'api.1flow.net',
    ]
