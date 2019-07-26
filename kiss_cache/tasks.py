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
        (base / res.path).mkdir(mode=0o755, parents=True, exist_ok=True)
    except OSError:
        res.state = Resource.STATE_FAILED
        res.save(update_fields=["state"])
        raise

    # Download the resource
    req = requests.get(res.url, stream=True, timeout=settings.DOWNLOAD_TIMEOUT)
    # TODO: save the size in the database?
    #       will allow to print a nice progress bar
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
    res.state = Resource.STATE_COMPLETED
    res.save(update_fields=["state"])
