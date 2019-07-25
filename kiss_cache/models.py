import hashlib
import pathlib
from urllib.parse import urlparse

from django.db import models
from django.conf import settings


class Resource(models.Model):
    url = models.URLField(unique=True)
    ttl = models.PositiveSmallIntegerField(default=60 * 60 * 24)
    path = models.CharField(max_length=65)
    filename = models.CharField(max_length=1024)

    STATE_DOWNLOADING, STATE_COMPLETED, STATE_FAILED = range(3)
    STATE_CHOICES = (
        (STATE_DOWNLOADING, "Downloading"),
        (STATE_COMPLETED, "Completed"),
        (STATE_FAILED, "Failed"),
    )
    state = models.IntegerField(choices=STATE_CHOICES, default=STATE_DOWNLOADING)

    # Parse the ttl
    def set_ttl(self, ttl):
        if ttl.endswith("d"):
            self.ttl = int(ttl[:-1]) * 60 * 60 * 24
        elif ttl.endswith("h"):
            self.ttl = int(ttl[:-1]) * 60 * 60
        elif ttl.endswith("m"):
            self.ttl = int(ttl[:-1]) * 60
        elif ttl.endswith("s"):
            self.ttl = int(ttl[:-1])
        else:
            raise NotImplementedError("Unknow TTL value")

    def set_path(self):
        m = hashlib.sha256()
        m.update(self.url.encode("utf-8"))
        m.update(self.filename.encode("utf-8"))
        data = m.hexdigest()
        self.path = str(pathlib.Path(data[0:2]) / data[2:])
