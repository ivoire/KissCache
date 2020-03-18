# -*- coding: utf-8 -*-
# vim: set ts=4
#
# Copyright 2019 Linaro Limited
#
# Author: Rémi Duraffort <remi.duraffort@linaro.org>
#
# SPDX-License-Identifier: MIT

from django.urls import reverse

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


def test_api_health(client, settings, tmpdir):
    settings.SHUTDOWN_PATH = str(tmpdir / "shutdown")
    ret = client.get(reverse("api.health"))

    (tmpdir / "shutdown").write_text("", encoding="utf-8")
    ret = client.get(reverse("api.health"))
    assert ret.status_code == 503
