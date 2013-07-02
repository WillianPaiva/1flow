# -*- coding: utf-8 -*-

import warnings

with warnings.catch_warnings():
    # These warnings are produced by external packages
    # that we use in 1flow. We have no time to fix them
    # ourselves, and their developers didn't update their
    # own code. BUMMER!

    warnings.filterwarnings("ignore", category=DeprecationWarning)
    import django.conf.urls.defaults # NOQA
    import django.utils.hashcompat # NOQA
    try:
        import jpype # NOQA

    except ImportError:
        # In case we import on a machine where there is no JVM,
        # because JVM is installed only on 'medium' workers. In
        # fact, the standard install is completely broken (we
        # need to create symlinks for it to work properly), and
        # we should avoid crashing here,
        pass
