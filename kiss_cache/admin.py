from django.contrib import admin

from kiss_cache.models import Resource


class ResourceAdmin(admin.ModelAdmin):
    list_display = ("url", "filepath", "state", "ttl")
    list_filter = ("state", "ttl")
    ordering = ["url"]

    def filepath(self, obj):
        return "%s/%s" % (obj.path, obj.filename)

    def get_readonly_fields(self, _, obj=None):
        if obj:
            return self.readonly_fields + ("filename", "path", "url",)
        return self.readonly_fields

admin.site.register(Resource, ResourceAdmin)
