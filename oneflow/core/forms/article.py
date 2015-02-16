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

# import autocomplete_light

from django.conf import settings
from django import forms
# from django.utils.translation import ugettext as _
from codemirror import CodeMirrorTextarea

from ..models import Article, HistoricalArticle, CONTENT_TYPES


LOGGER = logging.getLogger(__name__)


class DynamicModeEditForm(forms.ModelForm):

    """ a common form for all subsequent classes. """

    # Catched in the edit_field modal, avoid ESC/click-outside.
    prevent_accidental_close = True

    def set_editor_field_widget(self, field_name, mode):
        """ Create a field widget and set attributes accordingly. """

        self.fields[field_name].widget = CodeMirrorTextarea(
            mode=mode,
            addon_js=settings.CODEMIRROR_ADDONS_JS,
            addon_css=settings.CODEMIRROR_ADDONS_CSS,
            keymap=settings.CODEMIRROR_KEYMAP,
        )

    def test_html_content(self, content):
        """ Return True if content is likely to contain HTML. """

        return (
            u'<' in content
            and u'>' in content
            and u'</' in content
        )

    def test_content_type_html(self, content_type):
        """ Return True if content_type is HTML or cleaned HTML. """

        return content_type in (
            CONTENT_TYPES.HTML,
            CONTENT_TYPES.CLEANED_HTML,
        )


class ArticleEditExcerptForm(DynamicModeEditForm):

    """ Edit an article excerpt. """

    def __init__(self, *args, **kwargs):
        """ Hello pep257. You know I love you. """

        super(ArticleEditExcerptForm, self).__init__(*args, **kwargs)

        self.set_editor_field_widget(
            'excerpt',
            'html' if self.test_html_content(self.instance.excerpt)
            else 'markdown')

    class Meta:
        model = Article
        fields = ('excerpt', )


class ArticleEditContentForm(DynamicModeEditForm):

    """ Edit an article content. """

    def __init__(self, *args, **kwargs):
        """ Hello pep257. You know I love you. """

        super(ArticleEditContentForm, self).__init__(*args, **kwargs)

        self.set_editor_field_widget(
            'content',
            'html' if self.test_content_type_html(self.instance.content_type)
            else 'markdown')

    class Meta:
        model = Article
        fields = ('content', )


class HistoricalArticleEditExcerptForm(DynamicModeEditForm):

    """ Edit an article history excerpt. """

    def __init__(self, *args, **kwargs):
        """ Hello pep257. You know I love you. """

        super(HistoricalArticleEditExcerptForm, self).__init__(*args, **kwargs)

        self.set_editor_field_widget(
            'excerpt',
            'html' if self.test_html_content(self.instance.excerpt)
            else 'markdown')

    class Meta:
        model = HistoricalArticle
        fields = ('excerpt', )


class HistoricalArticleEditContentForm(DynamicModeEditForm):

    """ Edit an article history content. """

    def __init__(self, *args, **kwargs):
        """ Hello pep257. You know I love you. """

        super(HistoricalArticleEditContentForm, self).__init__(*args, **kwargs)

        self.set_editor_field_widget(
            'content',
            'html' if self.test_content_type_html(self.instance.content_type)
            else 'markdown')

    class Meta:
        model = HistoricalArticle
        fields = ('content', )
