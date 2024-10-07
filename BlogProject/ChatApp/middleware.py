from channels.exceptions import DenyConnection
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from oauth2_provider.models import AccessToken
from channels.security.websocket import WebsocketDenier
from django.utils import timezone
from channels.db import database_sync_to_async


class TokenAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        # Extract the token from the query parameters instead of headers
        query_string = scope.get('query_string', b'').decode('utf-8')
        token = self.get_token_from_query(query_string)

        if token:
            scope['user'] = await self.get_user_from_token(token)
            if scope['user'] == AnonymousUser():
                denier = WebsocketDenier()
                return await denier(scope, receive, send)
        else:
            denier = WebsocketDenier()
            return await denier(scope, receive, send)

        await super().__call__(scope, receive, send)

    def get_token_from_query(self, query_string):
        from urllib.parse import parse_qs
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]  # Get 'token' from query params
        return token

    @database_sync_to_async
    def get_user_from_token(self, token):
        access_token = AccessToken.objects.filter(token=token, expires__gt=timezone.now()).first()
        if access_token is None:
            return AnonymousUser()
        return access_token.user