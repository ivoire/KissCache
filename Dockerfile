FROM debian:buster-slim

LABEL maintainer="Rémi Duraffort <remi.duraffort@linaro.org>"

ENV DEBIAN_FRONTEND noninteractive

# Install dependencies
RUN apt-get update -q ;\
    apt-get install --no-install-recommends --yes gunicorn3 python3 python3-celery python3-pip python3-psycopg2 python3-redis python3-requests python3-yaml ;\
    python3 -m pip install --upgrade django whitenoise ;\
    # Cleanup
    apt-get clean ;\
    rm -rf /var/lib/apt/lists/*

# Add sources
WORKDIR /app/
COPY kiss_cache/ /app/kiss_cache/
# Create the django project
RUN useradd kiss-cache ;\
    mkdir /var/cache/kiss-cache/ ;\
    chown -R kiss-cache /var/cache/kiss-cache/ ;\
    chmod 775 /app ;\
    django-admin startproject website /app

COPY share/init.py /app/website/__init__.py
COPY share/celery.py /app/website/celery.py
COPY share/settings.py /app/website/custom_settings.py
COPY share/urls.py /app/website/urls.py

# Setup kiss_cache application
RUN echo "INSTALLED_APPS.append(\"kiss_cache\")" >> /app/website/settings.py ;\
    echo "from kiss_cache.settings import *" >> /app/website/settings.py ;\
    echo "from website.custom_settings import *" >> /app/website/settings.py ;\
    # Migrate and collect static files
    python3 manage.py collectstatic --noinput

COPY share/entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
