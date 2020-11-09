# -*- coding: utf-8 -*-
# vim: set ts=4
#
# Copyright 2019 Linaro Limited
#
# Author: Rémi Duraffort <remi.duraffort@linaro.org>
#
# SPDX-License-Identifier: MIT

from datetime import timedelta
import logging
import requests

from django.utils import timezone

from kiss_cache.__about__ import __version__
from kiss_cache.models import Resource, Statistic
from kiss_cache.tasks import expire, fetch


def test_fetch(caplog, db, mocker, settings, tmpdir):
    caplog.set_level(logging.DEBUG)
    settings.DOWNLOAD_PATH = str(tmpdir)

    Resource.objects.create(url="https://example.com")

    class Response:
        status_code = 200
        headers = {"Content-Length": 10, "Content-Type": "text/html; charset=UTF-8"}

        def iter_content(self, chunk_size, decode_unicode):
            assert chunk_size == settings.DOWNLOAD_CHUNK_SIZE
            assert decode_unicode is False
            return [b"h", b"e", b"l", b"l", b"o", b" ", b"w", b"o", b"r", b"l"]

        def close(self):
            pass

    class RequestRetry:
        def get(self, url, stream, headers, timeout):
            assert url == "https://example.com"
            assert stream is True
            assert headers == {
                "Accept-Encoding": "",
                "User-Agent": f"KissCache/{__version__}",
            }
            assert timeout == settings.DOWNLOAD_TIMEOUT
            return Response()

    def requests_retry():
        return RequestRetry()

    mocker.patch("kiss_cache.tasks.requests_retry", requests_retry)
    mocker.patch("time.time", lambda: 0)

    fetch("https://example.com")
    assert (
        tmpdir / "10/0680ad546ce6a577f42f52df33b4cfdca756859e664b8d7de329b150d09ce9"
    ).read_text(encoding="utf-8") == "hello worl"
    res = Resource.objects.get(url="https://example.com")
    assert res.state == Resource.STATE_FINISHED
    assert res.content_type == "text/html; charset=UTF-8"
    assert res.content_length == 10
    assert Statistic.objects.get(stat=Statistic.STAT_DOWNLOAD).value == 10
    assert caplog.record_tuples == [
        ("kiss_cache.tasks", 20, "Fetching 'https://example.com'"),
        ("kiss_cache.tasks", 20, "progress  10% (0MB)"),
        ("kiss_cache.tasks", 20, "progress  20% (0MB)"),
        ("kiss_cache.tasks", 20, "progress  30% (0MB)"),
        ("kiss_cache.tasks", 20, "progress  40% (0MB)"),
        ("kiss_cache.tasks", 20, "progress  50% (0MB)"),
        ("kiss_cache.tasks", 20, "progress  60% (0MB)"),
        ("kiss_cache.tasks", 20, "progress  70% (0MB)"),
        ("kiss_cache.tasks", 20, "progress  80% (0MB)"),
        ("kiss_cache.tasks", 20, "progress  90% (0MB)"),
        ("kiss_cache.tasks", 20, "progress 100% (0MB)"),
        ("kiss_cache.tasks", 20, "0MB downloaded in 0.00s (??MB/s)"),
    ]


def test_fetch_no_content_length(caplog, db, mocker, settings, tmpdir):
    caplog.set_level(logging.DEBUG)
    settings.DOWNLOAD_PATH = str(tmpdir)

    Resource.objects.create(url="https://example.com")

    class Response:
        status_code = 200
        headers = {"Content-Type": "text/html; charset=UTF-8"}

        def iter_content(self, chunk_size, decode_unicode):
            assert chunk_size == settings.DOWNLOAD_CHUNK_SIZE
            assert decode_unicode is False
            return [b"h", b"e", b"l", b"l", b"o", b" ", b"w", b"o", b"r", b"l"]

        def close(self):
            pass

    class RequestRetry:
        def get(self, url, stream, headers, timeout):
            assert url == "https://example.com"
            assert stream is True
            assert headers == {
                "Accept-Encoding": "",
                "User-Agent": f"KissCache/{__version__}",
            }
            assert timeout == settings.DOWNLOAD_TIMEOUT
            return Response()

    def requests_retry():
        return RequestRetry()

    mocker.patch("kiss_cache.tasks.requests_retry", requests_retry)
    mocker.patch("time.time", lambda: 0)

    fetch("https://example.com")
    assert (
        tmpdir / "10/0680ad546ce6a577f42f52df33b4cfdca756859e664b8d7de329b150d09ce9"
    ).read_text(encoding="utf-8") == "hello worl"
    res = Resource.objects.get(url="https://example.com")
    assert res.state == Resource.STATE_FINISHED
    assert res.content_type == "text/html; charset=UTF-8"
    assert res.content_length == 10
    assert Statistic.objects.get(stat=Statistic.STAT_DOWNLOAD).value == 10
    assert caplog.record_tuples == [
        ("kiss_cache.tasks", 20, "Fetching 'https://example.com'"),
        ("kiss_cache.tasks", 20, "0MB downloaded in 0.00s (??MB/s)"),
    ]


def test_fetch_errors(caplog, db, mocker, settings, tmpdir):
    caplog.set_level(logging.DEBUG)

    # db object does not exist
    fetch("https://example.com")
    assert caplog.record_tuples == [
        ("kiss_cache.tasks", 20, "Fetching 'https://example.com'"),
        (
            "kiss_cache.tasks",
            40,
            "Resource db object does not exist for 'https://example.com'",
        ),
    ]

    # Unable to create the directoiry
    def raising_mkdir(path, mode, parents, exist_ok):
        assert str(path) == "/var/cache/kiss-cache/10"
        assert mode == 0o755
        assert parents is True
        assert exist_ok is True
        raise PermissionError("Permission denied")

    Resource.objects.create(url="https://example.com")
    mocker.patch("pathlib.Path.mkdir", raising_mkdir)
    fetch("https://example.com")
    assert (
        Resource.objects.get(url="https://example.com").state == Resource.STATE_FINISHED
    )
    assert Resource.objects.get(url="https://example.com").status_code == 500
    assert caplog.record_tuples == [
        ("kiss_cache.tasks", 20, "Fetching 'https://example.com'"),
        (
            "kiss_cache.tasks",
            40,
            "Resource db object does not exist for 'https://example.com'",
        ),
        ("kiss_cache.tasks", 20, "Fetching 'https://example.com'"),
        (
            "kiss_cache.tasks",
            40,
            "Unable to create the directory '/var/cache/kiss-cache/10/0680ad546ce6a577f42f52df33b4cfdca756859e664b8d7de329b150d09ce9'",
        ),
        ("kiss_cache.tasks", 40, "Permission denied"),
    ]


def test_fetch_errors_2(caplog, db, mocker, settings, tmpdir):
    caplog.set_level(logging.DEBUG)

    # Unable to download
    Resource.objects.create(url="https://example.com")
    settings.DOWNLOAD_PATH = str(tmpdir)

    class RequestRetry:
        def get(self, url, stream, headers, timeout):
            assert url == "https://example.com"
            assert stream is True
            assert headers == {
                "Accept-Encoding": "",
                "User-Agent": f"KissCache/{__version__}",
            }
            assert timeout == settings.DOWNLOAD_TIMEOUT
            raise requests.RequestException("Unable to download 'https://example.com'")

    def requests_retry():
        return RequestRetry()

    mocker.patch("kiss_cache.tasks.requests_retry", requests_retry)
    fetch("https://example.com")

    assert (
        Resource.objects.get(url="https://example.com").state == Resource.STATE_FINISHED
    )
    assert Resource.objects.get(url="https://example.com").status_code == 502
    assert caplog.record_tuples == [
        ("kiss_cache.tasks", 20, "Fetching 'https://example.com'"),
        ("kiss_cache.tasks", 40, "Unable to connect to 'https://example.com'"),
        ("kiss_cache.tasks", 40, "Unable to download 'https://example.com'"),
    ]


def test_fetch_errors_3(caplog, db, mocker, settings, tmpdir):
    caplog.set_level(logging.DEBUG)

    # Unable to download
    Resource.objects.create(url="https://example.com")
    settings.DOWNLOAD_PATH = str(tmpdir)

    class Response:
        status_code = 404

        def close(self):
            pass

    class RequestRetry:
        def get(self, url, stream, headers, timeout):
            assert url == "https://example.com"
            assert stream is True
            assert headers == {
                "Accept-Encoding": "",
                "User-Agent": f"KissCache/{__version__}",
            }
            assert timeout == settings.DOWNLOAD_TIMEOUT
            return Response()

    def requests_retry():
        return RequestRetry()

    mocker.patch("kiss_cache.tasks.requests_retry", requests_retry)
    fetch("https://example.com")

    assert (
        Resource.objects.get(url="https://example.com").state == Resource.STATE_FINISHED
    )
    assert Resource.objects.get(url="https://example.com").status_code == 404
    assert caplog.record_tuples == [
        ("kiss_cache.tasks", 20, "Fetching 'https://example.com'"),
        ("kiss_cache.tasks", 40, "'https://example.com' returned 404"),
    ]


def test_expire(caplog, db, mocker, settings, tmpdir):
    now = timezone.now()
    mocker.patch("django.utils.timezone.now", lambda: now)

    caplog.set_level(logging.DEBUG)
    settings.DOWNLOAD_PATH = str(tmpdir)
    settings.RESOURCE_QUOTA = 60

    res = Resource.objects.create(
        url="https://example.com/rootfs.xz", content_length=10, status_code=200
    )
    res.created_at = now - timedelta(days=1, seconds=1)
    res.save()

    res = Resource.objects.create(
        url="https://example.com/nfsrootfs.tar.gz",
        content_length=10,
        created_at=now - timedelta(days=1, seconds=1),
        state=Resource.STATE_FINISHED,
        status_code=200,
    )
    res.created_at = now - timedelta(days=1, seconds=1)
    res.save()

    Resource.objects.create(
        url="https://example.com/kernel",
        content_length=20,
        state=Resource.STATE_FINISHED,
        status_code=200,
    )

    Resource.objects.create(
        url="https://example.com/ramdisk",
        content_length=30,
        state=Resource.STATE_FINISHED,
        last_usage=now
        - timedelta(seconds=settings.RESOURCE_QUOTA_AUTO_CLEAN_DELAY + 10),
        status_code=200,
    )

    Resource.objects.create(
        url="https://example.com/rootfs.img.gz",
        content_length=40,
        state=Resource.STATE_FINISHED,
        status_code=200,
    )

    # A failed resource to drop
    Resource.objects.create(
        url="https://example.com/rootfs.img.bz2",
        content_length=40,
        state=Resource.STATE_FINISHED,
        status_code=404,
    )

    assert Resource.total_size() == 150
    expire()

    assert (
        Resource.objects.filter(url="https://example.com/nfsrootfs.tar.gz").count() == 0
    )
    assert Resource.objects.filter(url="https://example.com/ramdisk").count() == 0
    assert caplog.record_tuples == [
        ("kiss_cache.tasks", 20, "Removing failed resources"),
        ("kiss_cache.tasks", 20, "* 'https://example.com/rootfs.img.bz2'"),
        ("kiss_cache.tasks", 20, "Expiring resources"),
        ("kiss_cache.tasks", 20, "* 'https://example.com/nfsrootfs.tar.gz'"),
        ("kiss_cache.tasks", 20, "done"),
        ("kiss_cache.tasks", 20, "Checking quota usage"),
        (
            "kiss_cache.tasks",
            20,
            "* Cleaning by last usage (100\xa0bytes > 45\xa0bytes)",
        ),
        ("kiss_cache.tasks", 20, "  - 30\xa0bytes: 'https://example.com/ramdisk'"),
        ("kiss_cache.tasks", 20, "* No more resources to clean"),
        ("kiss_cache.tasks", 20, "* Usage: 70\xa0bytes"),
        ("kiss_cache.tasks", 20, "done"),
    ]
