# -*- coding: utf-8 -*-
# vim: set ts=4

# Copyright 2019 Rémi Duraffort
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

from datetime import timedelta
import logging
import pathlib
import requests

from celery import shared_task
from celery.utils.log import get_task_logger

from django.db.models import F
from django.conf import settings
from django.utils import timezone

from kiss_cache.models import Resource, Statistic
from kiss_cache.utils import requests_retry


# Setup the loggers
logging.getLogger("requests").setLevel(logging.WARNING)
LOG = get_task_logger(__name__)


@shared_task
def fetch(url):
    # TODO: should the resource be removed from the db if an exception is
    # raised (instead of setting a 50x status_code?)
    LOG.info("Fetching '%s'", url)
    # Grab the object from the database
    try:
        res = Resource.objects.get(url=url)
    except Resource.DoesNotExist:
        LOG.error("Resource db object does not exist for '%s'", url)
        return

    # Create the directory
    try:
        base = pathlib.Path(settings.DOWNLOAD_PATH)
        (base / res.path).parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    except OSError as exc:
        LOG.error("Unable to create the directory '%s'", str((base / res.path)))
        LOG.exception(exc)
        Resource.objects.filter(pk=res.pk).update(
            state=Resource.STATE_FINISHED, status_code=500
        )
        return

    # Download the resource
    # * stream back the result
    # * only accept plain content (not gziped) so Content-Length is known
    # * with a timeout
    try:
        req = requests_retry().get(
            res.url,
            stream=True,
            headers={"Accept-Encoding": ""},
            timeout=settings.DOWNLOAD_TIMEOUT,
        )
    except requests.RequestException as exc:
        LOG.error("Unable to connect to '%s'", url)
        LOG.exception(exc)
        Resource.objects.filter(pk=res.pk).update(
            state=Resource.STATE_FINISHED, status_code=502
        )
        return

    # Update the status code
    Resource.objects.filter(pk=res.pk).update(status_code=req.status_code)
    if req.status_code != 200:
        Resource.objects.filter(pk=res.pk).update(state=Resource.STATE_FINISHED)
        LOG.error("'%s' returned %d", url, req.status_code)
        req.close()
        return
    res.refresh_from_db()

    # Store Content-Length and Content-Type
    Resource.objects.filter(pk=res.pk).update(
        content_length=req.headers.get("Content-Length"),
        content_type=req.headers.get("Content-Type", ""),
    )
    res.refresh_from_db()

    # TODO: make this idempotent to allow for task restart
    size = 0
    with res.open(mode="wb") as f_out:
        # Informe the caller about the current state
        Resource.objects.filter(pk=res.pk).update(state=Resource.STATE_DOWNLOADING)
        res.refresh_from_db()
        # Iterate
        try:
            for data in req.iter_content(
                chunk_size=settings.DOWNLOAD_CHUNK_SIZE, decode_unicode=False
            ):
                size += f_out.write(data)
        except requests.RequestException as exc:
            LOG.error("Unable to fetch '%s'", url)
            LOG.exception(exc)
            Resource.objects.filter(pk=res.pk).update(
                state=Resource.STATE_FINISHED, status_code=504
            )
            req.close()
            return

    # Check or save the size
    if res.content_length:
        if res.content_length != size:
            LOG.error(
                "The total size (%d) is not equal to the Content-Length (%d)",
                size,
                res.content_length,
            )
            # TODO: do something
    else:
        Resource.objects.filter(pk=res.pk).update(content_length=size)

    # Update the statistics
    Statistic.objects.filter(stat=Statistic.STAT_DOWNLOAD).update(
        value=F("value") + size
    )

    # Mark the task as done
    Resource.objects.filter(pk=res.pk).update(state=Resource.STATE_FINISHED)
    LOG.info("[done]")


@shared_task
def expire():
    LOG.info("Expiring resources")
    now = timezone.now()
    for res in Resource.objects.all():
        if res.created_at + timedelta(seconds=res.ttl) < now:
            LOG.info("* '%s'", res.url)
            res.delete()
    LOG.info("done")
