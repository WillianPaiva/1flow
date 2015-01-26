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

# from django.conf import settings
from django import forms
# from codemirror import CodeMirrorTextarea

from ..models import ProcessingChain


LOGGER = logging.getLogger(__name__)


class ProcessingChainForm(forms.ModelForm):

    """ A simple processing chain model form. """

    class Meta:
        model = ProcessingChain
        fields = (
            'name', 'slug', 'parent',
            # 'is_active',
            # 'categories',
        )


# class ProcessingChainEditRequirementsForm(forms.ModelForm):
#
#     """ Edit a processing chain model requirements. """
#
#     class Meta:
#         model = ProcessingChain
#         fields = ('requirements', )
#         widgets = {
#             'requirements': CodeMirrorTextarea(
#                 mode='shell',
#                 addon_js=settings.CODEMIRROR_ADDONS_JS,
#                 addon_css=settings.CODEMIRROR_ADDONS_CSS,
#                 keymap=settings.CODEMIRROR_KEYMAP,
#             )
#         }
