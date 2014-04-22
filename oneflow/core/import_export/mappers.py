# -*- coding: utf-8 -*-
"""
    Copyright 2013-2014 Eliot Berriot <contact@eliotberriot.com>

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

from ..models.nonrel import Subscription, Folder, Feed
import logging
LOGGER = logging.getLogger(__name__)

class BaseMapper(object):
    """
        Mappers are used to convert parsed data into model instances
        this is a base class for all mappers
    """

    model = None

    def __init__(self, data, **kwargs):

        # data used to create model instances. Should be returned by parsers, for example
        self.data = data

        # additional data
        self.kwargs = kwargs

    def mapp(self):
        """
            Launch the actual mapping process
        """
        raise NotImplementedError


class SubscriptionMapper(BaseMapper):

    model = Subscription

    def __init__(self, data, **kwargs):
        super(SubscriptionMapper, self).__init__(data, **kwargs)
        self.kwargs['root_folder'] = Folder.objects.get(name=u'__root__', owner=self.kwargs.get('owner'))

    def mapp(self):


        folders = [self.create_folder(root_folder)
                                     for root_folder in self.data.get('folders')]

        subscriptions = [self.create_subscription(subscription)
                                     for subscription in self.data.get('subscriptions')]

        return folders

    def create_folder(self, data, parent=None):
        """
        Create an actual Folder instance from parsed data
        This method may be called recursively in case of multilevel hierarchy
        :param data:
        :return:
        """
        if not parent:
            parent = self.kwargs.get('root_folder')

        try:
            # check if a folder with the same name already exists at the same level
            f = Folder.objects.get(name=data.get('name'), parent=parent)


        except Folder.DoesNotExist:
            f = Folder()
            f.owner = self.kwargs.get('owner')
            f.name = data.get('name')
            f.parent = parent
            f.save()

        if data.get('children'):
            # If needed, create children folders using data,
            # and set them as children to parent folder
            # TODO :  when children are added, are their parent updated automatically in MongoDB ?

            f.children = [self.create_folder(child, parent=f) for child in data.get('children')]
            f.save()

        return f


    def create_subscription(self, data):
        """
        Create a a Feed (if necessary) and a Subscription
        :param feed:
        :return:
        """

        # Create the Feed if he does not exist
        feed = Feed.create_feeds_from_url(data.get('url'))[0][0]
        try:
            subscription = Subscription.objects.get(user=self.kwargs.get('owner'), feed=feed)
            # Subscription exists in DB, do nothing
            return subscription

        except Subscription.DoesNotExist:
            try:
                subscription = Subscription.subscribe_user_to_feed(
                    self.kwargs.get('owner'), feed, background=True)
                subscription.folders.append(folder)
                subscription.name = data.get('title')
                subscription.save()

            except Exception, sub_exc:
                message = u'Failed to subscribe user %s to feed %s' % (self.kwargs.get('owner'), feed)
                LOGGER.exception(message)
                return message

            else:
                # A user subscribing to a feed from the web implicitely
                # tells us that this feed is still running. Even if for
                # some reason we closed it in the past, it seems OK now.
                if feed.closed:
                    feed.reopen()

        return subscription

test_data = {
    "folders": [
        {
            "name": "root1",
            "children": [
                {
                    "name": "root1-child1",
                },
                {
                    "name": "root1-child2",
                    "children": [
                        {
                            "name": "root1-child2-child1",
                        }
                    ]
                }
            ],

        },
        {
            "name": "root2",
            "children": [
                {
                    "name": "root2-child1",
                },
                {
                    "name": "root2-child2",
                    "children": [
                        {
                            "name": "root2-child2-child1",
                        }
                    ]
                }
            ]
        }
    ],
    "subscriptions": [
        {
            "url": "http://kii.eliotberriot.com/user/eliotberriot/items/feed",
            "title": "Kii",
            "folder": ['root1', 'root1-child1']
        }
    ]
}