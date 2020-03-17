# -*- coding: utf-8 -*-
# vim: set ts=4
#
# Copyright 2019 Linaro Limited
#
# Author: Rémi Duraffort <remi.duraffort@linaro.org>
#
# SPDX-License-Identifier: MIT

import pytest

import kiss_cache
from kiss_cache.utils import get_user_ip, is_client_allowed


class Request:
    def __init__(self, meta):
        self.META = meta


def test_get_user_ip():
    request = Request({"HTTP_X_FORWARDED_FOR": "127.0.0.1"})
    assert get_user_ip(request) == "127.0.0.1"

    request = Request({"HTTP_X_FORWARDED_FOR": "127.0.0.1,17.0.1.4"})
    assert get_user_ip(request) == "127.0.0.1"

    request = Request({"REMOTE_ADDR": "127.0.0.1"})
    assert get_user_ip(request) == "127.0.0.1"
    with pytest.raises(Exception, match="Unable to get the user ip"):
        get_user_ip(Request({}))


def test_is_client_allowed(monkeypatch, settings):
    settings.ALLOWED_NETWORKS = []
    assert is_client_allowed(None) is True

    monkeypatch.setattr(kiss_cache.utils, "get_user_ip", lambda r: "127.0.0.1")

    settings.ALLOWED_NETWORKS = ["127.0.0.1"]
    assert is_client_allowed(None) is True

    settings.ALLOWED_NETWORKS = ["127.0.0.0"]
    assert is_client_allowed(None) is False

    settings.ALLOWED_NETWORKS = ["127.0.0.0/30"]
    assert is_client_allowed(None) is True

    settings.ALLOWED_NETWORKS = ["192.168.0.0/16", "127.0.0.0/30"]
    assert is_client_allowed(None) is True
