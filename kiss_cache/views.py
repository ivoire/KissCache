import pathlib
import requests
import time
from urllib.parse import urlencode

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import IntegrityError
from django.db.models import F
from django.db.models.functions import Now
from django.conf import settings
from django.http import FileResponse, HttpResponseBadRequest, StreamingHttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_safe

from kiss_cache.models import Resource


def index(request):
    return render(request, "kiss_cache/index.html", {})


def resources(request):
    paginator = Paginator(Resource.objects.order_by("url"), 25)
    try:
        page = paginator.page(request.GET.get("page", 1))
    except (PageNotAnInteger, EmptyPage):
        return HttpResponseBadRequest()

    return render(request, "kiss_cache/resources.html", {"resources": page})


@require_safe
def api_fetch(request, filename):
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
        res, created = Resource.objects.get_or_create(url=url, filename=filename)
    except IntegrityError as exc:
        print(exc)
        res = Resource.objects.get(url=url)
        created = False

    # Set the last usage and increase the counter
    Resource.objects.filter(url=url, filename=filename).update(
        usage=F("usage") + 1, last_usage=Now()
    )

    # parse and set the ttl
    res.refresh_from_db()
    res.ttl = ttl
    res.save(update_fields=["ttl"])

    base = pathlib.Path(settings.DOWNLOAD_PATH)
    # If needed, fetch the url
    if created:
        # Set the path
        res.path = Resource.compute_path(res.url, res.filename)
        res.save(update_fields=["path"])

        (base / res.path).mkdir(mode=0o755, parents=True, exist_ok=True)
        # Stream back the results
        response = StreamingHttpResponse(res.fetch())
        response["Content-Disposition"] = "attachment; filename=%s" % res.filename
        return response
    else:
        if res.state == Resource.STATE_DOWNLOADING:
            response = StreamingHttpResponse(res.stream())
            response["Content-Disposition"] = "attachment; filename=%s" % res.filename
            return response
        elif res.state == Resource.STATE_COMPLETED:
            # Just return the file
            response = FileResponse(res.open("rb"))
            response["Content-Disposition"] = "attachment; filename=%s" % res.filename
            return response
        elif res.state == Resource.STATE_FAILED:
            # TODO: raise an error?
            ea
        else:
            raise NotImplementedError("new state value?")
