# -*- coding: utf-8 -*-

import logging

from django.contrib.sites import models
from django.db.models import signals
from django.conf import settings


LOGGER = logging.getLogger(__name__)


def create_site(app, created_models, verbosity, **kwargs):
    """ Create the default site when when we install the sites framework. """

    try:
        site = models.Site.objects.get(pk=settings.SITE_ID)

    except models.Site.DoesNotExist:
        site = models.Site.objects.create(pk=settings.SITE_ID,
                                          name=settings.SITE_NAME,
                                          domain=settings.SITE_DOMAIN)
        site.save()

        LOGGER.debug('Site created: %s', site)

    else:
        # update Django's example.com with our real data.
        site.name   = settings.SITE_NAME
        site.domain = settings.SITE_DOMAIN
        site.save()

        LOGGER.debug('Site updated: %s', site)


signals.post_syncdb.connect(create_site, sender=models)
