# -*- coding: utf-8 -*-

from django.contrib import admin
from django.conf import settings
from .models import LandingContent


class LandingContentAdmin(admin.ModelAdmin):
    list_display = ('name', 'content_en')
    #list_display_links = ('name')

    #list_filter = (HasTranslationFilter(lang)
    #               for lang, lang_name in settings.LANGUAGES)
    ordering = ('name',)
    search_fields = ('name', 'content_en', 'content_fr')


admin.site.register(LandingContent, LandingContentAdmin)
