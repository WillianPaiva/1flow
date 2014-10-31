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

from oneflow.core import models


LOGGER = logging.getLogger(__name__)


class WebPagesImportForm(forms.ModelForm):

    """ Import quasi-anything from the web (RSS feeds, web pages…). """

    # urls = forms.CharField(label=_(u'Web addresses'), required=True,
    #                        widget=forms.Textarea())

    class Meta:
        model = models.UserImport
        fields = ('urls', )

    def save(self, user):
        """ Record the current user and the lines count. """

        # Just in case.
        self.instance.urls = u'\n'.join(
            l.strip() for l in self.instance.urls.splitlines())

        self.instance.user = user
        self.instance.lines = self.instance.count

        return super(WebPagesImportForm, self).save()
