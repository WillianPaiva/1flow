# -*- coding: utf-8 -*-
"""
Copyright 2012-2014 Olivier Cortès <oc@1flow.io>.

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
# from tastypie.exceptions import Unauthorized
from tastypie.authentication import (MultiAuthentication,
                                     SessionAuthentication,
                                     ApiKeyAuthentication)
from tastypie.resources import ModelResource, ALL

# from tastypie import fields

from django.contrib.auth import get_user_model


LOGGER = logging.getLogger(__name__)


def SessionAndApiKeyAuthentications():
    """ Use like a standard TastyPie Authentication. """

    return MultiAuthentication(
        SessionAuthentication(), ApiKeyAuthentication())


class UserObjectsOnlyAuthorization(Authorization):

    """ Basic Authorization.

    cf. http://django-tastypie.readthedocs.org/en/latest/authorization.html
    """

    def __init__(self, *args, **kwargs):
        """ OMG. Init is init, pep257. """

        self.parent_chain = tuple(kwargs.get('parent_chain', ()))

    def obj_chain(self, obj):
        """ Return the last object of the parent-children chain.

        Eg. if we are authorizing on a class Child which has a Parent
        which has a GrandParent (which has a `.user` attribute), do
        equivalent of returning child.parent.grandparent.user, whatever
        the nesting level the chain is.
        """

        current_obj = obj

        for chain_node in self.parent_chain + ('user', ):
            current_obj = getattr(current_obj, chain_node)

        return current_obj

    def switch_permission(self, obj, user):
        """ Return True if :param:`obj` is owned by :param:`user`.

        We have 2 cases because we have 2 databases (NoSQL and relational).
        """

        try:
            # An object in the MongoDB database will have a `.django_user`.
            return obj.django_user == user

        except AttributeError:
            # An object in the relational database has a `.user` attribute.
            return obj == user

    def read_list(self, object_list, bundle):
        """ Return read list permission for current user. """

        user = bundle.request.user

        if user.is_superuser:
            return object_list

        # TODO:
        # if user.is_staff and …:

        kwargs = {'__'.join(self.parent_chain + ('user', )): user}

        try:
            return object_list.filter(**kwargs)

        except:
            # In case we are accessing the `User` model,
            # it has no 'user' field, we need to check the ID.
            #
            # TODO: make this a dedicated authorisation
            #       class for our `UserResource` class.
            return object_list.filter(id=user.id)

    def read_detail(self, object_list, bundle):
        """ Return read detail permissions for current user.

        Eg. “Is the requested object (or the object's parent if we have
        a parent chain defined) owned by the user?”
        """

        user = bundle.request.user

        if user.is_superuser:
            return True

        obj = self.obj_chain(bundle.obj)

        return self.switch_permission(obj, user)

    def create_list(self, object_list, bundle):
        """ TODO: understand me, implement me better, document me. """

        user = bundle.request.user

        if user.is_superuser:
            return object_list

        # Assuming they're auto-assigned to ``user``.
        return object_list

    def create_detail(self, object_list, bundle):
        """ TODO: make this method more granular for some types of objects.

        For now, the same authorization as :meth:`read_detail`.
        """

        return self.read_detail(object_list, bundle)

    def update_list(self, object_list, bundle):
        """ Return the list of objects the user is allowed to update. """

        allowed = []

        user = bundle.request.user

        if user.is_superuser:
            return object_list

        # Since they may not all be saved, iterate over them.
        for obj in object_list:

            current_obj = self.obj_chain(obj)

            if self.switch_permission(current_obj, user):
                allowed.append(obj)

        return allowed

    def update_detail(self, object_list, bundle):
        """ Return the permission to update details of the object.

        For now, the same authorization as :meth:`read_detail`.
        """

        return self.read_detail(object_list, bundle)

    def delete_list(self, object_list, bundle):
        """ Same authorization as :meth:`update_list`. """

        return self.update_list(object_list, bundle)

    def delete_detail(self, object_list, bundle):
        """ Same authorization as :meth:`update_detail`. """

        return self.update_detail(object_list, bundle)


User = get_user_model()


class EmberMeta:

    """ Ember-data default parameters. """

    # Ember-data expect the following 2 directives
    always_return_data = True
    allowed_methods    = ('get', 'post', 'put', 'delete')

    # These are specific to 1flow functionnals.
    authentication     = SessionAndApiKeyAuthentications()
    authorization      = UserObjectsOnlyAuthorization()


class UserResource(ModelResource):

    """ 1flow (Relational DB) user resource. """

    class Meta(EmberMeta):
        queryset = User.objects.all()
        resource_name = 'user'
        filtering = {'id': ALL, }
        ordering = ALL


__all__ = ('UserObjectsOnlyAuthorization', 'EmberMeta',
           'SessionAndApiKeyAuthentications', 'UserResource', )
