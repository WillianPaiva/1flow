# -*- coding: utf-8 -*-

import csv
from django.conf import settings
from django.http import HttpResponse
from django.template.defaultfilters import slugify
from django.contrib import admin
#from django.contrib.sites.models import Site
from django.contrib.admin.util import flatten_fieldsets
from django.utils.translation import ugettext_lazy as _

from .models import EmailContent

from sparks.django.admin import truncate_field


# •••••••••••••••••••••••••••••••••••••••••••••••• Helpers and abstract classes


class NearlyReadOnlyAdmin(admin.ModelAdmin):
    """ borrowed from https://code.djangoproject.com/ticket/17295
        with enhancements from http://stackoverflow.com/a/12923739/654755 """

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return self.readonly_fields

        if self.declared_fieldsets:
            fields = flatten_fieldsets(self.declared_fieldsets)
        else:
            fields = [field.name for field in self.model._meta.fields]
        return fields

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class CSVAdminMixin(admin.ModelAdmin):
    """
    Adds a CSV export action to an admin view.
    cf. http://djangosnippets.org/snippets/2908/
    """

    # This is the maximum number of records that will be written.
    # Exporting massive numbers of records should be done asynchronously.
    csv_record_limit = 10000
    extra_csv_fields = ()

    def get_actions(self, request):
        actions = self.actions if hasattr(self, 'actions') else []

        if request.user.is_superuser:
            actions.append('csv_export')

        actions = super(CSVAdminMixin, self).get_actions(request)
        return actions

    def get_extra_csv_fields(self, request):
        return self.extra_csv_fields

    def csv_export(self, request, qs=None, *args, **kwargs):
        response = HttpResponse(mimetype='text/csv')

        response['Content-Disposition'] = "attachment; filename={}.csv".format(
            slugify(self.model.__name__)
        )

        headers = list(self.list_display) + list(
            self.get_extra_csv_fields(request)
        )

        # BOM (Excel needs it to open UTF-8 file properly)
        response.write(u'\ufeff'.encode('utf8'))
        writer = csv.DictWriter(response, headers)

        # Write header.
        header_data = {}
        for name in headers:
            if hasattr(self, name) \
                    and hasattr(getattr(self, name), 'short_description'):
                header_data[name] = getattr(
                    getattr(self, name), 'short_description')

            else:
                field = self.model._meta.get_field_by_name(name)

                if field and field[0].verbose_name:
                    header_data[name] = field[0].verbose_name

                else:
                    header_data[name] = name

            header_data[name] = header_data[name].encode('utf-8', 'ignore')

        writer.writerow(header_data)

        # Write records.
        for row in qs[:self.csv_record_limit]:
            data = {}
            for name in headers:
                if hasattr(row, name):
                    data[name] = getattr(row, name)
                elif hasattr(self, name):
                    data[name] = getattr(self, name)(row)
                else:
                    raise Exception('Unknown field: %s' % (name,))

                if callable(data[name]):
                    data[name] = data[name]()

                if isinstance(data[name], unicode):
                    data[name] = data[name].encode('utf-8', 'ignore')
                else:
                    data[name] = unicode(data[name]).encode('utf-8', 'ignore')

            writer.writerow(data)

        return response

    csv_export.short_description = _(
        u'Export selected %(verbose_name_plural)s to CSV'
    )


# ••••••••••••••••••••••••••••••••••••••••••••••• Base Django App admin classes

if settings.FULL_ADMIN:

    LANGS = settings.TRANSMETA_LANGUAGES \
        if hasattr(settings, 'TRANSMETA_LANGUAGES') \
        else settings.LANGUAGES

    subject_fields_names = tuple(('subject_' + code)
                                 for code, lang in LANGS)
    subject_fields_displays = tuple((field + '_display')
                                    for field in subject_fields_names)

    class EmailContentAdmin(admin.ModelAdmin):
        list_display  = ('name', ) + subject_fields_displays
        search_fields = ('name', ) + subject_fields_names
        ordering      = ('name', )
        save_as       = True

    for attr, attr_name in zip(subject_fields_names,
                               subject_fields_displays):
        setattr(EmailContentAdmin, attr_name,
                truncate_field(EmailContent, attr))

    admin.site.register(EmailContent, EmailContentAdmin)
