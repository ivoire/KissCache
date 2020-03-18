# -*- coding: utf-8 -*-
# vim: set ts=4
#
# Copyright 2019 Linaro Limited
#
# Author: Rémi Duraffort <remi.duraffort@linaro.org>
#
# SPDX-License-Identifier: MIT

import logging
import requests

from kiss_cache.models import Resource, Statistic
from kiss_cache.tasks import fetch


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
            assert headers == {"Accept-Encoding": ""}
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
            assert headers == {"Accept-Encoding": ""}
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
            assert headers == {"Accept-Encoding": ""}
            assert timeout == settings.DOWNLOAD_TIMEOUT
            raise requests.RequestException("Unable to donwload 'https://example.com'")

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
        ("kiss_cache.tasks", 40, "Unable to donwload 'https://example.com'"),
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
            assert headers == {"Accept-Encoding": ""}
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
