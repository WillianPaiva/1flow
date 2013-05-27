
## Migration from Django user schema to 1flow user schema

    fab prod sdf.getdata:profiles

    fab prod sdf.getdata:auth.User
    # edit auth.User > remove 'username'

    # should re-create admin
    fab prod sdf.syncdb

    fab prod command:'./manage.py reset profiles --noinput'

    # Why? see http://stackoverflow.com/a/16071185/654755
    fab prod command:'./manage.py reset auth --noinput'

    # We need to reset logentry.
    fab prod command:'./manage.py reset admin --noinput'

    fab prod sdf.putdata
        # modified auth.User
    fab prod sdf.putdata
        # profiles

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
