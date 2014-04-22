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


import logging
LOGGER = logging.getLogger(__name__)
import listparser
class BaseParser(object):
    """
        Parsers process raw data and return cleaned data
    """


    def parse(self):
        """
            Launch the actual mapping process
        """
        raise NotImplementedError


class OMPLParser(BaseParser):
    """
    Parse OPML and return a dictionary with cleaned data
    The dictionary structure is as follows :
    {
        "folders": [
            {
                "name": "folder1",
                "children": [
                    {
                        "name": "folder1-child1",
                    },
                    {
                        "name": "folder1-child2",
                        "children": [
                            {
                                "name": "folder1-child2-child1",
                            }
                        ]
                    }
                ],
                "subscriptions": [
                    {
                        "url": "http://feed.url",
                        "title": "Subscription inside folder1"
                    }
                ]
            },
        ]
    }
    """

    def parse(self, data_to_parse):
        """
        :param data_to_parse: Data provided par listparser.
        For example, listparser accept a URL or plain XML
        :return:
        """

        parsed_data = listparser.parse(data_to_parse)

        cleaned_data = {}
        cleaned_data['folders'] = []

        for

