from django.shortcuts import render
from django.utils.crypto import get_random_string
from oauth2_provider.models import Application, AccessToken, RefreshToken
from rest_framework import viewsets, generics, status, permissions
from django.db.models import Q
from rest_framework.response import Response
from . import serializers, my_paginations, my_generics,filters,utils
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
from django.contrib.auth.models import Group, Permission
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction

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


class UserViewSet(viewsets.ViewSet, generics.CreateAPIView, generics.RetrieveAPIView, generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = serializers.UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = my_paginations.UserPagination
    parser_classes = [FormParser, MultiPartParser]
    filterset_class = filters.UserFilterBase
    filter_backends = [DjangoFilterBackend]
    # Thêm filter_backends và filterset_fields
    def get_permissions(self):
        if self.action in ['create','list','blog']:
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
    def retrieve_user(self, request):
        user = self.get_object()
        serializer = serializers.UserDetailSerializer(user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='job-applications')
    def job_applications(self, request, pk=None):
        user = request.user
        # người dung của blog
        job_application = JobApplication.objects.filter(user=user).order_by('-created_date')
        paginator = my_paginations.JobApplicationPagination()
        result_page = paginator.paginate_queryset(job_application, request)
        serializer = serializers.JobApplicationListSerializer(result_page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        user_id = kwargs.get('pk')  # Lấy ID từ URL
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = serializers.UserDetailSerializer(user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='blog', permission_classes=[permissions.IsAuthenticated])
    def blog(self, request, pk=None):
        #người dung của blog
        user_blog = User.objects.get(pk=pk)
        blogs = utils.get_blog_list_of_user(user_blog=user_blog,user=request.user)
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
            queryset = utils.get_blog_list(self.request.user)
            return queryset

    def get_permissions(self):
        if self.action in ['list','retrieve']:
            return [permissions.AllowAny()]
        if self.action in ['comment'] and self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action in ['list']:
            return serializers.BlogDetailSerializer
        return self.serializer_class

    def retrieve(self, request, pk=None):
        user = request.user
        blog = utils.get_blog_details(pk, user)
        if blog:
            # Check for private blog visibility
            if blog.visibility == 'private' and blog.user != user:
                return Response({'detail': 'You do not have permission to view this blog.'}, status=status.HTTP_403_FORBIDDEN)
            serializer = serializers.BlogDetailSerializer(blog, context={'request': request})
            return Response(serializer.data)
        return Response({'detail': 'Blog not found'}, status=status.HTTP_404_NOT_FOUND)


    with transaction.atomic():
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
            serializer = serializers.BlogSerializer(blog, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        blog = get_object_or_404(Blog, pk=pk, user=request.user)
        if request.user != blog.user:
            return Response({"detail": "You do not have permission to update this blog."},
                            status=status.HTTP_403_FORBIDDEN)
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
        if request.user != blog.user:
            return Response({"detail": "You do not have permission to delete this blog."},
                            status=status.HTTP_403_FORBIDDEN)

        blog.delete()  # Xóa comment và tệp tin đính kèm
        return Response(status=status.HTTP_204_NO_CONTENT)

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
            return Response({"detail": "Blog liked successfully."}, status=status.HTTP_200_OK)

        elif request.method == 'DELETE':
            if blog.visibility == 'private' and blog.user != user:
                return Response({'detail': 'You can only dislike your own private posts.'},
                                status=status.HTTP_403_FORBIDDEN)
            like = get_object_or_404(Like, blog=blog, user=user)
            like.delete()
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
    def comment(self, request, pk=None):
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
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        elif request.method == 'GET':
            comments = Comment.objects.filter(blog=blog,parent=None).order_by('-created_date')

            paginator = my_paginations.CommentPagination()

            result_page = paginator.paginate_queryset(comments, request)

            serializer = serializers.CommentListSerializer(result_page, many=True, context={'request': request})

            return paginator.get_paginated_response(serializer.data)


class CommentViewSet(viewsets.ViewSet,generics.UpdateAPIView,generics.DestroyAPIView):
    queryset = Comment.objects.all().order_by('-created_date')
    serializer_class = serializers.CommentSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = my_paginations.CommentPagination
    def get_permissions(self):
        if self.action in ['get_replies']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]
    @action(detail=True, methods=['get'], url_path='replies')
    def get_replies(self, request, pk=None):
        # Lấy comment cha dựa trên ID
        parent_comment = self.get_object()

        # Lấy danh sách các replies của comment cha
        replies = parent_comment.replies.all().order_by('-created_date')

        # Sử dụng pagination nếu cần
        page = self.paginate_queryset(replies)
        if page is not None:
            serializer = serializers.CommentListSerializer(page, many=True,context={'request': request})
            return self.get_paginated_response(serializer.data)
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
        if comment.user != request.user:
            return Response({'detail': 'You do not have permission to edit this comment.'},
                            status=status.HTTP_403_FORBIDDEN)
        comment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class JobApplicationViewSet(viewsets.ViewSet, generics.UpdateAPIView, generics.DestroyAPIView):
    queryset = JobApplication.objects.all().order_by('-created_date')
    serializer_class = serializers.JobApplicationSerializer

    # def update(self, request, *args, **kwargs):
    #     job_application = self.get_object()
    #     # Kiểm tra xem người dùng hiện tại có phải là người đã tạo ra JobApplication không
    #     if request.user != job_application.user:
    #         return Response({"detail": "You do not have permission to update this job application."},
    #                         status=status.HTTP_403_FORBIDDEN)
    #     serializer = serializers.JobApplicationSerializer(job_application, data=request.data, partial=True)
    #     if serializer.is_valid():
    #         serializer.save()
    #         return Response({"detail": "Job application updated successfully."},status=status.HTTP_200_OK)
    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    #
    # def destroy(self, request, pk=None):
    #     job_application = self.get_object()
    #     # Kiểm tra xem người dùng hiện tại có phải là người đã tạo ra JobApplication không
    #     if request.user != job_application.user:
    #         return Response({"detail": "You do not have permission to delete this job application."},
    #                         status=status.HTTP_403_FORBIDDEN)
    #     job_application.delete()
    #     return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['patch'], url_path='status')
    def update_status(self, request, pk=None):
        job_application = self.get_object()
        new_status = request.data.get('status')
        # Kiểm tra quyền chỉnh sửa: Chỉ cho phép người tạo bài đăng sửa đổi nó
        if job_application.job_post.user != request.user:
            return Response({'detail': 'You do not have permission to change status this job application.'},
                            status=status.HTTP_403_FORBIDDEN)
        if new_status not in dict(JobApplication.STATUS_CHOICES).keys():
            return Response({"error": "Invalid status value."}, status=status.HTTP_400_BAD_REQUEST)

        job_application.status = new_status
        job_application.save()

        serializer = serializers.JobApplicationDetailSerializer(job_application, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

class ChangePasswordViewSet(viewsets.ViewSet):
    queryset = User.objects.all()
    serializer_class = serializers.ChangePasswordSerializer
    def get_permissions(self):
        if self.action in ['reset_password','verify_code']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]
    @action(detail=False, methods=['patch'], url_path='change-password')
    def change_password(self, request, pk=None):
        serializer = serializers.ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({"message": "Password updated successfully"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='reset-password')
    def reset_password(self, request):
        serializer = serializers.PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        user = User.objects.get(email=email)
        code = get_random_string(length=6, allowed_chars='0123456789')

        try:
            reset_code = PasswordResetCode.objects.get(user=user)
            if not reset_code.is_expired():
                return Response({"error": "Already sent verify code"}, status=status.HTTP_400_BAD_REQUEST)
        except PasswordResetCode.DoesNotExist:
            reset_code = PasswordResetCode(user=user)

        reset_code.code = code
        reset_code.expires_at = timezone.now() + timedelta(minutes=3)
        reset_code.status = False
        reset_code.save()

        send_verification_email(email,'Mã xác nhận đổi mật khẩu',f'Đây là mã xác nhận của bạn: {code}'
                                                                 f'\n MÃ HIỆU LỰC NÀY CÓ TÁC DỤNG TRONG 3 PHÚT!')

        return Response({"message": "Verification code sent to your email"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='verify-code')
    def verify_code(self, request):
        serializer = serializers.VerifyCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.get(email=serializer.validated_data['email'])
        reset_code = PasswordResetCode.objects.get(user=user, code=serializer.validated_data['code'])

        if reset_code.is_expired():
            return Response({"error": "Verification code expired"}, status=status.HTTP_400_BAD_REQUEST)

        if reset_code.status:
            return Response({"error": "Verification code already used"}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(serializer.validated_data['new_password'])
        user.save()

        reset_code.status = True
        reset_code.save()

        return Response({"message": "Password has been updated successfully"}, status=status.HTTP_200_OK)




class JobPostViewSet(viewsets.ViewSet,generics.ListAPIView,generics.RetrieveAPIView,generics.UpdateAPIView,generics.CreateAPIView,generics.DestroyAPIView):
    queryset = JobPost.objects.all()
    serializer_class = serializers.JobPostSerializer
    pagination_class = my_paginations.JobPostPagination
    permission_classes = [permissions.IsAuthenticated]  # Yêu cầu người dùng phải đăng nhập

    def get_permissions(self):
        if self.action in ['list','retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self, *args, **kwargs):
        if self.action in ['retrieve']:
            return serializers.JobPostDetailSerializer
        elif self.action in ['list']:
            return serializers.JobPostListSerializer
        return self.serializer_class

    def update(self, request, *args, **kwargs):
        job_post = self.get_object()

        # Kiểm tra quyền chỉnh sửa: Chỉ cho phép người tạo bài đăng sửa đổi nó
        if job_post.user != request.user:
            return Response({'detail': 'You do not have permission to edit this job post.'},
                            status=status.HTTP_403_FORBIDDEN)

        # Loại bỏ trường không cho phép chỉnh sửa nếu cần
        data = request.data.copy()
        if 'user' in data:  # Không cho phép chỉnh sửa người dùng
            data.pop('user')

        partial = True  # Cho phép cập nhật một phần
        serializer = self.get_serializer(job_post, data=data, partial=partial)

        if serializer.is_valid():
            updated_job_post = serializer.save()  # Lưu các thay đổi
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request):
        user = request.user

        data = request.data.copy()
        data['user'] = user.id  # Gán user hiện tại vào dữ liệu

        serializer = serializers.JobPostSerializer(data=data)

        if serializer.is_valid():
            instance = serializer.save(user=user)
            return Response(serializers.JobPostDetailSerializer(instance,context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post','get'], url_path='job-applications')
    def add_job_application(self, request, pk=None):
        job_post = self.get_object()
        user = request.user
        if request.method == 'POST':
            serializer = serializers.JobApplicationSerializer(data=request.data)
            if serializer.is_valid():
                # Lưu đơn xin việc với công ty và người dùng hiện tại
                instance = serializer.save(job_post=job_post, user=user, status='pending')
                return Response({'detail':"Job application created successfully."},
                                status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        elif request.method == 'GET':
            if user != job_post.user:
                return Response({"detail": "You do not have permission to view these job applications."}, status=status.HTTP_403_FORBIDDEN)
            job_applications = JobApplication.objects.filter(job_post=job_post).order_by('-created_date')
            paginator = my_paginations.JobApplicationPagination()
            paginated_applications = paginator.paginate_queryset(job_applications, request)
            serializer = serializers.JobApplicationListSerializer(paginated_applications, many=True,context={'request': request})
            return paginator.get_paginated_response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        job_post = self.get_object()
        if job_post.user != request.user:
            return Response({'detail': 'You do not have permission to delete this job post.'},
                            status=status.HTTP_403_FORBIDDEN)
        job_post.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CategoryViewSet(viewsets.ViewSet,generics.ListAPIView,generics.DestroyAPIView,generics.UpdateAPIView,generics.CreateAPIView):
    queryset = Category.objects.all().order_by('-created_date')
    serializer_class = serializers.CategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = my_paginations.CategoryPagination

    def get_permissions(self):
        if self.action in ['list','product']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        if not utils.has_admin_or_manager_permission(request.user):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if not utils.has_admin_or_manager_permission(request.user):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not utils.has_admin_or_manager_permission(request.user):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

    @action(methods=['get'], detail=True, url_path='products')
    def product(self, request, pk=None):
        # Lấy danh mục dựa vào pk
        category = get_object_or_404(Category, pk=pk)

        # Lấy danh sách sản phẩm thuộc về danh mục đó
        products = Product.objects.filter(productcategory__category=category)

        # Phân trang danh sách sản phẩm
        paginator = my_paginations.ProductPagination()
        page = paginator.paginate_queryset(products, request)

        # Serialize danh sách sản phẩm
        serializer = serializers.ProductListSerializer(page, many=True, context={'request': request})

        # Trả về danh sách sản phẩm đã phân trang
        return paginator.get_paginated_response(serializer.data)




class ProductViewSet(viewsets.ViewSet,generics.RetrieveAPIView,generics.CreateAPIView,generics.UpdateAPIView,generics.DestroyAPIView,generics.ListAPIView):
    queryset = Product.objects.all().order_by('-created_date')
    serializer_class = serializers.ProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = my_paginations.ProductPagination

    def get_queryset(self):
        query = self.queryset
        title = self.request.query_params.get('title')
        if title:
            query = query.filter(title__icontains=title)
        return query


    def get_permissions(self):
        if self.action in ['list','retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action in ['retrieve']:
            return serializers.ProductDetailSerializer
        if self.action in ['list']:
            return serializers.ProductListSerializer
        if self.action in ['partial_update']:
            return serializers.ProductUpdateSerializer
        return self.serializer_class

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            try:
                with transaction.atomic():
                    # Tạo sản phẩm và lưu trữ
                    product = serializer.save(user=request.user)

                    # Thêm các category vào product
                    categories = request.data.getlist('category', None)
                    if categories:
                        for cat in categories:
                            obj = Category.objects.get(pk=cat)
                            ProductCategory.objects.create(product=product, category=obj)

                    # Serialize the response data
                    return Response(serializer.data, status=status.HTTP_201_CREATED)

            except Category.DoesNotExist:
                return Response({'error': 'Category does not exist.'}, status=status.HTTP_400_BAD_REQUEST)

            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        product = get_object_or_404(Product, pk=pk, user=request.user)

        if request.user != product.user:
            return Response({"detail": "You do not have permission to update this product."},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(product, data=request.data, partial=True)

        if serializer.is_valid():
            try:
                with transaction.atomic():
                    # Cập nhật sản phẩm
                    product = serializer.save()

                    # Cập nhật categories
                    categories = request.data.getlist('category', None)
                    if categories:
                        # Xóa các category hiện có của sản phẩm
                        ProductCategory.objects.filter(product=product).delete()

                        # Thêm các category mới vào sản phẩm
                        for cat in categories:
                            obj = Category.objects.get(pk=cat)  # Nếu không tìm thấy, sẽ gây ra Category.DoesNotExist
                            ProductCategory.objects.create(product=product, category=obj)

                    return Response({'Message': 'Updated product successfully.'}, status=status.HTTP_200_OK)

            except Category.DoesNotExist:
                return Response({'detail': 'One or more categories do not exist.'}, status=status.HTTP_400_BAD_REQUEST)

            except Exception as e:
                return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BannerViewSet(viewsets.ViewSet,generics.ListAPIView,generics.UpdateAPIView,generics.CreateAPIView,generics.DestroyAPIView):
    queryset = Banner.objects.filter(status='show').order_by('-created_date')
    serializer_class = serializers.BannerSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = my_paginations.BannerPagination

    def get_permissions(self):
        if self.action in ['list']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action in ['list']:
            return serializers.BannerListSerializer
        return self.serializer_class

    def create(self, request, *args, **kwargs):
        if not utils.has_admin_or_manager_permission(request.user):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            try:
                # Lưu banner với người dùng hiện tại
                banner = serializer.save(user=request.user)
                # Trả về dữ liệu chi tiết của banner mới tạo
                return Response(serializers.BannerDetailSerializer(banner, context={'request': request}).data,
                                status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        if not utils.has_admin_or_manager_permission(request.user):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        # Lấy đối tượng Banner cần cập nhật
        banner = get_object_or_404(Banner, pk=pk)

        # Tạo serializer với dữ liệu từ request và đối tượng banner đã có
        serializer = self.get_serializer(banner, data=request.data, partial=True)

        # Kiểm tra tính hợp lệ của dữ liệu
        if serializer.is_valid():
            try:
                # Cập nhật thông tin banner
                banner = serializer.save()
                # Trả về dữ liệu chi tiết của banner sau khi cập nhật
                return Response(serializers.BannerDetailSerializer(banner, context={'request': request}).data,
                                status=status.HTTP_200_OK)
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Nếu dữ liệu không hợp lệ, trả về lỗi với thông báo chi tiết
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        # Lấy đối tượng Banner cần xóa
        banner = get_object_or_404(Banner, pk=pk)

        # Kiểm tra quyền của người dùng trước khi xóa (tùy chọn)
        if not utils.has_admin_or_manager_permission(request.user):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        try:
            # Thực hiện xóa banner
            banner.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], url_path='list', detail=False)
    def list_banner(self, request):
        # Kiểm tra quyền truy cập
        if not utils.has_admin_or_manager_permission(request.user):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        # Lấy danh sách banner và phân trang
        queryset = Banner.objects.all().order_by('-created_date')
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = serializers.BannerSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = serializers.BannerSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)














# class CompanyViewSet(viewsets.ViewSet,generics.CreateAPIView,generics.ListAPIView,generics.RetrieveAPIView,generics.UpdateAPIView):
#     queryset = Company.objects.all().order_by('-workers_number')
#     serializer_class = serializers.CompanySerializer
#     permission_classes = [permissions.IsAuthenticated]
#     pagination_class = my_paginations.CompanyPagination
#
#     def get_permissions(self):
#         if self.action in ['list','retrieve']:
#             return [permissions.AllowAny()]
#         return [permissions.IsAuthenticated()]
#
#     def get_serializer_class(self):
#         if self.action in ['list']:
#             return serializers.CompanyListSerializer
#         if self.action in ['retrieve']:
#             return serializers.CompanyDetailSerializer
#         return self.serializer_class
#
#     def create(self, request):
#         serializer = self.serializer_class(data=request.data)
#         if serializer.is_valid():
#             company = serializer.save(founder=request.user)  # Gán người dùng hiện tại là người tạo công ty
#             return Response(serializers.CompanyDetailSerializer(company, context={'request': request}).data, status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
#
#     @action(methods=['patch'],url_path='status',detail=True)
#     def update_status(self,request,pk=None):
#         company = Company.objects.get(pk=pk)
#         company_status = self.request.data.get('status')
#         company.status = company_status
#         company.save()
#         return Response({"detail": "Status update successfully."}, status=status.HTTP_200_OK)
#
#     @action(detail=True, methods=['post','get'],url_path='recruitments')
#     def add_recruitment(self, request, pk=None):
#         company = self.get_object()
#         owner = request.user
#         if request.method == 'POST':
#             serializer = serializers.RecruitmentSerializer(data=request.data)
#             if serializer.is_valid():
#                 instance = serializer.save(company=company, owner=owner, status=True)
#                 return Response(serializers.RecruitmentDetailSerializer(instance,context={'request':request}).data, status=status.HTTP_201_CREATED)
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
#         elif request.method == 'GET':
#             recruitments = Recruitment.objects.filter(company=company).order_by('-created_date')
#             paginator = my_paginations.RecruitmentPagination()
#             paginated_recruitments = paginator.paginate_queryset(recruitments, request)
#             serializer = serializers.RecruitmentListSerializer(paginated_recruitments, many=True, context={'request': request})
#             return paginator.get_paginated_response(serializer.data)
#
#     @action(detail=True, methods=['post','get'], url_path='job-applications')
#     def add_job_application(self, request, pk=None):
#         company = self.get_object()
#         user = request.user
#         if request.method == 'POST':
#             serializer = serializers.JobApplicationSerializer(data=request.data)
#             if serializer.is_valid():
#                 # Lưu đơn xin việc với công ty và người dùng hiện tại
#                 instance = serializer.save(company=company, user=user, status='pending')
#                 return Response(serializers.JobApplicationDetailSerializer(instance, context={'request': request}).data,
#                                 status=status.HTTP_201_CREATED)
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
#         elif request.method == 'GET':
#             job_applications = JobApplication.objects.filter(company=company).order_by('-created_date')
#             paginator = my_paginations.JobApplicationPagination()
#             paginated_applications = paginator.paginate_queryset(job_applications, request)
#             serializer = serializers.JobApplicationListSerializer(paginated_applications, many=True,
#                                                                   context={'request': request})
#             return paginator.get_paginated_response(serializer.data)

# class RecruitmentViewSet(viewsets.ViewSet, generics.ListAPIView, generics.UpdateAPIView, generics.DestroyAPIView):
#     queryset = Recruitment.objects.all().order_by('-created_date')
#     serializer_class = serializers.RecruitmentSerializer
#
#     def retrieve(self, request, pk=None):
#         recruitment = self.get_object()
#         serializer = serializers.RecruitmentDetailSerializer(recruitment, context={'request': request})
#         return Response(serializer.data,status=status.HTTP_200_OK)
#
#     def destroy(self, request, pk=None):
#         recruitment = self.get_object()
#         recruitment.delete()
#         return Response({"detail": "Recruitment deleted successfully."},status=status.HTTP_204_NO_CONTENT)
#
#     @action(detail=True, methods=['patch'], url_path='status')
#     def toggle_status(self, request, pk=None):
#         recruitment = self.get_object()
#         recruitment.status = not recruitment.status
#         recruitment.save()
#         return Response({"detail": "Recruitment updated successfully."}, status=status.HTTP_200_OK)