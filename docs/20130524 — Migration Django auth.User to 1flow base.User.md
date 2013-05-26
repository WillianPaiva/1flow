
## Migration from Django user schema to 1flow user schema

    fab prod sdf.getdata:auth.User
    fab prod sdf.getdata:profiles

    # edit auth.User > remove 'username'

    reset profiles
    reset auth

    syncdb
    # should re-create admin

    fab prod sdf.putdata:auth.User
    fab prod sdf.putdata:profiles
