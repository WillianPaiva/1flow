# -*- coding: utf-8 -*-

from django.contrib import admin
from django.conf import settings
from .models import LandingContent

TRUNCATE_LENGTH = 50

content_fields_names = tuple(('content_' + code)
                             for code, lang
                             in settings.LANGUAGES)
content_fields_displays = tuple((field + '_display')
                                for field in content_fields_names)


class LandingContentAdmin(admin.ModelAdmin):
    list_display = ('name', ) + content_fields_displays
    #list_display_links = ('name')

    #list_filter = (HasTranslationFilter(lang)
    #               for lang, lang_name in settings.LANGUAGES)
    ordering = ('name',)
    search_fields = ('name', ) + content_fields_names


def truncated(cls, field_name):
    def wrapped(self, obj):
        value = getattr(obj, field_name)
        return value[:TRUNCATE_LENGTH] + (value[TRUNCATE_LENGTH:] and u'…')

    wrapped.short_description = cls._meta.get_field_by_name(
        field_name)[0].verbose_name
    wrapped.admin_order_field = field_name
    return wrapped

for attr, attr_name in zip(content_fields_names,
                           content_fields_displays):
    setattr(LandingContentAdmin, attr_name,
            truncated(LandingContent, attr))


admin.site.register(LandingContent, LandingContentAdmin)
