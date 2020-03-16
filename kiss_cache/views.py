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
import pathlib
import time

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import IntegrityError
from django.db.models import F
from django.db.models.functions import Now
from django.conf import settings
from django.http import (
    FileResponse,
    HttpResponse,
    HttpResponseBadRequest,
    StreamingHttpResponse,
)
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_safe

from kiss_cache.__about__ import __version__
from kiss_cache.models import Resource, Statistic
from kiss_cache.tasks import fetch
from kiss_cache.utils import check_client_ip, is_client_allowed


def index(request):
    return render(
        request,
        "kiss_cache/index.html",
        {
            "api_url": request.build_absolute_uri(reverse("api.fetch")),
            "version": __version__,
        },
    )


def help(request):
    return render(
        request,
        "kiss_cache/help.html",
        {
            "ALLOWED_NETWORKS": settings.ALLOWED_NETWORKS,
            "user_ip": request.META.get("HTTP_X_FORWARDED_FOR", "??").split(",")[0],
            "user_ip_allowed": is_client_allowed(request),
            "api_url": request.build_absolute_uri(reverse("api.fetch")),
        },
    )


def statistics(request):
    # Compute the quota and current size
    size = Resource.total_size()
    quota = settings.RESOURCE_QUOTA
    progress = 0
    with contextlib.suppress(Exception):
        progress = int(size / quota * 100)
    if progress >= 85:
        progress_status = "danger"
    elif progress >= 60:
        progress_status = "warning"
    else:
        progress_status = "success"

    # Count the resources
    query = Resource.objects.order_by("url")
    scheduled = query.filter(state=Resource.STATE_SCHEDULED).count()
    downloading = query.filter(state=Resource.STATE_DOWNLOADING).count()
    successes = query.filter(state=Resource.STATE_FINISHED, status_code=200).count()
    failures = (
        query.filter(state=Resource.STATE_FINISHED).exclude(status_code=200).count()
    )
    return render(
        request,
        "kiss_cache/statistics.html",
        {
            "total_size": size,
            "quota": quota,
            "progress": progress,
            "progress_status": progress_status,
            "scheduled_count": scheduled,
            "downloading_count": downloading,
            "successes_count": successes,
            "failures_count": failures,
            "download": Statistic.objects.get(stat=Statistic.STAT_DOWNLOAD).value,
            "upload": Statistic.objects.get(stat=Statistic.STAT_UPLOAD).value,
        },
    )


def resources(request, page=1, state="successes"):
    query = Resource.objects.order_by("url")
    scheduled = query.filter(state=Resource.STATE_SCHEDULED).count()
    downloading = query.filter(state=Resource.STATE_DOWNLOADING).count()
    successes = query.filter(state=Resource.STATE_FINISHED, status_code=200).count()
    failures = (
        query.filter(state=Resource.STATE_FINISHED).exclude(status_code=200).count()
    )

    if state == "scheduled":
        query = query.filter(state=Resource.STATE_SCHEDULED)
    elif state == "downloading":
        query = query.filter(state=Resource.STATE_DOWNLOADING)
    elif state == "successes":
        query = query.filter(state=Resource.STATE_FINISHED, status_code=200)
    elif state == "failures":
        query = query.filter(state=Resource.STATE_FINISHED).exclude(status_code=200)
    else:
        return HttpResponseBadRequest("Invalid state")

    paginator = Paginator(query, 25)
    try:
        page = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        return HttpResponseBadRequest()

    return render(
        request,
        "kiss_cache/resources.html",
        {
            "resources": page,
            "state": state,
            "url_name": "resources." + state,
            "scheduled_count": scheduled,
            "downloading_count": downloading,
            "successes_count": successes,
            "failures_count": failures,
        },
    )


class HttpResponseServieUnavailable(HttpResponse):
    status_code = 503


@require_safe
def api_health(request):
    if pathlib.Path(settings.SHUTDOWN_PATH).exists():
        return HttpResponseServieUnavailable("Graceful shutdown")
    return HttpResponse("ok")


@check_client_ip
@require_safe
def api_fetch(request, filename=None):
    url = request.GET.get("url")
    ttl = request.GET.get("ttl", settings.DEFAULT_TTL)

    # Check parameters
    if url is None:
        return HttpResponseBadRequest("'url' should be specified")
    # Parse the TTL
    try:
        ttl = Resource.parse_ttl(ttl)
    except Exception:
        return HttpResponseBadRequest("Invalid 'ttl' value")

    try:
        # TODO: remove in case of exception in this function
        res, created = Resource.objects.get_or_create(url=url)
    except IntegrityError:
        res = Resource.objects.get(url=url)
        created = False

    # Set the last usage and increase the counter
    Resource.objects.filter(pk=res.pk).update(usage=F("usage") + 1, last_usage=Now())

    # If needed, fetch the url
    if created:
        # We don't know yet the size of the resource, so just check that the
        # quota is not already consumed
        if Resource.is_over_quota():
            Resource.objects.filter(pk=res.pk).update(
                state=Resource.STATE_FINISHED, status_code=507
            )
            return HttpResponse(status=507)

        # Set the ttl and the path
        res.path = Resource.compute_path(res.url)
        Resource.objects.filter(pk=res.pk).update(path=res.path, ttl=ttl)

        # Schedule the fetch task
        fetch.delay(res.url)
    else:
        # Set the TTL if the resulting date is earlier
        now = timezone.now()
        current_end = res.created_at + timedelta(seconds=res.ttl)
        new_end = now + timedelta(seconds=ttl)
        if current_end > new_end:
            ttl = (now - res.created_at).total_seconds() + ttl
            res.ttl = ttl
            Resource.objects.filter(pk=res.pk).update(ttl=ttl)

    res.refresh_from_db()
    if res.state == Resource.STATE_SCHEDULED:
        # Wait for the task to start
        # TODO: add timeout
        while True:
            res.refresh_from_db()
            if res.state != Resource.STATE_SCHEDULED:
                break
            time.sleep(1)

    # Update the statistics
    if res.content_length:
        Statistic.objects.filter(stat=Statistic.STAT_UPLOAD).update(
            value=F("value") + res.content_length
        )

    # The task has been started.
    if res.state == Resource.STATE_DOWNLOADING:
        response = StreamingHttpResponse(res.stream())
        if res.content_length:
            response["Content-Length"] = res.content_length
        if res.content_type:
            response["Content-Type"] = res.content_type
        if filename:
            response["Content-Disposition"] = "attachment; filename=%s" % filename
        return response
    elif res.state == Resource.STATE_FINISHED:
        # Check the status code
        if res.status_code != 200:
            return HttpResponse(status=res.status_code)

        # Just return the file
        response = FileResponse(res.open("rb"))
        if res.content_type:
            response["Content-Type"] = res.content_type
        if filename:
            response["Content-Disposition"] = "attachment; filename=%s" % filename
        return response
    else:
        raise NotImplementedError("new state value?")
