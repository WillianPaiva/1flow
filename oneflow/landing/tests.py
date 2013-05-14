# -*- coding: utf-8 -*-
# pylint: disable=E1103,C0103

import logging

from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse

#from ..base.utils import send_email_with_db_content

LOGGER = logging.getLogger(__file__)


class LandingTests(TestCase):

    fixtures = ['base_2013-05-14_final-before-beta-opening',
                'landing_2013-05-14_final-before-beta-opening']

    def setUp(self):
        self.client = Client()

    def test_no_empty_mail(self):

        response = self.client.post(
            reverse('landing_home'), {'email': ''},
            follow=True
        )
        self.assertEqual(response.status_code, 200)

    def test_request_invive(self):

        response = self.client.post(
            reverse('landing_home'), {'email': 'olive@licorn.org'},
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        #LOGGER.debug(response)

    def test_sending_mails(self):

        # send_email_with_db_content(request,
        #                            'landing_thanks'
        #                            if has_invites_left
        #                            else 'landing_waiting_list',
        #                            user)
        pass
