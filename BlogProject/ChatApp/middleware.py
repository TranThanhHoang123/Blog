from channels.exceptions import DenyConnection
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from oauth2_provider.models import AccessToken
from channels.security.websocket import WebsocketDenier
from django.utils import timezone
from channels.db import database_sync_to_async
class TokenAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        headers = dict(scope['headers'])
        token = headers.get(b'authorization', None)
        if token:
            token = token.decode('utf-8').split(' ')[1]
            scope['user'] = await self.get_user_from_token(token)
            if scope['user'] == AnonymousUser():
                denier = WebsocketDenier()
                return await denier(scope, receive, send)
        else:
            denier = WebsocketDenier()
            return await denier(scope, receive, send)
        await super().__call__(scope, receive, send)

    @database_sync_to_async
    def get_user_from_token(self, token):
        access_token = AccessToken.objects.filter(token=token, expires__gt=timezone.now()).first()
        if access_token is None:
            return AnonymousUser()
        return access_token.user