#
# Put production machines hostnames here.
#

# ADMINS += (('Matthieu Chaignot', 'mc@1flow.net'), )

if SITE_ID == 1:
    ALLOWED_HOSTS += [
        '1flowapp.com',
        'www.1flowapp.com',
    ]

else:
    ALLOWED_HOSTS += [
        '1flow.net',
        'www.1flow.net',
        'app.1flow.net',
        'api.1flow.net',
    ]
