from django.urls import path

from kiss_cache import views


urlpatterns = [
    path("", views.index, name="home"),
    path("resources/", views.resources, name="resources"),
    path("usage/", views.index, name="usage"),
    path("api/v1/fetch/<str:filename>/", views.api_fetch, name="api.fetch"),
]
