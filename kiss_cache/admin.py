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
