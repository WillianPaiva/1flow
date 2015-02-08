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

# import random
import logging

# from constance import config

import autocomplete_light

from django.conf import settings
from django import forms
# from django.utils.translation import ugettext as _
from codemirror import CodeMirrorTextarea

from ..models import ChainedItem


LOGGER = logging.getLogger(__name__)


class ChainedItemForm(autocomplete_light.ModelForm):

    """ A simple chained item model form. """

    class Meta:
        model = ChainedItem
        exclude = ('chain', 'item', 'position',
                   'is_active', 'is_valid', 'check_error', 'notes', )
        # fields = ('item', 'is_active',
        #           'parameters', )


class ChainedItemPositionForm(forms.ModelForm):

    """ A chained item model form to update its position in list. """

    class Meta:
        model = ChainedItem
        fields = ('position', )


class ChainedItemEditParametersForm(forms.ModelForm):

    """ Edit a chained item model parameters. """

    # Catched in the edit_field modal, avoid ESC/click-outside.
    prevent_accidental_close = True

    class Meta:
        model = ChainedItem
        fields = ('parameters', )
        widgets = {
            'parameters': CodeMirrorTextarea(
                mode='yaml',
                addon_js=settings.CODEMIRROR_ADDONS_JS,
                addon_css=settings.CODEMIRROR_ADDONS_CSS,
                keymap=settings.CODEMIRROR_KEYMAP,
            )
        }
