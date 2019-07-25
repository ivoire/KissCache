import hashlib
import pathlib
import requests
from urllib.parse import urlparse

from django.db import models
from django.conf import settings
from django.http import Http404


class Resource(models.Model):
    url = models.URLField(unique=True)
    ttl = models.PositiveSmallIntegerField(default=60 * 60 * 24)
    path = models.CharField(max_length=65, blank=True, null=True)
    filename = models.CharField(max_length=1024)
    last_usage = models.DateTimeField(blank=True, null=True)
    usage = models.IntegerField(default=0)

    STATE_DOWNLOADING, STATE_COMPLETED, STATE_FAILED = range(3)
    STATE_CHOICES = (
        (STATE_DOWNLOADING, "Downloading"),
        (STATE_COMPLETED, "Completed"),
        (STATE_FAILED, "Failed"),
    )
    state = models.IntegerField(choices=STATE_CHOICES, default=STATE_DOWNLOADING)

    # Parse the ttl
    @classmethod
    def parse_ttl(cls, ttl):
        if ttl.endswith("d"):
            return int(ttl[:-1]) * 60 * 60 * 24
        elif ttl.endswith("h"):
            return int(ttl[:-1]) * 60 * 60
        elif ttl.endswith("m"):
            return int(ttl[:-1]) * 60
        elif ttl.endswith("s"):
            return int(ttl[:-1])
        else:
            raise NotImplementedError("Unknow TTL value")

    # Compute the path
    @classmethod
    def compute_path(self, url, filename):
        m = hashlib.sha256()
        m.update(url.encode("utf-8"))
        m.update(filename.encode("utf-8"))
        data = m.hexdigest()
        return str(pathlib.Path(data[0:2]) / data[2:])

    def size(self):
        return (pathlib.Path(settings.DOWNLOAD_PATH) / self.path / self.filename).stat().st_size

    def open(self, mode):
        return (pathlib.Path(settings.DOWNLOAD_PATH) / self.path / self.filename).open(mode)

    def stream(self):
        with self.open("rb") as f_in:
            while True:
                # Send as most data as possible
                data = f_in.read()
                while data:
                    yield data
                    data = f_in.read()

                # Are we done with downloading?
                try:
                    self.refresh_from_db()
                except Resource.DoesNotExist:
                    # The object was removed from the db => failure
                    self.state = Resource.STATE_FAILED
                if self.state != Resource.STATE_DOWNLOADING:
                    break
            # Send the remaining data
            data = f_in.read()
            while data:
                yield data
                data = f_in.read()

        if self.state == Resource.STATE_FAILED:
            raise Http404("Resource was removed")

    def fetch(self):
        req = requests.get(self.url, stream=True, timeout=settings.DOWNLOAD_TIMEOUT)
        with self.open(mode="wb") as f_out:
            for data in req.iter_content(chunk_size=settings.DOWNLOAD_CHUNK_SIZE, decode_unicode=False):
                f_out.write(data)
                yield data
        self.state = Resource.STATE_COMPLETED
        self.save(update_fields=["state"])
