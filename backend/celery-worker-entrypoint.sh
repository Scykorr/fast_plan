#!/bin/sh
set -e

python manage.py migrate --noinput

exec celery -A config worker --loglevel=info
