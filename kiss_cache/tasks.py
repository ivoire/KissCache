# -*- coding: utf-8 -*-
# vim: set ts=4
#
# Copyright 2019 Linaro Limited
#
# Author: Rémi Duraffort <remi.duraffort@linaro.org>
#
# SPDX-License-Identifier: MIT

import contextlib
from datetime import timedelta
import logging
import math
import pathlib
import requests
import time

from celery import shared_task
from celery.utils.log import get_task_logger

from django.db.models import F
from django.conf import settings
from django.utils import timezone

from kiss_cache.__about__ import __version__
from kiss_cache.models import Resource, Statistic
from kiss_cache.utils import requests_retry


# Setup the loggers
logging.getLogger("requests").setLevel(logging.WARNING)
LOG = get_task_logger(__name__)


@shared_task(ignore_result=True)
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
            headers={"Accept-Encoding": "", "User-Agent": f"kisscache/{__version__}"},
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
        try:
            # variables to log progress
            last_logged_value = 0
            start = time.time()

            # Loop on the data
            iterator = req.iter_content(
                chunk_size=settings.DOWNLOAD_CHUNK_SIZE, decode_unicode=False
            )
            for data in iterator:
                size += f_out.write(data)

                if res.content_length:
                    percent = math.floor(size / float(res.content_length) * 100)
                    if percent >= last_logged_value + 5:
                        last_logged_value = percent
                        LOG.info(
                            "progress %3d%% (%dMB)", percent, int(size / (1024 * 1024))
                        )
                else:
                    if size >= last_logged_value + 25 * 1024 * 1024:
                        last_logged_value = size
                        LOG.info("progress %dMB", int(size / (1024 * 1024)))

            # Log the speed
            end = time.time()
            speed = "??"
            with contextlib.suppress(ZeroDivisionError):
                speed = "%0.2f" % round(size / (1024 * 1024 * (end - start)), 2)
            LOG.info(
                "%dMB downloaded in %0.2fs (%sMB/s)",
                size / (1024 * 1024),
                round(end - start, 2),
                speed,
            )

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


@shared_task(ignore_result=True)
def expire():
    LOG.info("Expiring resources")
    now = timezone.now()
    for res in Resource.objects.all():
        if res.created_at + timedelta(seconds=res.ttl) < now:
            LOG.info("* '%s'", res.url)
            res.delete()
    LOG.info("done")
