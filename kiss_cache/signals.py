# -*- coding: utf-8 -*-
# vim: set ts=4
#
# Copyright 2019 Linaro Limited
#
# Author: Rémi Duraffort <remi.duraffort@linaro.org>
#
# SPDX-License-Identifier: MIT

import contextlib
import pathlib

from django.conf import settings
from django.db.models.signals import post_delete
from django.dispatch import receiver

from kiss_cache.models import Resource


@receiver(post_delete, sender=Resource)
def resource_post_delete(sender, **kwargs):
    resource = kwargs["instance"]
    base = pathlib.Path(settings.DOWNLOAD_PATH)
    with contextlib.suppress(Exception):
        (base / resource.path).unlink()
