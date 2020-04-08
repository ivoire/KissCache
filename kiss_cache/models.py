# -*- coding: utf-8 -*-
# vim: set ts=4
#
# Copyright 2019 Linaro Limited
#
# Author: Rémi Duraffort <remi.duraffort@linaro.org>
#
# SPDX-License-Identifier: MIT

import contextlib
import hashlib
import pathlib
import time

from django.db import models
from django.db.models.aggregates import Sum
from django.conf import settings


class Resource(models.Model):
    # TODO: max_length=?
    url = models.URLField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    ttl = models.IntegerField(default=60 * 60 * 24)
    content_length = models.IntegerField(blank=True, null=True)
    content_type = models.CharField(max_length=256, blank=True)
    last_usage = models.DateTimeField(blank=True, null=True)
    usage = models.IntegerField(default=0)

    STATE_SCHEDULED, STATE_DOWNLOADING, STATE_FINISHED = range(3)
    STATE_CHOICES = (
        (STATE_SCHEDULED, "Scheduled"),
        (STATE_DOWNLOADING, "Downloading"),
        (STATE_FINISHED, "Finished"),
    )
    state = models.IntegerField(choices=STATE_CHOICES, default=STATE_SCHEDULED)
    status_code = models.IntegerField(default=0)

    @property
    def path(self):
        """ Compute the path of the local file """
        # TODO: take created_at into account
        m = hashlib.sha256()
        m.update(self.url.encode("utf-8"))
        data = m.hexdigest()
        return str(pathlib.Path(data[0:2]) / data[2:])

    @classmethod
    def parse_ttl(cls, val):
        """
        Parse the TTL (Time To Live)

        The TTL should be of the form <integer><unit>.
        Accepted units are "dhms" for days, hours, minutes and seconds.
        """
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

    @classmethod
    def total_size(cls):
        """ Compute the sum of the size of all Resources """
        size = cls.objects.aggregate(size=Sum("content_length"))["size"]
        if size is None:
            size = 0
        return size

    @classmethod
    def is_over_quota(cls):
        """ Returns True if the quota is already fully used """
        if settings.RESOURCE_QUOTA <= 0:
            return False
        return bool(cls.total_size() >= settings.RESOURCE_QUOTA)

    def progress(self):
        """ Return a string with the download progress """
        size = 0
        with contextlib.suppress(Exception):
            size = (pathlib.Path(settings.DOWNLOAD_PATH) / self.path).stat().st_size
        max_size = self.content_length
        with contextlib.suppress(Exception):
            return int(size / max_size * 100)
        return "??"

    def open(self, mode):
        """ Open the underlying file and return the file object """
        return (pathlib.Path(settings.DOWNLOAD_PATH) / self.path).open(mode)

    def stream(self):
        """
        Stream the resource while it's being downloaded.

        If the database object is removed, raise a 404.
        """
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
                    # The object was removed from the db => 404
                    self.status_code = 404
                    self.state = Resource.STATE_FINISHED

                if self.state == Resource.STATE_FINISHED:
                    break

            # Check the status code
            if self.status_code != 200:
                raise Exception("status-code is not 200: %d" % self.status_code)

            # Send the remaining data
            data = f_in.read()
            while data:
                yield data
                data = f_in.read()


class Statistic(models.Model):
    STAT_DOWNLOAD, STAT_UPLOAD = range(2)
    STAT_CHOICES = ((STAT_DOWNLOAD, "Download"), (STAT_UPLOAD, "Upload"))
    stat = models.IntegerField(choices=STAT_CHOICES, primary_key=True)
    value = models.BigIntegerField(default=0)
