from django.shortcuts import render
from oauth2_provider.models import Application, AccessToken, RefreshToken
from rest_framework import viewsets, generics, status, permissions
from django.db.models import Q
from rest_framework.response import Response
from . import serializers, my_paginations, my_generics
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from .utils import *
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from oauth2_provider.views import TokenView
from rest_framework.decorators import api_view, permission_classes
from django.utils import timezone
from datetime import timedelta
from rest_framework.permissions import AllowAny
from oauth2_provider.settings import oauth2_settings
import json
import uuid
from rest_framework import status
from .models import *


# Create your views here.
class CustomTokenView(TokenView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            data = json.loads(response.content)
            refresh_token = data.get('refresh_token')
            response.set_cookie(
                key='refresh_token',
                value=refresh_token,
                expires=settings.OAUTH2_PROVIDER['REFRESH_TOKEN_EXPIRE_SECONDS'],
                secure=False,
                httponly=True,
                samesite='Lax'
            )
        return response


@api_view(['POST'])
@permission_classes([AllowAny])
def custom_refresh_token(request):
    refresh_token = request.COOKIES.get('refresh_token')
    client_id = request.data.get('client_id')
    client_secret = request.data.get('client_secret')

    if not refresh_token:
        return JsonResponse({'error': 'No refresh token provided'}, status=400)

    if not client_id or not client_secret:
        return JsonResponse({'error': 'Client ID and client secret required'}, status=400)

    try:
        application = Application.objects.get(client_id=client_id)
    except Application.DoesNotExist:
        return JsonResponse({'error': 'Invalid client credentials'}, status=400)

    # So sánh client_secret đã mã hóa
    if not check_client_secret(application.client_secret, client_secret):
        return JsonResponse({'error': 'Invalid client credentials'}, status=400)

    try:
        token = RefreshToken.objects.get(token=refresh_token, application=application)
    except RefreshToken.DoesNotExist:
        return JsonResponse({'error': 'Invalid refresh token'}, status=400)

        # Tính toán thời gian hết hạn của refresh token
        token_expires_at = token.updated + timedelta(seconds=OAUTH2_PROVIDER['REFRESH_TOKEN_EXPIRE_SECONDS'])

        # Kiểm tra thời gian hết hạn
        if timezone.now() > token_expires_at:
            return JsonResponse({'error': 'Refresh token expired'}, status=400)

    user = token.user

    # Tạo token ngẫu nhiên
    new_access_token = uuid.uuid4().hex

    # Lưu access token mới vào cơ sở dữ liệu
    new_access_token_obj = AccessToken.objects.create(
        user=user,
        application=application,
        token=new_access_token,
        expires=timezone.now() + timedelta(seconds=oauth2_settings.ACCESS_TOKEN_EXPIRE_SECONDS),
    )

    response_data = {
        'access_token': new_access_token_obj.token,
        'expires_in': oauth2_settings.ACCESS_TOKEN_EXPIRE_SECONDS
    }

    return JsonResponse(response_data)


class UserViewSet(viewsets.ViewSet, generics.CreateAPIView, generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = serializers.UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = my_paginations.UserPagination
    parser_classes = [FormParser, MultiPartParser]

    def get_permissions(self):
        if self.action in ['create']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action in ['retrieve']:
            return serializers.UserDetailSerializer
        return self.serializer_class

    def get_object(self):
        return self.request.user

    @action(detail=False, methods=['patch'], url_path='update-profile')
    def update_profile(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = serializers.UserUpdateSerializer(user, data=request.data, partial=True,
                                                      context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Profile updated successfully'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='details')
    def retrieve_user(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = serializers.UserDetailSerializer(user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        user_id = kwargs.get('pk')  # Lấy ID từ URL
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = serializers.UserDetailSerializer(user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='blog', permission_classes=[permissions.IsAuthenticated])
    def my_blogs(self, request, pk=None):
        user = request.user
        if pk == str(user.id):
            blogs = Blog.objects.filter(user=user).order_by('-created_date')
        else:
            blogs = Blog.objects.filter(user_id=pk, visibility='public').order_by('-created_date')

        paginator = my_paginations.BlogPagination()
        result_page = paginator.paginate_queryset(blogs, request)
        serializer = serializers.BlogDetailSerializer(result_page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)


class BlogViewSet(viewsets.ViewSet, generics.RetrieveAPIView, generics.ListAPIView):
    queryset = Blog.objects.all().order_by('-created_date')
    serializer_class = serializers.BlogSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    pagination_class = my_paginations.BlogPagination

    def get_queryset(self):
        if self.action in ['list']:
            queryset = Blog.objects.filter(visibility='public').order_by('-created_date')
            return queryset

    def get_permissions(self):
        if self.action in ['list']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action in ['list']:
            return serializers.BlogDetailSerializer
        return self.serializer_class

    def retrieve(self, request, pk=None):
        blog = get_object_or_404(Blog, pk=pk)
        # Check for private blog visibility
        if blog.visibility == 'private' and blog.user != request.user:
            return Response({'detail': 'You do not have permission to view this blog.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = serializers.BlogDetailWithCommentsSerializer(instance=blog, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        user = request.user
        content = request.data.get('content')
        description = request.data.get('description')
        visibility = request.data.get('visibility')
        medias = request.FILES.getlist('media')

        # Validate and create blog instance
        blog = Blog.objects.create(
            user=user,
            content=content,
            description=description,
            visibility=visibility
        )

        # Handle media files
        for file in medias:
            BlogMedia.objects.create(blog=blog, file=file)

        # Serialize the response data
        serializer = serializers.BlogDetailSerializer(blog, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        blog = get_object_or_404(Blog, pk=pk, user=request.user)
        serializer = self.get_serializer(blog, data=request.data, partial=True)
        if serializer.is_valid():
            updated_blog = serializer.save()
            new_media = request.FILES.getlist('media')
            if new_media:
                for file in new_media:
                    BlogMedia.objects.create(blog=updated_blog, file=file)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        blog = get_object_or_404(Blog, pk=pk, user=request.user)
        blog.delete()  # Xóa comment và tệp tin đính kèm
        return Response({'message': 'Blog deleted successfully'}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete', 'get'], url_path='like')
    def like(self, request, pk=None):
        blog = get_object_or_404(Blog, pk=pk)
        user = request.user

        if request.method == 'POST':
            if blog.visibility == 'private' and blog.user != user:
                return Response({'detail': 'You can only like your own private posts.'},
                                status=status.HTTP_403_FORBIDDEN)
            if Like.objects.filter(blog=blog, user=user).exists():
                return Response({"detail": "You have already liked this blog."}, status=status.HTTP_400_BAD_REQUEST)
            Like.objects.create(blog=blog, user=user)
            blog.likes_count += 1
            blog.save()
            return Response({"detail": "Blog liked successfully."}, status=status.HTTP_200_OK)

        elif request.method == 'DELETE':
            if blog.visibility == 'private' and blog.user != user:
                return Response({'detail': 'You can only dislike your own private posts.'},
                                status=status.HTTP_403_FORBIDDEN)
            like = get_object_or_404(Like, blog=blog, user=user)
            like.delete()
            blog.likes_count -= 1
            blog.save()
            return Response({"detail": "Blog unliked successfully."}, status=status.HTTP_200_OK)

        if blog.visibility == 'private' and blog.user != user:
            return Response({'detail': 'You are not authorized to view likes for this post.'},
                            status=status.HTTP_403_FORBIDDEN)

        elif request.method == 'GET':
            likes = Like.objects.filter(blog=blog).order_by('-created_date')
            paginator = my_paginations.LikePagination()
            paginator.page_size = 10  # Số lượng người dùng trên mỗi trang
            result_page = paginator.paginate_queryset(likes, request)
            serializer = serializers.UserListSerializer([like.user for like in result_page], many=True,
                                                        context={'request': request})

            return paginator.get_paginated_response(serializer.data)

    @action(detail=True, methods=['post', 'get'], url_path='comment')
    def add_comment(self, request, pk=None):
        blog = get_object_or_404(Blog, pk=pk)
        user = request.user

        # Kiểm tra quyền truy cập dựa vào visibility
        if blog.visibility == 'private' and blog.user != user:
            return Response({'detail': 'You do not have permission to view or add comments to this blog.'},
                            status=status.HTTP_403_FORBIDDEN)

        if request.method == 'POST':
            data = request.data.copy()
            data['blog'] = blog.id
            parent_id = data.get('parent')
            if parent_id:
                parent_comment = get_object_or_404(Comment, id=parent_id)
                data['parent'] = parent_comment.id

            serializer = serializers.CommentSerializer(data=data, context={'request': request})

            if serializer.is_valid():
                serializer.save(user=user)
                blog.comments_count += 1
                blog.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        elif request.method == 'GET':
            comments = Comment.objects.filter(blog=blog).order_by('-created_date')

            paginator = my_paginations.CommentPagination()

            result_page = paginator.paginate_queryset(comments, request)

            serializer = serializers.CommentListSerializer(result_page, many=True, context={'request': request})

            return paginator.get_paginated_response(serializer.data)


class CommentViewSet(viewsets.ViewSet,generics.UpdateAPIView,generics.DestroyAPIView):
    queryset = Comment.objects.all().order_by('-created_date')
    serializer_class = serializers.CommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def update(self, request, *args, **kwargs):
        comment = self.get_object()

        # Kiểm tra quyền chỉnh sửa
        if comment.user != request.user:
            return Response({'detail': 'You do not have permission to edit this comment.'},
                            status=status.HTTP_403_FORBIDDEN)

        # Loại bỏ trường 'parent' khỏi dữ liệu gửi đến
        data = request.data.copy()
        if 'parent' in data:
            data.pop('parent')

        partial = True
        serializer = self.get_serializer(comment, data=data, partial=partial)

        if serializer.is_valid():
            old_file = comment.file
            updated_comment = serializer.save()

            # Xóa file cũ nếu có file mới được cập nhật
            if old_file and old_file != updated_comment.file:
                old_file.delete(save=False)

            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        comment = self.get_object()
        blog = comment.blog
        response = super().destroy(request, *args, **kwargs)
        blog.comments_count -= 1
        blog.save()
        return Response({"message":"Comment deleted successfully"},status=status.HTTP_204_NO_CONTENT)
