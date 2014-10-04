# -*- coding: utf-8 -*-
"""
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

from ..models import MailFeedRule

LOGGER = logging.getLogger(__name__)


class MailFeedRuleForm(forms.ModelForm):

    """ A simple mail feed rule model form. """

    class Meta:
        model = MailFeedRule
        fields = ('account', 'header_field', 'other_header',
                  'match_type', 'match_value', 'match_action', )
