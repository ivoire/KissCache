import pathlib
import requests
import time
from urllib.parse import urlencode

from django.db import IntegrityError
from django.conf import settings
from django.http import FileResponse
from django.shortcuts import render
from django.views.decorators.http import require_safe

from kiss_cache.models import Resource


@require_safe
def api_fetch(request, url):
    ttl = request.GET.get("ttl")

    print(request.GET)
    if len(request.GET.keys()):
        url = url + "?" + urlencode(request.GET)
    print(url)
    # Check parameters
    if ttl is None:
        ttl = settings.DEFAULT_TTL

    filename = "index.html"

    try:
        res, created = Resource.objects.get_or_create(url=url, filename=filename)
    except IntegrityError:
        res = Resource.objects.get(url=url)
        created = False

    # parse and set the ttl
    res.set_ttl(ttl)
    res.save()

    base = pathlib.Path(settings.DOWNLOAD_PATH)
    # If needed, fetch the url
    if created:
        res.set_path()
        res.save()
        (base / res.path).mkdir(mode=0o755, parents=True, exist_ok=True)
        with (base / res.path / res.filename).open(mode="wb") as f_in:
            req = requests.get(url, stream=True, timeout=settings.DOWNLOAD_TIMEOUT)
            for data in req.iter_content(chunk_size=settings.DOWNLOAD_CHUNK_SIZE, decode_unicode=False):
                f_in.write(data)
        # TODO: Handle errors
        res.state = Resource.STATE_COMPLETED
        res.save()
        # Send back the results
        response = FileResponse((base / res.path / res.filename).open("rb"))
        response["Content-Disposition"] = "attachment; filename=%s" % res.filename
        return response
    else:
        if res.state == Resource.STATE_DOWNLOADING:
            # Loop until the download is finished
            while True:
                time.sleep(1)
                res.refresh_from_db()
                if res.state != Resource.STATE_DOWNLOADING:
                    break
            if res.state == Resource.STATE_COMPLETED:
                response = FileResponse((base / res.path / res.filename).open("rb"))
                response["Content-Disposition"] = "attachment; filename=%s" % res.filename
                return response
            elif res.state == Resource.STATE_FAILED:
                srg
                
        elif res.state == Resource.STATE_COMPLETED:
            # Just return the file
            response = FileResponse((base / res.path / res.filename).open("rb"))
            response["Content-Disposition"] = "attachment; filename=%s" % res.filename
            return response
        elif res.state == Resource.STATE_FAILED:
            # TODO: raise an error?
            ea
        else:
            raise NotImplementedError("new state value?")
