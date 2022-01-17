import channels
import channels.auth
import channels_graphql_ws
from graphql_jwt import Verify
from graphql_jwt.middleware import JSONWebTokenMiddleware

from opengeo.schema.schema import schema


def authentication_middleware(next_middleware, root, info, *args, **kwds):
    """
    CURRENT UNUSED, REPLACED WITH JSONWebTokenMiddleware
    Middleware for JWT authentication
    """
    # Skip Graphiql introspection requests, there are a lot.
    if (
            info.operation.name is not None
            and info.operation.name.value != "IntrospectionQuery"
    ):
        info.context.COOKIES = info.context.cookies
        # Authenticate user from the request
        Verify.verify(root, info, None)
    return next_middleware(root, info, *args, **kwds)


class MyGraphqlWsConsumer(channels_graphql_ws.GraphqlWsConsumer):
    """Channels WebSocket consumer which provides GraphQL API."""

    async def on_connect(self, payload):
        """Handle WebSocket connection event."""

        # Use auxiliary Channels function `get_user` to replace an
        # instance of `channels.auth.UserLazyObject` with a native
        # Django user object (user model instance or `AnonymousUser`)
        # It is not necessary, but it helps to keep resolver code
        # simpler. Cause in both HTTP/WebSocket requests they can use
        # `info.context.user`, but not a wrapper. For example objects of
        # type Graphene Django type `DjangoObjectType` does not accept
        # `channels.auth.UserLazyObject` instances.
        # https://github.com/datadvance/DjangoChannelsGraphqlWs/issues/23
        self.scope["user"] = await channels.auth.get_user(self.scope)

    schema = schema
    jwt_middleware = JSONWebTokenMiddleware()
    middleware = [jwt_middleware.resolve]
