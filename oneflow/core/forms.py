# -*- coding: utf-8 -*-

import logging

from django import forms
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import get_user_model
from mongodbforms import DocumentForm

from .models import (HomePreferences, ReadPreferences,
                     SelectorPreferences, StaffPreferences)

LOGGER = logging.getLogger(__name__)
User = get_user_model()


class FullUserCreationForm(forms.ModelForm):
    """ Like the django UserCreationForm,
        with optional first_name and last_name,
        and email too.

        .. note:: the ``username`` field from Django's ``UserCreationForm``
            is overriden by our Model's one. Thus the 30 chars limit
            doesn't apply.
    """

    error_messages = {
        'password_mismatch': _("The two password fields didn't match."),
    }

    email = forms.EmailField()
    password1 = forms.CharField(label=_("Password"),
                                widget=forms.PasswordInput)
    password2 = forms.CharField(label=_("Password confirmation"),
                                widget=forms.PasswordInput,
                                help_text=_("Enter the same password as "
                                            "above, for verification."))

    class Meta:
        model  = User
        fields = ['first_name', 'last_name',
                  'username', 'email',
                  'password1', 'password2', ]

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(
                self.error_messages['password_mismatch'])
        return password2

    def save(self, commit=True):
        user = super(FullUserCreationForm, self).save(commit=False)

        user.set_password(self.cleaned_data["password1"])
        user.email      = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name  = self.cleaned_data["last_name"]

        if commit:
            user.save()

        return user


class UserProfileEditForm(forms.ModelForm):

    class Meta:
        model  = User
        fields = ['first_name', 'last_name', ]


class HomePreferencesForm(DocumentForm):

    class Meta:
        model = HomePreferences

        # Other fields are not yet ready
        exclude = ('style', )


class ReadPreferencesForm(DocumentForm):

    class Meta:
        model = ReadPreferences


class SelectorPreferencesForm(DocumentForm):

    class Meta:
        model = SelectorPreferences


class StaffPreferencesForm(DocumentForm):

    class Meta:
        model = StaffPreferences
