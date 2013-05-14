# -*- coding: utf-8 -*-

from django.contrib import admin
from django.conf import settings
from .models import LandingContent
from sparks.django.admin import truncate_field

content_fields_names = tuple(('content_' + code)
                             for code, lang
                             in settings.LANGUAGES)
content_fields_displays = tuple((field + '_display')
                                for field in content_fields_names)


class LandingContentAdmin(admin.ModelAdmin):
    list_display  = ('name', ) + content_fields_displays
    search_fields = ('name', ) + content_fields_names
    ordering      = ('name', )


for attr, attr_name in zip(content_fields_names,
                           content_fields_displays):
    setattr(LandingContentAdmin, attr_name,
            truncate_field(LandingContent, attr))


admin.site.register(LandingContent, LandingContentAdmin)
