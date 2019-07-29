import pathlib
import requests

from celery import shared_task
from django.conf import settings

from kiss_cache.models import Resource


@shared_task
def fetch(url):
    # Grab the object from the database
    res = Resource.objects.get(url=url)

    # Create the directory
    try:
        base = pathlib.Path(settings.DOWNLOAD_PATH)
        (base / res.path).parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    except OSError:
        res.state = Resource.STATE_FAILED
        res.save(update_fields=["state"])
        raise

    # Download the resource
    # * stream back the result
    # * only accept plain content (not gziped) so Content-Length is known
    # * with a timeout
    req = requests.get(
        res.url,
        stream=True,
        headers={"Accept-Encoding": ""},
        timeout=settings.DOWNLOAD_TIMEOUT,
    )

    # Save the status code
    res.status_code = req.status_code
    if res.status_code != 200:
        res.state = Resource.STATE_FINISHED
        res.save(update_fields=["state", "status_code"])
        LOG.error("'%s' returned %d", url, res.status_code)
        return
    res.save(update_fields=["status_code"])

    # Store Content-Length and Content-Type
    res.content_length = req.headers.get("Content-Length")
    res.content_type = req.headers.get("Content-Type", "")
    res.save(update_fields=["content_length", "content_type"])

    # TODO: make this idempotent to allow for task restart
    with res.open(mode="wb") as f_out:
        # Informe the caller about the current state
        res.state = Resource.STATE_DOWNLOADING
        res.save(update_fields=["state"])
        # Iterate
        # TODO: except requests.exceptions
        for data in req.iter_content(
            chunk_size=settings.DOWNLOAD_CHUNK_SIZE, decode_unicode=False
        ):
            f_out.write(data)

    # Mark the task as done
    res.state = Resource.STATE_FINISHED
    res.save(update_fields=["state"])
