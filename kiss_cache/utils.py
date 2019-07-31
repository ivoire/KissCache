from functools import wraps
import ipaddress
import requests

from django.conf import settings
from django.http import HttpResponseForbidden
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


def is_client_allowed(request):
    # If ALLOWED_NETWORKS is empty: accept every clients
    if not settings.ALLOWED_NETWORKS:
        return True
    # Filter the clients
    if "HTTP_X_FORWARDED_FOR" not in request.META:
        raise Exception("Missing X-Forwarded-For header")
    client_ip = ipaddress.ip_address(request.META["HTTP_X_FORWARDED_FOR"])
    for rule in settings.ALLOWED_NETWORKS:
        if client_ip in ipaddress.ip_network(rule):
            return True
    # Nothing matching: access is denied
    return False


def check_client_ip(func):
    @wraps(func)
    def inner(request, *args, **kwargs):
        if is_client_allowed(request):
            return func(request, *args, **kwargs)
        # Nothing matching: access is denied
        return HttpResponseForbidden()

    return inner


def requests_retry():
    session = requests.Session()
    retries = 5
    backoff_factor = 0.5
    retry = Retry(
        total=retries, read=retries, connect=retries, backoff_factor=backoff_factor
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session
