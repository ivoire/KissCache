from django.urls import path

from kiss_cache import views


urlpatterns = [
    path("api/v1/fetch/<str:filename>/", views.api_fetch),
]
