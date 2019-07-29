from django.urls import path

from kiss_cache import views


urlpatterns = [
    path("", views.index, name="home"),
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
    path("usage/", views.index, name="usage"),
    path("api/v1/fetch/", views.api_fetch, name="api.fetch"),
    path("api/v1/fetch/<str:filename>", views.api_fetch, name="api.fetch"),
]
