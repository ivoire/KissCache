from django.apps import AppConfig


class KissCacheConfig(AppConfig):
    name = "kiss_cache"

    def ready(self):
        import kiss_cache.signals
