import logging
import pathlib
import requests

from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings

from kiss_cache.models import Resource


# Setup the loggers
logging.getLogger("requests").setLevel(logging.WARNING)
LOG = get_task_logger(__name__)


@shared_task
def fetch(url):
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
        res.state = Resource.STATE_FINISHED
        res.status_code = 500
        res.save(update_fields=["state", "status_code"])
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
    LOG.info("[done]")
