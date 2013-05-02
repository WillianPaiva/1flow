# -*- coding: utf-8 -*-

from django import forms
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _


class LandingPageForm(forms.ModelForm):

    class Meta:
        model  = User
        fields = ('email', )

    def clean_email(self):

        email = self.cleaned_data['email']

        if email.strip() == u'':
            raise forms.ValidationError(
                _(u"L'adresse email ne doit pas être vide."))

        return email
