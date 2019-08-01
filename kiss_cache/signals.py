# -*- coding: utf-8 -*-
# vim: set ts=4

# Copyright 2018 Rémi Duraffort
# This file is part of KissCache.
#
# KissCache is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# KissCache is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with KissCache.  If not, see <http://www.gnu.org/licenses/>

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
