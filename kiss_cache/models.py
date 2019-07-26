import hashlib
import pathlib
import time

from django.db import models
from django.conf import settings
from django.http import Http404


class Resource(models.Model):
    url = models.URLField(unique=True)
    ttl = models.IntegerField(default=60 * 60 * 24)
    path = models.CharField(max_length=65, blank=True, null=True)
    filename = models.CharField(max_length=1024)
    last_usage = models.DateTimeField(blank=True, null=True)
    usage = models.IntegerField(default=0)

    STATE_SCHEDULED, STATE_DOWNLOADING, STATE_COMPLETED, STATE_FAILED = range(4)
    STATE_CHOICES = (
        (STATE_SCHEDULED, "Scheduled"),
        (STATE_DOWNLOADING, "Downloading"),
        (STATE_COMPLETED, "Completed"),
        (STATE_FAILED, "Failed"),
    )
    state = models.IntegerField(choices=STATE_CHOICES, default=STATE_SCHEDULED)

    # Parse the ttl
    @classmethod
    def parse_ttl(cls, val):
        if val.endswith("d"):
            ttl = int(val[:-1]) * 60 * 60 * 24
        elif val.endswith("h"):
            ttl = int(val[:-1]) * 60 * 60
        elif val.endswith("m"):
            ttl = int(val[:-1]) * 60
        elif val.endswith("s"):
            ttl = int(val[:-1])
        else:
            raise NotImplementedError("Unknow TTL value")

        if ttl <= 0:
            raise Exception("The TTL should be positive")
        return ttl

    # Compute the path
    @classmethod
    def compute_path(cls, url, filename):
        m = hashlib.sha256()
        m.update(url.encode("utf-8"))
        m.update(filename.encode("utf-8"))
        data = m.hexdigest()
        return str(pathlib.Path(data[0:2]) / data[2:])

    def size(self):
        try:
            return (
                (pathlib.Path(settings.DOWNLOAD_PATH) / self.path / self.filename)
                .stat()
                .st_size
            )
        except:
            return "??"

    def open(self, mode):
        return (pathlib.Path(settings.DOWNLOAD_PATH) / self.path / self.filename).open(
            mode
        )

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
                    time.sleep(1)
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
