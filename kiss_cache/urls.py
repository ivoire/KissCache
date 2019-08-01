# -*- coding: utf-8 -*-
# vim: set ts=4

# Copyright 2018 Rémi Duraffort
# This file is part of KissCache.
#
# KissCache is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# KissCache is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with KissCache.  If not, see <http://www.gnu.org/licenses/>

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
        "resources/downloading/",
        views.resources,
        {"state": "downloading"},
        name="resources.downloading",
    ),
    path(
        "resources/successes/",
        views.resources,
        {"state": "successes"},
        name="resources",
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
    path("api/v1/fetch/", views.api_fetch, name="api.fetch"),
    path("api/v1/fetch/<str:filename>", views.api_fetch, name="api.fetch"),
]
