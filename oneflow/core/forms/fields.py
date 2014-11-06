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
from django_select2.fields import HeavySelect2TagField

LOGGER = logging.getLogger(__name__)


class OnlyNameChoiceField(forms.ModelChoiceField):

    """ In forms we need something much simpler than `__unicode__()`. """

    def label_from_instance(self, obj):
        """ Get an indented label from the folder depth level. """

        level = obj.level - 1

        if level < 0:
            level = 0

        return (u' ' * 8 * level) + obj.name


class OnlyNameMultipleChoiceField(forms.ModelMultipleChoiceField):

    """ In forms we need something much simpler than `__unicode__()`. """

    def label_from_instance(self, obj):
        """ Get an indented label from depth level; only name if no depth. """

        try:
            level = obj.level - 1

        except AttributeError:
            return obj.name

        if level < 0:
            level = 0

        return (u' ' * 8 * obj.level - 1) + obj.name


class UsersMultipleAndTagField(HeavySelect2TagField):

    """ In forms we need something much simpler than `__unicode__()`. """

    def __init__(self, *args, **kwargs):
        """ COME AND INIT ME!. """

        self.user = kwargs.pop('user')

        super(UsersMultipleAndTagField, self).__init__(*args, **kwargs)

    def create_new_value(self, value):
        """ Create a new entry from address book. """

        LOGGER.info(u'CREATING new value from %s in %s address_book',
                    value, self.user.username)

        value = value.strip()

        things = value.split()

        # Is this an already existing 1flow user that wants to be created???
        if things[-1].startswith(u'@'):
            raise RuntimeError(u'BAD %s' % value)

        if value not in (None, u''):
            self.user.update(add_to_set__address_book=value)

            LOGGER.info(u'ADDED %s to %s address_book',
                        value, self.user.username)
            # self.user.safe_reload()
