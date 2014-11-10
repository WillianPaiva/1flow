# -*- coding: utf-8 -*-
u"""
Copyright 2013-2014 Olivier Cortès <oc@1flow.io>.

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
from ..models import (
    HomePreferences, ReadPreferences,
    SelectorPreferences, StaffPreferences
)

LOGGER = logging.getLogger(__name__)


class HomePreferencesForm(forms.ModelForm):

    class Meta:
        model = HomePreferences
        fields = (
            'show_advanced_preferences',
            'read_shows',
            'experimental_features',
        )


class ReadPreferencesForm(forms.ModelForm):

    class Meta:
        model = ReadPreferences
        fields = (
            'starred_marks_read',
            'starred_marks_archived',
            'bookmarked_marks_archived',
            'watch_attributes_mark_archived',
            'starred_removes_bookmarked',
            'bookmarked_marks_unread',
            'reading_speed',
            'auto_mark_read_delay',
            'read_switches_to_fullscreen',
            'show_bottom_navbar',
        )


class SelectorPreferencesForm(forms.ModelForm):

    class Meta:
        model = SelectorPreferences
        fields = (
            'titles_show_unread_count',
            'lists_show_unread_count',
            'folders_show_unread_count',
            'extended_folders_depth',
            'subscriptions_in_multiple_folders',
            'show_closed_streams',
        )


class StaffPreferencesForm(forms.ModelForm):

    class Meta:
        model = StaffPreferences
        fields = (
            'super_powers_enabled',
            'reading_lists_show_bad_articles',
            'selector_shows_admin_links',
            'no_home_redirect',
        )
