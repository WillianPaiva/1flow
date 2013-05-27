# -*- coding: utf-8 -*-

import csv
from django.db import transaction
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.template.defaultfilters import slugify
from django.shortcuts import get_object_or_404
from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.forms import AdminPasswordChangeForm
from django.template.response import TemplateResponse
from django.contrib.admin.util import flatten_fieldsets
from django.utils.html import escape
from django.utils.translation import ugettext, ugettext_lazy as _
from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.csrf import csrf_protect

from .models import EmailContent, User
from .forms import UserChangeForm, UserCreationForm

from sparks.django.admin import languages, truncate_field

csrf_protect_m = method_decorator(csrf_protect)

try:
    from ..profiles.models import UserProfile
except ImportError:
    UserProfile = None


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


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False


class UserAdmin(admin.ModelAdmin):
    """ This class mimics the standard UserAdmin, as seen in Django 1.5 at:
        https://raw.github.com/django/django/master/django/contrib/auth/admin.py

        We add it in case you would like to include oneflow.base in other apps.
    """

    add_form_template = 'admin/auth/user/add_form.html'
    change_user_password_template = None
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', )}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2')}),
    )
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    list_display = ('email', 'first_name', 'last_name', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('first_name', 'last_name', 'email')
    ordering = ('email',)
    filter_horizontal = ('groups', 'user_permissions', )

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        return super(UserAdmin, self).get_fieldsets(request, obj)

    def get_form(self, request, obj=None, **kwargs):
        """ Use special form during user creation """

        defaults = {}
        if obj is None:
            defaults.update({
                'form': self.add_form,
                'fields': admin.util.flatten_fieldsets(self.add_fieldsets),
            })
        defaults.update(kwargs)
        return super(UserAdmin, self).get_form(request, obj, **defaults)

    def get_urls(self):
        from django.conf.urls import patterns
        return patterns('',
                        (r'^(\d+)/password/$',
                        self.admin_site.admin_view(self.user_change_password))
                        ) + super(UserAdmin, self).get_urls()

    def lookup_allowed(self, lookup, value):
        # See #20078: we don't want to allow any lookups involving passwords.
        if lookup.startswith('password'):
            return False
        return super(UserAdmin, self).lookup_allowed(lookup, value)

    @sensitive_post_parameters()
    @csrf_protect_m
    @transaction.commit_on_success
    def add_view(self, request, form_url='', extra_context=None):
        # It's an error for a user to have add permission but NOT change
        # permission for users. If we allowed such users to add users, they
        # could create superusers, which would mean they would essentially have
        # the permission to change users. To avoid the problem entirely, we
        # disallow users from adding users if they don't have change
        # permission.
        if not self.has_change_permission(request):
            if self.has_add_permission(request) and settings.DEBUG:
                # Raise Http404 in debug mode so that the user gets a helpful
                # error message.
                raise Http404(
                    'Your user does not have the "Change user" permission. In '
                    'order to add users, Django requires that your user '
                    'account have both the "Add user" and "Change user" '
                    'permissions set.')
            raise PermissionDenied
        if extra_context is None:
            extra_context = {}
        username_field = self.model._meta.get_field(self.model.USERNAME_FIELD)
        defaults = {
            'auto_populated_fields': (),
            'username_help_text': username_field.help_text,
        }
        extra_context.update(defaults)
        return super(UserAdmin, self).add_view(request, form_url,
                                               extra_context)

    @sensitive_post_parameters()
    def user_change_password(self, request, id, form_url=''):
        if not self.has_change_permission(request):
            raise PermissionDenied
        user = get_object_or_404(self.queryset(request), pk=id)
        if request.method == 'POST':
            form = self.change_password_form(user, request.POST)
            if form.is_valid():
                form.save()
                msg = ugettext('Password changed successfully.')
                messages.success(request, msg)
                return HttpResponseRedirect('..')
        else:
            form = self.change_password_form(user)

        fieldsets = [(None, {'fields': list(form.base_fields)})]
        adminForm = admin.helpers.AdminForm(form, fieldsets, {})

        context = {
            'title': _('Change password: %s') % escape(user.get_username()),
            'adminForm': adminForm,
            'form_url': form_url,
            'form': form,
            'is_popup': '_popup' in request.REQUEST,
            'add': True,
            'change': False,
            'has_delete_permission': False,
            'has_change_permission': True,
            'has_absolute_url': False,
            'opts': self.model._meta,
            'original': user,
            'save_as': False,
            'show_save': True,
        }
        return TemplateResponse(request,
                                self.change_user_password_template or
                                'admin/auth/user/change_password.html',
                                context, current_app=self.admin_site.name)

    def response_add(self, request, obj, post_url_continue=None):
        """
        Determines the HttpResponse for the add_view stage. It mostly defers to
        its superclass implementation but is customized because the User model
        has a slightly different workflow.
        """
        # We should allow further modification of the user just added i.e. the
        # 'Save' button should behave like the 'Save and continue editing'
        # button except in two scenarios:
        # * The user has pressed the 'Save and add another' button
        # * We are adding a user in a popup
        if '_addanother' not in request.POST and '_popup' not in request.POST:
            request.POST['_continue'] = 1
        return super(UserAdmin, self).response_add(request, obj,
                                                   post_url_continue)


class OneFlowUserAdmin(UserAdmin, CSVAdminMixin):

    list_display = ('id', 'email', 'full_name_display',
                    'date_joined', 'last_login',
                    'profile_email_announcements_display',
                    'is_active', 'is_staff', 'is_superuser',
                    'groups_display', )
    list_display_links = ('email', 'full_name_display', )
    list_filter = ('profile__email_announcements',
                   'is_active', 'is_staff', 'is_superuser', )
    ordering = ('-date_joined',)
    date_hierarchy = 'date_joined'
    search_fields = ('email', 'first_name', 'last_name', )
    change_list_template = "admin/change_list_filter_sidebar.html"
    change_list_filter_template = "admin/filter_listing.html"
    inlines = [] if UserProfile is None else [UserProfileInline, ]

    def groups_display(self, obj):
        return u', '.join([g.name for g in obj.groups.all()]
                          ) if obj.groups.count() else u'—'

    groups_display.short_description = _(u'Groups')

    def full_name_display(self, obj):
        return obj.get_full_name()

    full_name_display.short_description = _(u'Full name')

    def profile_email_announcements_display(self, obj):
        return obj.profile.email_announcements

    profile_email_announcements_display.short_description = _(u'Announcements?')
    profile_email_announcements_display.admin_order_field = 'profile__email_announcements' # NOQA
    profile_email_announcements_display.boolean = True


admin.site.register(User, OneFlowUserAdmin)


if settings.FULL_ADMIN:
    subject_fields_names = tuple(('subject_' + code)
                                 for code, lang in languages)
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
