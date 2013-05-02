# -*- coding: utf-8 -*-

from django.contrib.sites import models
from django.db.models import signals
from django.conf import settings


def create_site(app, created_models, verbosity, **kwargs):
    """ Create the default site when when we install the sites framework. """

    if not models.Site in created_models:
        return

    try:
        models.Site.objects.get(pk=settings.SITE_ID)

    except models.Site.DoesNotExist:
        models.Site.objects.create(pk=settings.SITE_ID,
                                   name=settings.SITE_NAME,
                                   domain=settings.SITE_DOMAIN).save()

signals.post_syncdb.connect(create_site, sender=models)
