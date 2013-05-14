# -*- coding: utf-8 -*-

import logging

#from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponseNotFound
from django.template import RequestContext
from django.template.loader import render_to_string

from sparks.django.utils import HttpResponseTemporaryServerError


LOGGER = logging.getLogger(__name__)


def error_handler(request, *args, **kwargs):
    """ Our error handler returns a 503 instead of a bare 500. Returning a 503
        seems much more correct: the situation is clearly temporary and the
        error will certainly be resolved. For search robots this is better too.

        Besides that point, our handler passes the whole request to the 500
        template, via the whole template context processors chain, which could
        be considered risky, but is really not because we don't have any
        custom processor and Django's one are fully tested (at least we hope).
    """

    return HttpResponseTemporaryServerError(render_to_string('500.html',
                                            context_instance=RequestContext(
                                            request)))


def not_found_handler(request, *args, **kwargs):
    """ Our 404 custom handler.

        Basically, it's just a one liner which does exactly what the Django's
        one does, but our 404.html lies in base/templates instead of
        ${root}/templates, and we have no way to specify only the modified
        path. And I don't want to create ${root}/templates just to hold the
        400.html.
    """

    return HttpResponseNotFound(render_to_string('404.html',
                                context_instance=RequestContext(request)))


def crash(request, **kwargs):
    """ deliberately run a non-existent function,
        we need to have a way to trigger a 500. """

    raise RuntimeError(u'Voluntary crash test to validate the error chain.')
