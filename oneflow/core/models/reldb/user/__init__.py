# -*- coding: utf-8 -*-
u"""
Copyright 2014 Olivier Cortès <oc@1flow.io>.

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
from constance import config
from ..common import User
from ..feed import BaseFeed

from feeds import UserFeeds  # NOQA

from subscriptions import UserSubscriptions  # NOQA

from counters import UserCounters  # NOQA


def User_is_staff_or_superuser_and_enabled_property_get(self):
    """ Say if the user is an enabled staff member or super user.


    Eg. he/she *is* a staff member or super user **and** he/she has
    activated super powers in his/her preferences panel.
    """

    return ((self.is_staff or self.is_superuser)
            and self.preferences.staff.super_powers_enabled)


def User_unsubscribed_feeds_property_get(self):
    """ Return all good feeds the user is not subscribed to. """

    return BaseFeed.objects.good().exclude(
        id__in=self.all_subscriptions.all().values_list(
            'feed_id', flat=True))


def User_has_staff_access_property_get(self):
    """ Return ``True`` if user has staff access.

    Eg. if :meth:`is_staff_or_superuser_and_enabled` **and** if
    `config.STAFF_HAS_FULL_ACCESS` is ``True`` (it's not the default).

    Use this property on something when a staff member is accessing
    something he/she is not owner of, and this will raise a privacy
    issue.

    By opposition, the :meth:`is_staff_or_superuser_and_enabled`
    property is used only to add staff features to any page when
    the current user is staff and he accesses his own data. Eg. to
    include staff buttons or staff links to the admin.
    """

    return self.is_staff_or_superuser_and_enabled \
        and config.STAFF_HAS_FULL_ACCESS


User.has_staff_access = property(User_has_staff_access_property_get)
User.is_staff_or_superuser_and_enabled = property(
    User_is_staff_or_superuser_and_enabled_property_get)
User.unsubscribed_feeds = property(User_unsubscribed_feeds_property_get)
