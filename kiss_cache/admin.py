from django.contrib import admin

from kiss_cache.models import Resource, Statistic


class ResourceAdmin(admin.ModelAdmin):
    list_display = ("url", "path", "state", "ttl", "usage")
    list_filter = ("state", "ttl")
    ordering = ["url"]

    def get_readonly_fields(self, _, obj=None):
        if obj:
            return self.readonly_fields + ("path", "url")
        return self.readonly_fields


class StatisticAdmin(admin.ModelAdmin):
    list_display = ("get_stat_display", "value")
    ordering = ["stat"]


admin.site.register(Resource, ResourceAdmin)
admin.site.register(Statistic, StatisticAdmin)
