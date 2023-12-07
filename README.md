KissCache
=========

KissCache is a simple and stupid caching server.

Features
========

KissCache is able to:

* fetch and cache remote resources over http and https
* stream back the content to the clients
* automatically remove old resources
* restrict the api to specific sub-networks
* record usage statistics
* set and enforce a quota

In a near future, KissCache will be able to:

* automatically re-fetch selected resources
* ...


Using KissCache
===============

Installing
----------

KissCache is providing a docker-compose that will start the required services:

    git clone https://gitlab.com/linaro/kisscache
    make

The frontend will be available at http://localhost:8001/

Configuration
-------------

The configuration file is a YAML dictionary in **share/kiss-cache.yaml**.

You can set every *Django* and *Celery* variables in this configuration files.

The default KissCache variables are:

* *DOWNLOAD_TIMEOUT*
* *DOWNLOAD_PATH*
* *DOWNLOAD_CHUNK_SIZE*
* *DEFAULT_TTL*
* *ALLOWED_NETWORKS*

See **kiss_cache/settings.py** for the full list of variables.

Usage
-----

In order to use KissCache, users should prefix the resources's URLs by the KissCache URL.

In order to cache **https://example.com/kernel** with a local KissCache instance, the user should access to:

    http://localhost:8001/api/v1/fetch/?url=https://example.com/kernel

Debugging Django errors
-----------------------

If the KissCache is returning an error (500), you can activate the debug traces
by adding **DEBUG=1** to the environment of the **web** service in the
docker-compose configuration.
