"""
ASGI config for core project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""




import os
from django.core.asgi import get_asgi_application

# 1️⃣ Make sure Django settings are configured BEFORE anything else
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

# 2️⃣ Initialize Django ASGI application first (for ORM, models, staticfiles, etc.)
django_asgi_app = get_asgi_application()

# 3️⃣ Import channels dependencies AFTER Django is ready
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import chatapp.routing  # will now safely import consumers

# 4️⃣ Final ASGI application combining Django HTTP + WebSocket
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            chatapp.routing.websocket_urlpatterns
        )
    ),
})