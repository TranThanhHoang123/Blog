"""
ASGI config for BlogProject project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from ChatApp import routing,middleware
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BlogProject.settings')

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': middleware.TokenAuthMiddleware(
        URLRouter(
            routing.websocket_urlpatterns
        )
    ),
})
