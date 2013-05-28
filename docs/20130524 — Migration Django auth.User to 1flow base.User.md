
## Migration from Django user schema to 1flow user schema

    ENV=test

    fab ${ENV} maint

    fab ${ENV} sdf.getdata:profiles

    fab ${ENV} sdf.getdata:auth.User
    # edit auth.User > remove 'username'

    # should re-create admin
    fab ${ENV} sdf.syncdb

    fab ${ENV} command:'./manage.py reset profiles --noinput'

    # Why? see http://stackoverflow.com/a/16071185/654755
    fab ${ENV} command:'./manage.py reset auth --noinput'

    # We need to reset logentry.
    fab ${ENV} command:'./manage.py reset admin --noinput'

    fab ${ENV} sdf.putdata
        # modified auth.User
    fab ${ENV} sdf.putdata
        # profiles

    # remove duplicate supervisor entries
    restart / clean the supervisor configuration


    fab ${ENV} op

## Form adaptations

cf. https://docs.djangoproject.com/en/1.5/topics/auth/customizing/#custom-users-and-the-built-in-auth-forms


### Need rewrite

- UserCreationForm
- UserChangeForm

### OK or should be OK

- PasswordResetForm: should be OK
- SetPasswordForm: OK
- AuthenticationForm: OK
- PasswordChangeForm: OK
- AdminPasswordChangeForm: OK

## Tests

- sparks create superuser [OK]
- inscription [OK]
    - délai 1 seconde
- ré-inscription [OK]
- admin classique, liste + form [OK]
- admin 1flow, liste + form [OK]
    - change password [OK]
- admin création [OK]

- edit profile
- change password
