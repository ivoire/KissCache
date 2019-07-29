from django.contrib import admin

from kiss_cache.models import Resource


class ResourceAdmin(admin.ModelAdmin):
    list_display = ("url", "path", "state", "ttl", "usage")
    list_filter = ("state", "ttl")
    ordering = ["url"]

    def get_readonly_fields(self, _, obj=None):
        if obj:
            return self.readonly_fields + ("path", "url")
        return self.readonly_fields


admin.site.register(Resource, ResourceAdmin)
