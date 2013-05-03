# -*- coding: utf-8 -*-

from django.contrib import admin

from .models import LandingContent


class LandingContentAdmin(admin.ModelAdmin):
    pass


admin.site.register(LandingContent, LandingContentAdmin)
