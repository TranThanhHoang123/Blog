from rest_framework_mongoengine import serializers
from asgiref.sync import sync_to_async
from .models_mongo import Chat
from BlogApp.serializers import UserListSerializer
from BlogApp.models import User
from django.utils.functional import SimpleLazyObject
from rest_framework import serializers as serializer_django

class ChatSerializer(serializers.DocumentSerializer):
    class Meta:
        model = Chat
        fields = ['id', 'message', 'created_date', 'updated_date', 'user_id', 'group_id', 'metadata']


class ChatListSerializer(serializers.DocumentSerializer):

    class Meta:
        model = Chat
        fields = ['id', 'message', 'created_date', 'updated_date', 'group_id', 'metadata']

    def to_representation(self, obj):
        # Gọi phương thức to_representation của lớp cha để lấy dữ liệu cơ bản
        data = super().to_representation(obj)

        # Lấy đối tượng user từ User model dựa vào user_id
        try:
            user = User.objects.get(id=obj.user_id)
            data['user'] = UserListSerializer(user, context=self.context).data
        except User.DoesNotExist:
            data['user'] = None

        return data

class AsyncChatListSerializer(serializers.DocumentSerializer):
    class Meta:
        model = Chat
        fields = ['id', 'message', 'created_date', 'updated_date', 'group_id', 'metadata']

    async def to_representation(self, obj):
        data = super().to_representation(obj)

        try:
            user = await sync_to_async(User.objects.get)(id=obj.user_id)
            # Xử lý user data trực tiếp
            # Access the profile in an async-safe way
            profile = await sync_to_async(lambda: user.profile)()

            # Build the user data with profile
            data['user'] = {
                'id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'username': user.username,
                'profile': {
                    'profile_picture': self.context['request'].build_absolute_uri(
                        f"/static/{profile.profile_picture.name}") if profile.profile_picture else None,
                    'profile_background': self.context['request'].build_absolute_uri(
                        f"/static/{profile.profile_background.name}") if profile.profile_background else None,
                }
            }
        except User.DoesNotExist:
            data['user'] = None

        return data



class ChatUpdateSerializer(serializers.DocumentSerializer):
    class Meta:
        model = Chat
        fields = ['message', 'metadata']  # Chỉ cần các trường cần cập nhật
