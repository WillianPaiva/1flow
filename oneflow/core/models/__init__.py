# -*- coding: utf-8 -*-

from django.contrib.auth.models import AbstractBaseUser

from .reldb import * # NOQA
from .nonrel import * # NOQA
from .keyval import * # NOQA


class SimpleUser(AbstractBaseUser):
    # No need of username, we have the email…
    #username = models.CharField(max_length=254, unique=True, db_index=True)
    email = models.EmailField(max_length=254, unique=True, db_index=True)
    twitter_handle = models.CharField(max_length=255)
    ...

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['twitter_handle']
