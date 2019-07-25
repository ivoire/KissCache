FROM debian:buster-slim

LABEL maintainer="Rémi Duraffort <remi.duraffort@linaro.org>"

ENV DEBIAN_FRONTEND noninteractive

# Install dependencies
RUN apt-get update -q ;\
    apt-get install --no-install-recommends --yes gunicorn3 python3 python3-pip python3-psycopg2 python3-requests python3-yaml ;\
    python3 -m pip install --upgrade django whitenoise ;\
    # Cleanup
    apt-get clean ;\
    rm -rf /var/lib/apt/lists/*

# Add ReactOWeb sources
WORKDIR /app/
COPY kiss_cache/ /app/kiss_cache/
COPY share/settings.py /app/kiss_cache/custom_settings.py
COPY share/urls.py /app/kiss_cache/urls.py.orig

# Create and setup the Django project
RUN chmod 775 /app ;\
    django-admin startproject website /app ;\
    mv /app/kiss_cache/urls.py.orig /app/website/urls.py ;\
    # Setup lavafed application
    echo "INSTALLED_APPS.append(\"kiss_cache\")" >> /app/website/settings.py ;\
    echo "from kiss_cache.settings import *" >> /app/website/settings.py ;\
    echo "from kiss_cache.custom_settings import *" >> /app/website/settings.py ;\
    # Migrate and collect static files
    python3 manage.py collectstatic --noinput

COPY share/entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
