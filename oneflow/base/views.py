# -*- coding: utf-8 -*-


def crash(request, **kwargs):
    """ deliberately run a non-existent function,
        we need to have a way to trigger a 500. """

    raise RuntimeError(u'Voluntary crash test to validate the error chain.')
