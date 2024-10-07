from rest_framework_mongoengine import viewsets,generics
from rest_framework import permissions, status
from . import serializers,models_mongo,my_paginations,utils
from rest_framework.response import Response
from rest_framework.decorators import action
from BlogApp.models import User,GroupChat
from mongoengine.queryset.visitor import Q
from datetime import datetime

# Create your views here.
class ChatViewSet(viewsets.GenericViewSet,generics.UpdateAPIView,generics.ListAPIView):
    queryset = models_mongo.Chat.objects.all().order_by('-created_date')
    serializer_class = serializers.ChatUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = my_paginations.ChatPagination

    def get_queryset(self,request):
        query = self.queryset
        message = request.query_params.get('message')
        if message:
            if self.action in ['list']:
                query = query.filter(message__icontains=message)
        return query

    def get_serializer_class(self):
        if self.action in ['list','list_pinned']:
            return serializers.ChatListSerializer
        return self.serializer_class

    def list(self, request, *args, **kwargs):
        user= self.request.user
        # Lấy ID của group từ query params hoặc kwargs (tùy theo thiết kế)
        group_id = request.query_params.get('group_id')
        user_id = request.query_params.get('user_id')

        if not group_id and not user_id:
            return Response({'error': 'group_id or user_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if user_id:
            user_ids = sorted([user.id, int(user_id)])
            group_id = f"{user_ids[0]}_{user_ids[1]}"
            print(group_id)
        else:
            # Kiểm tra group chat có tồn tại hay không
            try:
                group = GroupChat.objects.get(id=group_id)
            except GroupChat.DoesNotExist:
                return Response({'error': 'Group not found.'}, status=status.HTTP_404_NOT_FOUND)

            # Kiểm tra xem user có phải thành viên của group chat không
            if not utils.is_user_in_group_sync(group, request.user):
                return Response({'error': 'You are not a member of this group.'}, status=status.HTTP_403_FORBIDDEN)
        print(group_id)
        # Lấy danh sách chat trong group
        queryset = self.get_queryset(request).filter(
            Q(group_id=group_id) & (Q(metadata__pin=False) | Q(metadata__pin__exists=False))
        )

        # Áp dụng pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='pin')
    def list_pinned(self, request, *args, **kwargs):
        """
        Phương thức này trả về danh sách tin nhắn được ghim (metadata 'ghim' = True).
        """
        group_id = request.query_params.get('group_id')
        if not group_id:
            return Response({'error': 'Group ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Kiểm tra group chat có tồn tại hay không
        try:
            group = GroupChat.objects.get(id=group_id)
        except GroupChat.DoesNotExist:
            return Response({'error': 'Group not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Kiểm tra quyền truy cập vào group chat
        if not utils.is_user_in_group_sync(group, request.user):
            return Response({'error': 'You are not a member of this group.'}, status=status.HTTP_403_FORBIDDEN)

        # Lọc danh sách tin nhắn được ghim (metadata 'pin' = True)
        pinned_queryset = self.get_queryset(request).filter(
            group_id=group_id, metadata__pin=True
        )

        # Áp dụng pagination cho danh sách tin nhắn ghim
        page = self.paginate_queryset(pinned_queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(pinned_queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        # Lấy ID của chat từ URL
        chat_id = kwargs.get('id')
        try:
            chat = models_mongo.Chat.objects.get(id=chat_id)
        except models_mongo.Chat.DoesNotExist:
            return Response({'error': 'Message not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Kiểm tra xem người dùng có phải là tác giả của chat không
        if str(chat.user_id) != str(request.user.id):
            return Response({'error': 'You dont have permissions to do this action.'}, status=status.HTTP_403_FORBIDDEN)

        # Kiểm tra trạng thái của chat
        if 'removed' in chat.metadata and chat.metadata['removed'] == True:
            return Response({'error': 'Message have been removed.'}, status=status.HTTP_400_BAD_REQUEST)

        # Nếu tất cả điều kiện đều hợp lệ, cập nhật chat
        serializer = self.get_serializer(chat, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        instance.updated_date = datetime.utcnow()

        return Response(serializers.ChatSerializer(instance).data, status=status.HTTP_200_OK)

