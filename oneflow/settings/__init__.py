# -*- coding: utf-8 -*-
# Django settings for oneflow project, handled via sparks dynamic settings.

from sparks.django.settings import find_settings

execfile(find_settings(__file__))
