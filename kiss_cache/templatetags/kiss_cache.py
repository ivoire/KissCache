# -*- coding: utf-8 -*-
# vim: set ts=4
#
# Copyright 2020-present Linaro Limited
#
# Author: Rémi Duraffort <remi.duraffort@linaro.org>
#
# SPDX-License-Identifier: MIT

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def sort_icon(order, value):
    attribute = order[1:] if order[0] == "-" else order
    print(f"{attribute=}: {value=}")
    if attribute != value:
        print("a link")
        return mark_safe(f"""<a href="?order={value}"><i class="fas fa-sort-amount-up float-right"></i></a>""")

    if order[0] == "-":
        return mark_safe(f"""<a href="?order={value}"><i class="fas fa-sort-amount-down float-right"></i></a>""")
    else:
        return mark_safe(f"""<a href="?order=-{value}"><i class="fas fa-sort-amount-up-alt float-right"></i></a>""")
