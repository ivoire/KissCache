from datetime import timedelta
import time

from django.db.models.aggregates import Sum
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
from django.views.decorators.http import require_safe

from kiss_cache.models import Resource
from kiss_cache.tasks import fetch
from kiss_cache.utils import check_client_ip


def index(request):
    return render(request, "kiss_cache/index.html", {})


def statistics(request):
    # Compute the quota and current size
    size = Resource.objects.aggregate(size=Sum("content_length"))["size"]
    quota = settings.RESOURCE_QUOTA
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


@check_client_ip
@require_safe
def api_fetch(request, filename=None):
    # TODO: handle HEAD requests
    url = request.GET.get("url")
    ttl = request.GET.get("ttl")

    # Check parameters
    if url is None:
        return HttpResponseBadRequest("'url' should be specified")
    if ttl is None:
        ttl = settings.DEFAULT_TTL
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

    # Set the TTL if the resulting date is earlier
    res.refresh_from_db()
    if res.created_at + timedelta(seconds=res.ttl) > res.created_at + timedelta(
        seconds=ttl
    ):
        res.ttl = ttl
        res.save(update_fields=["ttl"])

    # If needed, fetch the url
    if created:
        # Set the path
        res.path = Resource.compute_path(res.url)
        res.save(update_fields=["path"])

        # Schedule the fetch task
        fetch.delay(res.url)

    if res.state == Resource.STATE_SCHEDULED:
        # Wait for the task to start
        # TODO: add timeout
        while True:
            res.refresh_from_db()
            if res.state != Resource.STATE_SCHEDULED:
                break
            time.sleep(1)

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
