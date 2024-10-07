from django.urls import path
from . import consumers
websocket_urlpatterns = [
    path('ws/chat/<int:id_group>/', consumers.ChatAsyncConsumer.as_asgi()),
    path('ws/chat/personal/<int:to_user_id>/', consumers.PersonalChatAsyncConsumer.as_asgi()),
]