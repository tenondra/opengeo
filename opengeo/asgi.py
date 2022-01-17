from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.urls import path

from opengeo.graphql_socket_consumer import MyGraphqlWsConsumer

# ASGI settings for the app

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AuthMiddlewareStack(
            URLRouter(
                [path("graphql", MyGraphqlWsConsumer.as_asgi())]
            )
        ),
    }
)