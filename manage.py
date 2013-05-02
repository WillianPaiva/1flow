#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
from sparks.django import create_admin_user


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oneflow.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

    create_admin_user(email='admin@1flow.net')
