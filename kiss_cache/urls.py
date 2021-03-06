# -*- coding: utf-8 -*-
# vim: set ts=4
#
# Copyright 2019 Linaro Limited
#
# Author: Rémi Duraffort <remi.duraffort@linaro.org>
#
# SPDX-License-Identifier: MIT

from django.urls import path

from kiss_cache import views


urlpatterns = [
    path("", views.index, name="home"),
    path("help/", views.help, name="help"),
    path(
        "resources/scheduled/",
        views.resources,
        {"state": "scheduled"},
        name="resources.scheduled",
    ),
    path(
        "resources/scheduled/<int:page>/",
        views.resources,
        {"state": "scheduled"},
        name="resources.scheduled",
    ),
    path(
        "resources/downloading/",
        views.resources,
        {"state": "downloading"},
        name="resources.downloading",
    ),
    path(
        "resources/downloading/<int:page>/",
        views.resources,
        {"state": "downloading"},
        name="resources.downloading",
    ),
    path(
        "resources/successes/",
        views.resources,
        {"state": "successes"},
        name="resources.successes",
    ),
    path(
        "resources/successes/<int:page>/",
        views.resources,
        {"state": "successes"},
        name="resources.successes",
    ),
    path(
        "resources/failures/",
        views.resources,
        {"state": "failures"},
        name="resources.failures",
    ),
    path(
        "resources/failures/<int:page>/",
        views.resources,
        {"state": "failures"},
        name="resources.failures",
    ),
    path("statistics/", views.statistics, name="statistics"),
    path("api/v1/health/", views.api_health, name="api.health"),
    path("api/v1/fetch/", views.api_fetch, name="api.fetch"),
    path("api/v1/fetch/<str:filename>", views.api_fetch, name="api.fetch"),
    path("api/v1/status/", views.api_status, name="api.status"),
]
