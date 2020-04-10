# -*- coding: utf-8 -*-
# vim: set ts=4
#
# Copyright 2019 Linaro Limited
#
# Author: Rémi Duraffort <remi.duraffort@linaro.org>
#
# SPDX-License-Identifier: MIT

import pytest
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from django.http import HttpResponseForbidden

import kiss_cache
from kiss_cache.utils import (
    check_client_ip,
    get_user_ip,
    is_client_allowed,
    requests_retry,
)


class Request:
    def __init__(self, meta):
        self.META = meta


def test_check_client_ip(settings):
    @check_client_ip
    def func(request):
        return True

    settings.ALLOWED_NETWORKS = ["127.0.0.1"]
    assert func(Request({"HTTP_X_FORWARDED_FOR": "127.0.0.1"})) is True
    assert isinstance(
        func(Request({"HTTP_X_FORWARDED_FOR": "192.168.0.12"})), HttpResponseForbidden
    )


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


def test_requests_retry(settings):
    rr = requests_retry()
    assert isinstance(rr, requests.Session)
    assert isinstance(rr.adapters["http://"], HTTPAdapter)
    assert rr.adapters["https://"] is rr.adapters["http://"]
    assert isinstance(rr.adapters["http://"].max_retries, Retry)
    r = rr.adapters["http://"].max_retries
    assert r.total == settings.DOWNLOAD_RETRY
    assert r.read == settings.DOWNLOAD_RETRY
    assert r.connect == settings.DOWNLOAD_RETRY
    assert r.status == settings.DOWNLOAD_RETRY
    assert r.backoff_factor == settings.DOWNLOAD_BACKOFF_FACTOR
