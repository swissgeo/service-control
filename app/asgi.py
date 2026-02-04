"""
ASGI config for project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

from os import environ

from django.core.asgi import get_asgi_application

from utils.otel import initialize_tracing

environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = initialize_tracing(get_asgi_application())
