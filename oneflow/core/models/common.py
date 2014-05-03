# -*- coding: utf-8 -*-
"""
    Copyright 2014 Olivier Cortès <oc@1flow.io>

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
    License along with 1flow. If not, see http://www.gnu.org/licenses/

    ————————————————————————————————————————————————————————————————————————————

    .. note:: as of Celery 3.0.20, there are many unsolved problems related
        to tasks-as-methods. Just to name a few:
        - https://github.com/celery/celery/issues/1458
        - https://github.com/celery/celery/issues/1459
        - https://github.com/celery/celery/issues/1478

        As I have no time to dive into celery's code and fix them myself,
        I just turned tasks-as-methods into standard tasks calling the
        method inside the task.

        This has the side-effect benefit of avoiding any `.reload()` call
        inside the tasks methods themselves, at the expense of needing to
        register the methods as standard tasks manually.

        But in the meantime, this allows tests to work correctly, which is
        a cool benefit.

        Special post-create tasks must be named ``def class_post_create_task()``
        not just ``class_post_create()``. This is because these special
        methods are not meant to be called in the app normal life, but only
        at a special moment (after database record creation, exactly).
        BUT, I prefer the name of the celery task to stay without
        the ``_task`` suffix for shortyness and readability in celery flower.
"""

import logging

LOGGER = logging.getLogger(__name__)


class ModelMixin():
    """ Common methods to all our Models.


        .. versionadded: 0.99
    """

    pass
