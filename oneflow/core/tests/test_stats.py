# -*- coding: utf-8 -*-
# pylint: disable=E1103,C0103
"""
    Copyright 2013-2014 Olivier Cortès <oc@1flow.io>

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

from django.test import TestCase
from django.test.utils import override_settings

from oneflow.base.tests import connect_mongodb_testsuite
from oneflow.core.models import Article
from oneflow.core.stats import (PythonErrorClassifier, GenericErrorClassifier,
                                UrlErrorClassifier, ContentErrorClassifier)

LOGGER = logging.getLogger(__file__)

connect_mongodb_testsuite()

Article.drop_collection()


@override_settings(STATICFILES_STORAGE=
                   'pipeline.storage.NonPackagingPipelineStorage',
                   CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
                   CELERY_ALWAYS_EAGER=True,
                   BROKER_BACKEND='memory',)
class ErrorClassifierTests(TestCase):

    def setUp(self):

        # NOTE: we need real web pages, else the absolutization won't work or
        # will find duplicates and tests will fail for a real-life reason.
        # Here we need to keep an article without any url_error, so we have
        # to make it point to a real working URL.
        self.a1 = Article(title='ErrorClassifierTests #1',
                          url='http://blog.1flow.io/post/59410536612/1flow-blog-has-moved').save() # NOQA

        self.a2 = Article(title='ErrorClassifierTests #2',
                          url='http://t.co/t2',
                          url_error="HTTPConnectionPool(host='t.co', port=80): Max retries exceeded with url: /t1 (Caused by <class 'socket.error'>: [Errno 60] Operation timed out)").save() # NOQA
        self.a3 = Article(title='ErrorClassifierTests #3',
                          url='http://t.co/t3',
                          url_error="HTTP Error 404 (Not Found) while resolving http://t.co/t3.").save() # NOQA
        self.a4 = Article(title='ErrorClassifierTests #4',
                          url='http://t.co/t4',
                          url_error="HTTP Error 404 (Not Found) while resolving http://t.co/t4.").save() # NOQA
        self.a5 = Article(title='ErrorClassifierTests #5',
                          url='http://t.co/t5',
                          url_error="HTTPConnectionPool(host='t.co', port=80): Max retries exceeded with url: /t5 (Caused by <class 'socket.error'>: [Errno 65] No route to host)").save() # NOQA
        self.a6 = Article(title='ErrorClassifierTests #6',
                          url='http://t.co/6',
                          url_error="HTTPConnectionPool(host='t.co', port=80): Max retries exceeded with url: /t6 (Caused by <class 'socket.error'>: [Errno 54] Connection reset by peer)").save() # NOQA

    def tearDown(self):
        Article.drop_collection()

    def test_python_errors_classifiers(self):

        results = PythonErrorClassifier(Article.objects(url_error__ne=''),
                                        'url_error').classify()

        stored = results.get('stored_instances')
        errors = results.get('error_types')

        self.assertEquals(results.get('seen_objects'), 5)

        self.assertEquals(len(errors), 5)
        self.assertEquals(len(stored), 5)

    def test_generic_errors_classifiers(self):

        results = GenericErrorClassifier(Article.objects(url_error__ne=''),
                                         'url_error').classify()

        stored = results.get('stored_instances')
        errors = results.get('error_types')

        self.assertEquals(results.get('seen_objects'), 5)

        self.assertEquals(len(errors), 5)
        self.assertEquals(len(stored), 5)

    def test_url_error_classifier(self):

        # NOTE: these errors strings are directly taken from the production
        #       database. Only URLs have been changed for tests.
        #

        results = UrlErrorClassifier(Article.objects(url_error__ne=''),
                                     'url_error').classify()

        self.assertEquals(sorted(results.keys()), [u'duration',
                          u'error_types', u'seen_objects', u'stored_instances'])
        self.assertEquals(results.get('seen_objects'), 5)

        stored = results.get('stored_instances')
        errors = results.get('error_types')

        self.assertEquals(len(errors), 4)
        self.assertEquals(len(stored), 4)

        err404 = stored.get(UrlErrorClassifier.ERR_NETWORK_HTTP404)

        self.assertEquals(len(err404), 2)
        self.assertTrue(self.a3 in err404)
        self.assertTrue(self.a4 in err404)

        err401 = stored.get(UrlErrorClassifier.ERR_NETWORK_HTTP401)
        self.assertEquals(err401, None)

    def test_content_error_classifier(self):

        # NOTE: these errors strings are directly taken from the production
        #       database. Only URLs have been changed for tests.
        #
        # ValidationError (Article:51fa68957711037f4003a37b) (1.GenericReferences can only contain documents: ['tags']): 1
        # ValidationError (Article:51fa68e47711037f3d03a3fe) (5.GenericReferences can only contain documents: ['tags']): 1
        # ValidationError (Article:51fa6b6aa24639329b2ce203) (1.GenericReferences can only contain documents: ['tags']): 1
        # ValidationError (Article:51fa69c3a24639329a2ce21a) (3.GenericReferences can only contain documents: ['tags']): 1
        # ValidationError (Article:51fa67a97711037f3d03a33d) (GenericReferences can only contain documents: ['tags']): 1
        # ValidationError (Article:51fa68e57711037f3d03a413) (4.GenericReferences can only contain documents: ['tags']): 1
        # ValidationError (Article:51fa64377711037f3f03a30c) (2.GenericReferences can only contain documents: ['tags']): 1
        # ValidationError (Article:51fa69c3a24639329a2ce207) (3.GenericReferences can only contain documents: ['tags']): 1
        # ValidationError (Article:51fa6b3f7711037f6a25ae46) (6.GenericReferences can only contain documents: ['tags']): 1
        # ValidationError (Article:51fa6b68a2463932a02ce2af) (11.GenericReferences can only contain documents: ['tags']): 1

        # TODO: url_error__ne -> content_error__ne
        # when we fully implement this test method.
        results = ContentErrorClassifier(Article.objects(url_error__ne=''),
                                         'content_error').classify()

        self.assertEquals(results.get('seen_objects'), 5)

        #
        # TODO: create articles and continue this test.
        #
