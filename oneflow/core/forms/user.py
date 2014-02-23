# -*- coding: utf-8 -*-
"""
    Copyright 2013-2014 Olivier Cortès <oc@1flow.io>

    This file is part of the 1flow project.

    1flow is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of
    the License, or (at your option) any later version.

    1flow is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public
    License along with 1flow.  If not, see http://www.gnu.org/licenses/

"""

import logging

from django import forms

from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import get_user_model

LOGGER = logging.getLogger(__name__)
User   = get_user_model()


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
