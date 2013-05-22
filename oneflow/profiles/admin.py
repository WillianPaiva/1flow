# -*- coding: utf-8 -*-

from django.contrib import admin
from django.contrib.auth.models import User  # , Group
from django.contrib.auth.admin import UserAdmin as AuthUserAdmin
from django.utils.translation import ugettext_lazy as _

from ..base.admin import NearlyReadOnlyAdmin, CSVAdminMixin
from .models import UserProfile


class UserProfileAdmin(CSVAdminMixin):
    ordering = ('-last_modified', )
    date_hierarchy = 'last_modified'
    list_filter = ('last_modified', )


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False


class UserAdmin(NearlyReadOnlyAdmin, CSVAdminMixin, AuthUserAdmin):

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
    inlines = [UserProfileInline, ]

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

admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
