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

from django.conf import settings
from django import forms
from codemirror import CodeMirrorTextarea

from ..models import Processor


LOGGER = logging.getLogger(__name__)


class ProcessorForm(forms.ModelForm):

    """ A simple processor model form. """

    class Meta:
        model = Processor
        fields = (
            'name', 'slug', 'parent',
            # 'is_active',
            'needs_parameters',
        )


class ProcessorEditRequirementsForm(forms.ModelForm):

    """ Edit a processor model requirements. """

    # Catched in the edit_field modal, avoid ESC/click-outside.
    prevent_accidental_close = True

    class Meta:
        model = Processor
        fields = ('requirements', )
        widgets = {
            'requirements': CodeMirrorTextarea(
                mode='shell',
                addon_js=settings.CODEMIRROR_ADDONS_JS,
                addon_css=settings.CODEMIRROR_ADDONS_CSS,
                keymap=settings.CODEMIRROR_KEYMAP,
            )
        }


class ProcessorEditAcceptCodeForm(forms.ModelForm):

    """ Edit a processor model accept code. """

    # Catched in the edit_field modal, avoid ESC/click-outside.
    prevent_accidental_close = True

    class Meta:
        model = Processor
        fields = ('accept_code', )
        widgets = {
            'accept_code': CodeMirrorTextarea(
                mode='python',
                addon_js=settings.CODEMIRROR_ADDONS_JS,
                addon_css=settings.CODEMIRROR_ADDONS_CSS,
                keymap=settings.CODEMIRROR_KEYMAP,
            ),
        }


class ProcessorEditProcessCodeForm(forms.ModelForm):

    """ Edit a processor model process code. """

    # Catched in the edit_field modal, avoid ESC/click-outside.
    prevent_accidental_close = True

    class Meta:
        model = Processor
        fields = ('process_code', )
        widgets = {
            'process_code': CodeMirrorTextarea(
                mode='python',
                addon_js=settings.CODEMIRROR_ADDONS_JS,
                addon_css=settings.CODEMIRROR_ADDONS_CSS,
                keymap=settings.CODEMIRROR_KEYMAP,
            ),
        }
