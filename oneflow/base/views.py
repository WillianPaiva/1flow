# -*- coding: utf-8 -*-

import logging

#from django.utils.translation import ugettext_lazy as _
from django.template import RequestContext
from django.template.loader import render_to_string

from sparks.django.utils import HttpResponseTemporaryServerError

LOGGER = logging.getLogger(__name__)


# WTF? @requires_csrf_token
def error_handler(request, *args, **kwargs):
    """ Returning a 503 seems much more correct: the situation is clearly
        temporary, the error will certainly be resolved. For searchbots this
        seems better too.

        http://agopian.info/blog/django-et-le-handler500-retourner-une-erreur-503.html # NOQA
    """

    #if kwargs.get('raise_exception', True):
    #    LOGGER.exception('Error while processing request')

    return HttpResponseTemporaryServerError(render_to_string('500.html',
                                            RequestContext(request)))


def crash(request, **kwargs):
    """ deliberately run a non-existent function,
        we need to have a way to trigger a 500. """

    raise RuntimeError(u'Voluntary crash test to validate the error chain.')
