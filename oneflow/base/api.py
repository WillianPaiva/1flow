# -*- coding: utf-8 -*-
"""
    Copyright 2012-2014 Olivier Cortès <oc@1flow.io>

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

from tastypie.authorization import Authorization  # , DjangoAuthorization
from tastypie.exceptions import Unauthorized
from tastypie.authentication import (MultiAuthentication,
                                     SessionAuthentication,
                                     ApiKeyAuthentication)
from tastypie.resources import ModelResource, ALL

#from tastypie import fields

from django.contrib.auth import get_user_model


LOGGER = logging.getLogger(__name__)

common_authentication = MultiAuthentication(SessionAuthentication(),
                                            ApiKeyAuthentication())


class UserObjectsOnlyAuthorization(Authorization):
    """ Basic Authorization

        cf. http://django-tastypie.readthedocs.org/en/latest/authorization.html
    """

    def read_list(self, object_list, bundle):
        user = bundle.request.user

        if user.is_staff or user.is_superuser:
            return object_list

        try:
            return object_list.filter(user=user)

        except:
            # In case we are accessing the `User` model,
            # it has no 'user' field, we need to check the ID.
            #
            # TODO: make this a dedicated authorisation
            #       class for our `UserResource` class.
            return object_list.filter(id=user.id)

    def read_detail(self, object_list, bundle):
        # Is the requested object owned by the user?

        user = bundle.request.user

        try:
            return bundle.obj.user == user or user.is_staff or user.is_superuser

        except AttributeError:
            return bundle.obj == user or user.is_staff or user.is_superuser

    def create_list(self, object_list, bundle):
        # Assuming their auto-assigned to ``user``.
        return object_list

    def create_detail(self, object_list, bundle):
        """ TODO: make this method more granular for some types of objects. """

        user = bundle.request.user

        try:
            return bundle.obj.user == user or user.is_staff or user.is_superuser

        except AttributeError:
            return user.is_staff or user.is_superuser

    def update_list(self, object_list, bundle):
        allowed = []

        user = bundle.request.user

        # Since they may not all be saved, iterate over them.
        for obj in object_list:
            try:
                # Django User is tried first.
                object_user_id = obj.user.django_user

            except AttributeError:
                # If not, we get the MongoDB id.
                object_user_id = obj.user.id

            if user.is_staff or user.is_superuser or object_user_id == user.id:
                allowed.append(obj)

        return allowed

    def update_detail(self, object_list, bundle):
        try:
            return bundle.obj.user.django_user == bundle.request.user.id

        except AttributeError:
            return bundle.obj == bundle.request.user

    def delete_list(self, object_list, bundle):
        """ TODO: implement staff/superuser. """
        # Sorry user, no deletes for you!
        raise Unauthorized("Sorry, no deletes.")

    def delete_detail(self, object_list, bundle):
        """ TODO: implement staff/superuser. """
        raise Unauthorized("Sorry, no deletes.")


User = get_user_model()


class EmberMeta:
    # Ember-data expect the following 2 directives
    always_return_data = True
    allowed_methods    = ('get', 'post', 'put', 'delete')

    # These are specific to 1flow functionnals.
    authentication     = common_authentication
    authorization      = UserObjectsOnlyAuthorization()


class UserResource(ModelResource):

    class Meta(EmberMeta):
        queryset = User.objects.all()
        resource_name = 'user'
        filtering = {'id': ALL, }
        ordering = ALL


__all__ = ('UserObjectsOnlyAuthorization', 'EmberMeta',
           'common_authentication', 'UserResource', )
