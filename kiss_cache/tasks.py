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

from django.conf import settings
from django.template.defaultfilters import filesizeformat
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
        Statistic.failures(1)
        return

    # Keep track of the total amount of data
    size = 0
    retries = 0
    max_retries = settings.RESOURCE_PARTIAL_DOWLOAD_RETRIES
    # TODO: make this idempotent to allow for task restart
    try:
        while retries < max_retries:
            # Download the resource
            # * stream back the result
            # * only accept plain content (not gzipped) so Content-Length is known
            # * with a timeout
            try:
                # Use a range header if this is a retry
                headers = {
                    "Accept-Encoding": "",
                    "User-Agent": f"KissCache/{__version__}",
                }
                if size:
                    headers["Range"] = f"bytes={size}-"

                req = requests_retry().get(
                    res.url,
                    stream=True,
                    headers=headers,
                    timeout=settings.DOWNLOAD_TIMEOUT,
                )
            except requests.RequestException as exc:
                LOG.error("Unable to connect to '%s'", url)
                LOG.exception(exc)
                Resource.objects.filter(pk=res.pk).update(
                    state=Resource.STATE_FINISHED, status_code=502
                )
                Statistic.failures(1)
                return

            # When retrying range requests should work, hence status_code is 206
            if retries > 0:
                if req.status_code != 206:
                    LOG.error("Unable to issue range requests when retrying")
                    req.status_code = 502
                else:
                    req.status_code = 200

            # Update the status code
            if req.status_code != 200:
                Resource.objects.filter(pk=res.pk).update(
                    status_code=req.status_code, state=Resource.STATE_FINISHED
                )
                Statistic.failures(1)
                LOG.error("'%s' returned %d", url, req.status_code)
                req.close()
                return
            Resource.objects.filter(pk=res.pk).update(status_code=200)
            res.refresh_from_db()

            if retries == 0:
                # Store Content-Length and Content-Type
                Resource.objects.filter(pk=res.pk).update(
                    content_length=req.headers.get("Content-Length"),
                    content_type=req.headers.get("Content-Type", ""),
                )
                res.refresh_from_db()

            # When retrying, append to the file
            mode = "wb" if retries == 0 else "ab"
            with res.open(mode=mode) as f_out:
                # Informe the caller about the current state
                Resource.objects.filter(pk=res.pk).update(
                    state=Resource.STATE_DOWNLOADING
                )
                res.refresh_from_db()

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
                                "progress %3d%% (%dMB)",
                                percent,
                                int(size / (1024 * 1024)),
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
            # Retry if kisscache was unable to download the full file
            if not res.content_length:
                break
            if res.content_length == size:
                break

            LOG.warning(
                "The total size (%d) is not equal to the Content-Length (%d)",
                size,
                res.content_length,
            )
            LOG.warning("Retrying (%d/%d) after 5 seconds", retries, max_retries)
            time.sleep(5)
            retries += 1

    except requests.RequestException as exc:
        LOG.error("Unable to fetch '%s'", url)
        LOG.exception(exc)
        Resource.objects.filter(pk=res.pk).update(
            state=Resource.STATE_FINISHED, status_code=504
        )
        Statistic.failures(1)
        return

    except Exception as exc:
        LOG.error("Unable to fetch '%s'", url)
        LOG.exception(exc)
        Resource.objects.filter(pk=res.pk).update(
            state=Resource.STATE_FINISHED, status_code=504
        )
        Statistic.failures(1)
        return

    # Check or save the size
    if res.content_length:
        if res.content_length != size:
            LOG.error(
                "The total size (%d) is not equal to the Content-Length (%d)",
                size,
                res.content_length,
            )
            # Set the status_code to 502 so it will be removed soon
            Resource.objects.filter(pk=res.pk).update(
                state=Resource.STATE_FINISHED, status_code=504
            )
            Statistic.download(size)
            Statistic.failures(1)
    else:
        Resource.objects.filter(pk=res.pk).update(content_length=size)

    # Update the statistics
    Statistic.download(size)
    Statistic.successes(1)

    # Mark the task as done
    Resource.objects.filter(pk=res.pk).update(state=Resource.STATE_FINISHED)


@shared_task(ignore_result=True)
def expire():
    LOG.info("Removing failed resources")
    query = Resource.objects.filter(state=Resource.STATE_FINISHED)
    for res in query.exclude(status_code=200):
        LOG.info("* '%s'", res.url)
        res.delete()
    LOG.info("done")

    LOG.info("Expiring resources")
    for res in Resource.objects.filter(state=Resource.STATE_FINISHED):
        if res.created_at + timedelta(seconds=res.ttl) < timezone.now():
            LOG.info("* '%s'", res.url)
            res.delete()
    LOG.info("done")

    LOG.info("Checking quota usage")
    limit = settings.RESOURCE_QUOTA * settings.RESOURCE_QUOTA_AUTO_CLEAN / 100
    if Resource.total_size() > limit:
        LOG.info(
            "* Cleaning by last usage (%s > %s)",
            filesizeformat(Resource.total_size()),
            filesizeformat(limit),
        )
        last_usage_limit = timezone.now() - timedelta(
            seconds=settings.RESOURCE_QUOTA_AUTO_CLEAN_DELAY
        )
        while Resource.total_size() > limit:
            try:
                q = Resource.objects.filter(state=Resource.STATE_FINISHED)
                q = q.filter(last_usage__lt=last_usage_limit)
                res = q.order_by("last_usage")[0]
                LOG.info("  - %s: '%s'", filesizeformat(res.content_length), res.url)
                res.delete()
            except IndexError:
                LOG.info("* No more resources to clean")
                break
    LOG.info("* Usage: %s", filesizeformat(Resource.total_size()))
    LOG.info("done")
