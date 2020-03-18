# -*- coding: utf-8 -*-
# vim: set ts=4
#
# Copyright 2019 Linaro Limited
#
# Author: Rémi Duraffort <remi.duraffort@linaro.org>
#
# SPDX-License-Identifier: MIT

from django.http import FileResponse
from django.http.response import StreamingHttpResponse
from django.urls import reverse
from django.utils import timezone

from kiss_cache.__about__ import __version__
from kiss_cache.models import Resource, Statistic


def test_index(client):
    ret = client.get(reverse("home"))
    assert len(ret.templates) == 2
    assert ret.templates[0].name == "kiss_cache/index.html"
    assert ret.templates[1].name == "kiss_cache/base.html"
    assert ret.context["api_url"] == "http://testserver/api/v1/fetch/"
    assert ret.context["version"] == __version__


def test_help(client):
    ret = client.get(reverse("help"))
    assert len(ret.templates) == 2
    assert ret.templates[0].name == "kiss_cache/help.html"
    assert ret.templates[1].name == "kiss_cache/base.html"
    assert ret.context["ALLOWED_NETWORKS"] == []
    assert ret.context["user_ip"] == "127.0.0.1"
    assert ret.context["user_ip_allowed"] == True
    assert ret.context["api_url"] == "http://testserver/api/v1/fetch/"


def test_statistics(client, db, settings):
    # Empty page
    ret = client.get(reverse("statistics"))
    assert len(ret.templates) == 2
    assert ret.templates[0].name == "kiss_cache/statistics.html"
    assert ret.templates[1].name == "kiss_cache/base.html"
    assert ret.context["total_size"] == 0
    assert ret.context["quota"] == settings.RESOURCE_QUOTA
    assert ret.context["progress"] == 0
    assert ret.context["progress_status"] == "success"
    assert ret.context["scheduled_count"] == 0
    assert ret.context["downloading_count"] == 0
    assert ret.context["successes_count"] == 0
    assert ret.context["failures_count"] == 0
    assert ret.context["download"] == 0
    assert ret.context["upload"] == 0

    # Create some resources
    MEGA = 1024 * 1024
    Resource.objects.create(url="http://example.com/1", state=Resource.STATE_SCHEDULED)
    Resource.objects.create(
        url="http://example.com/2",
        state=Resource.STATE_DOWNLOADING,
        content_length=111 * MEGA,
    )
    Resource.objects.create(
        url="http://example.com/3",
        state=Resource.STATE_FINISHED,
        status_code=200,
        content_length=222 * MEGA,
    )
    Resource.objects.create(
        url="http://example.com/4",
        state=Resource.STATE_FINISHED,
        status_code=504,
        content_length=333 * MEGA,
    )
    Statistic.objects.filter(stat=Statistic.STAT_DOWNLOAD).update(value=666 * MEGA)
    Statistic.objects.filter(stat=Statistic.STAT_UPLOAD).update(value=2 * 666 * MEGA)
    ret = client.get(reverse("statistics"))
    assert len(ret.templates) == 2
    assert ret.templates[0].name == "kiss_cache/statistics.html"
    assert ret.templates[1].name == "kiss_cache/base.html"
    assert ret.context["total_size"] == 666 * MEGA
    assert ret.context["quota"] == settings.RESOURCE_QUOTA
    assert ret.context["progress"] == 32
    assert ret.context["progress_status"] == "success"
    assert ret.context["scheduled_count"] == 1
    assert ret.context["downloading_count"] == 1
    assert ret.context["successes_count"] == 1
    assert ret.context["failures_count"] == 1
    assert ret.context["download"] == 666 * MEGA
    assert ret.context["upload"] == 2 * 666 * MEGA


def test_resources(client, db):
    # Empty page
    ret = client.get(reverse("resources.successes"))
    assert len(ret.templates) == 2
    assert ret.templates[0].name == "kiss_cache/resources.html"
    assert ret.templates[1].name == "kiss_cache/base.html"
    assert len(ret.context["resources"].object_list) == 0
    assert ret.context["resources"].number == 1
    assert ret.context["state"] == "successes"
    assert ret.context["url_name"] == "resources.successes"
    assert ret.context["scheduled_count"] == 0
    assert ret.context["downloading_count"] == 0
    assert ret.context["successes_count"] == 0
    assert ret.context["failures_count"] == 0

    # Create some resources
    MEGA = 1024 * 1024
    Resource.objects.create(url="http://example.com/1", state=Resource.STATE_SCHEDULED)
    Resource.objects.create(
        url="http://example.com/2",
        state=Resource.STATE_DOWNLOADING,
        content_length=111 * MEGA,
    )
    Resource.objects.create(
        url="http://example.com/3",
        state=Resource.STATE_FINISHED,
        status_code=200,
        content_length=222 * MEGA,
    )
    Resource.objects.create(
        url="http://example.com/4",
        state=Resource.STATE_FINISHED,
        status_code=504,
        content_length=333 * MEGA,
    )

    Statistic.objects.filter(stat=Statistic.STAT_DOWNLOAD).update(value=666 * MEGA)
    Statistic.objects.filter(stat=Statistic.STAT_UPLOAD).update(value=2 * 666 * MEGA)

    # Test each pages
    ret = client.get(reverse("resources.scheduled"))
    assert len(ret.templates) == 2
    assert ret.templates[0].name == "kiss_cache/resources.html"
    assert ret.templates[1].name == "kiss_cache/base.html"
    assert len(ret.context["resources"].object_list) == 1
    assert ret.context["resources"].object_list[0].url == "http://example.com/1"
    assert ret.context["resources"].number == 1
    assert ret.context["state"] == "scheduled"
    assert ret.context["url_name"] == "resources.scheduled"
    assert ret.context["scheduled_count"] == 1
    assert ret.context["downloading_count"] == 1
    assert ret.context["successes_count"] == 1
    assert ret.context["failures_count"] == 1

    ret = client.get(reverse("resources.downloading"))
    assert len(ret.templates) == 2
    assert ret.templates[0].name == "kiss_cache/resources.html"
    assert ret.templates[1].name == "kiss_cache/base.html"
    assert len(ret.context["resources"].object_list) == 1
    assert ret.context["resources"].object_list[0].url == "http://example.com/2"
    assert ret.context["resources"].number == 1
    assert ret.context["state"] == "downloading"
    assert ret.context["url_name"] == "resources.downloading"
    assert ret.context["scheduled_count"] == 1
    assert ret.context["downloading_count"] == 1
    assert ret.context["successes_count"] == 1
    assert ret.context["failures_count"] == 1

    ret = client.get(reverse("resources.successes"))
    assert len(ret.templates) == 2
    assert ret.templates[0].name == "kiss_cache/resources.html"
    assert ret.templates[1].name == "kiss_cache/base.html"
    assert len(ret.context["resources"].object_list) == 1
    assert ret.context["resources"].object_list[0].url == "http://example.com/3"
    assert ret.context["resources"].number == 1
    assert ret.context["state"] == "successes"
    assert ret.context["url_name"] == "resources.successes"
    assert ret.context["scheduled_count"] == 1
    assert ret.context["downloading_count"] == 1
    assert ret.context["successes_count"] == 1
    assert ret.context["failures_count"] == 1

    ret = client.get(reverse("resources.failures"))
    assert len(ret.templates) == 2
    assert ret.templates[0].name == "kiss_cache/resources.html"
    assert ret.templates[1].name == "kiss_cache/base.html"
    assert len(ret.context["resources"].object_list) == 1
    assert ret.context["resources"].object_list[0].url == "http://example.com/4"
    assert ret.context["resources"].number == 1
    assert ret.context["state"] == "failures"
    assert ret.context["url_name"] == "resources.failures"
    assert ret.context["scheduled_count"] == 1
    assert ret.context["downloading_count"] == 1
    assert ret.context["successes_count"] == 1
    assert ret.context["failures_count"] == 1


def test_api_health(client, mocker, settings, tmpdir):
    settings.SHUTDOWN_PATH = str(tmpdir / "shutdown")
    ret = client.get(reverse("api.health"))

    (tmpdir / "shutdown").write_text("", encoding="utf-8")
    ret = client.get(reverse("api.health"))
    assert ret.status_code == 503


def test_api_fetch(client, db, mocker, settings, tmpdir):
    URL = "https://example.com"

    def mocked_fetch(url):
        assert url == URL
        Resource.objects.filter(url=URL).update(
            state=Resource.STATE_FINISHED,
            status_code=200,
            content_length=12,
            content_type="text/html; charset=UTF-8",
        )
        path = Resource.objects.get(url=URL).path
        assert (
            path == "10/0680ad546ce6a577f42f52df33b4cfdca756859e664b8d7de329b150d09ce9"
        )
        (tmpdir / "10").mkdir()
        (
            tmpdir / "10/0680ad546ce6a577f42f52df33b4cfdca756859e664b8d7de329b150d09ce9"
        ).write_text("Hello world!", encoding="utf-8")

    settings.DOWNLOAD_PATH = str(tmpdir)

    fetch = mocker.patch("kiss_cache.tasks.fetch.delay", mocked_fetch)

    ret = client.get(f"{reverse('api.fetch')}?url={URL}&ttl=42d")
    assert isinstance(ret, FileResponse)
    assert ret._closable_objects[0].name == str(
        tmpdir / "10/0680ad546ce6a577f42f52df33b4cfdca756859e664b8d7de329b150d09ce9"
    )
    assert ret.status_code == 200
    assert ret._headers["content-type"] == ("Content-Type", "text/html; charset=UTF-8")
    assert ret._headers["content-length"] == ("Content-Length", "12")
    assert next(ret.streaming_content) == b"Hello world!"

    # Download a second time
    ret = client.get(f"{reverse('api.fetch')}?url={URL}&ttl=42d")
    assert isinstance(ret, FileResponse)
    assert ret._closable_objects[0].name == str(
        tmpdir / "10/0680ad546ce6a577f42f52df33b4cfdca756859e664b8d7de329b150d09ce9"
    )
    assert ret.status_code == 200
    assert ret._headers["content-type"] == ("Content-Type", "text/html; charset=UTF-8")
    assert ret._headers["content-length"] == ("Content-Length", "12")
    assert next(ret.streaming_content) == b"Hello world!"

    # Download a third time and set a shorter ttl
    now = timezone.now()
    mocker.patch("django.utils.timezone.now", lambda: now)
    ret = client.get(f"{reverse('api.fetch')}?url={URL}&ttl=4d")
    assert isinstance(ret, FileResponse)
    assert ret._closable_objects[0].name == str(
        tmpdir / "10/0680ad546ce6a577f42f52df33b4cfdca756859e664b8d7de329b150d09ce9"
    )
    assert ret.status_code == 200
    assert ret._headers["content-type"] == ("Content-Type", "text/html; charset=UTF-8")
    assert ret._headers["content-length"] == ("Content-Length", "12")
    assert next(ret.streaming_content) == b"Hello world!"
    assert Resource.objects.get(url=URL).ttl == 345_600


def test_api_fetch_streaming(client, db, mocker, settings, tmpdir):
    URL = "https://example.com"

    def mocked_fetch(url):
        assert url == URL
        Resource.objects.filter(url=URL).update(
            state=Resource.STATE_DOWNLOADING,
            status_code=200,
            content_length=12,
            content_type="text/html; charset=UTF-8",
        )
        path = Resource.objects.get(url=URL).path
        assert (
            path == "10/0680ad546ce6a577f42f52df33b4cfdca756859e664b8d7de329b150d09ce9"
        )
        (tmpdir / "10").mkdir()
        (
            tmpdir / "10/0680ad546ce6a577f42f52df33b4cfdca756859e664b8d7de329b150d09ce9"
        ).write_text("Hello world!", encoding="utf-8")

    settings.DOWNLOAD_PATH = str(tmpdir)

    fetch = mocker.patch("kiss_cache.tasks.fetch.delay", mocked_fetch)

    ret = client.get(f"{reverse('api.fetch')}?url={URL}&ttl=42d")
    assert isinstance(ret, StreamingHttpResponse)
    assert ret.status_code == 200
    assert ret._headers["content-type"] == ("Content-Type", "text/html; charset=UTF-8")
    assert ret._headers["content-length"] == ("Content-Length", "12")
    assert next(ret.streaming_content) == b"Hello world!"


def test_api_fetch_errors(client, db, mocker):
    URL = "https://example.com"

    #  missing url
    ret = client.get(reverse("api.fetch"))
    assert ret.status_code == 400

    # Invalid ttl format
    ret = client.get(f"{reverse('api.fetch')}?url={URL}&ttl=1k")
    assert ret.status_code == 400

    # Over quota
    mocker.patch("kiss_cache.models.Resource.is_over_quota", lambda: True)
    ret = client.get(f"{reverse('api.fetch')}?url={URL}")
    assert ret.status_code == 507
