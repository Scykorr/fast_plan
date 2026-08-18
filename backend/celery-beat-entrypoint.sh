#!/bin/sh
set -e

python manage.py migrate --noinput

exec celery -A config beat --loglevel=info
