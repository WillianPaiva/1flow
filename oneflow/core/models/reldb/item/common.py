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

import hashlib
import logging


LOGGER = logging.getLogger(__name__)


__all__ = [
    'generate_orphaned_hash',
]


def generate_orphaned_hash(title, feeds):
    """ Return a unique hash for an article title in some feeds.

    .. warning:: should be used only for orphaned articles. At least,
        I created this function to distinguish duplicates in orphaned
        articles.
    """

    to_hash = u'{0}:{1}'.format(
        u','.join(sorted(unicode(f.id)
                  for f in feeds)), title).encode('utf-8')

    ze_hash = hashlib.sha1(to_hash).hexdigest()

    # LOGGER.debug(u'New HASH from : %s → %s', to_hash, ze_hash)

    return ze_hash
