from django.shortcuts import redirect
from django.utils.crypto import get_random_string
from oauth2_provider.models import Application
from rest_framework import viewsets, generics, permissions
from rest_framework.response import Response
from . import serializers, my_paginations, filters, utils, my_permissions
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from .utils import *
from django.http import JsonResponse
from django.conf import settings
from oauth2_provider.views import TokenView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from oauth2_provider.settings import oauth2_settings
from django.db.utils import IntegrityError
import json
import uuid
from rest_framework import status
from .models import *
from django.contrib.auth.models import Group
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from rest_framework.exceptions import ValidationError
from django.core.cache import cache


# Create your views here.
class CustomTokenView(TokenView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            data = json.loads(response.content)
            refresh_token = data.get('refresh_token')

            # Thiết lập cookie cho refresh_token
            response.set_cookie(
                key='refresh_token',
                value=refresh_token,
                expires=settings.OAUTH2_PROVIDER['REFRESH_TOKEN_EXPIRE_SECONDS'],
                secure=False,
                httponly=True,
                samesite='Strict'
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


class UserViewSet(viewsets.ViewSet, generics.RetrieveAPIView, generics.ListAPIView):
    queryset = User.objects.filter(is_active=True)
    serializer_class = serializers.UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = my_paginations.UserPagination
    parser_classes = [FormParser, MultiPartParser]
    filterset_class = filters.UserFilterBase
    filter_backends = [DjangoFilterBackend]

    # Thêm filter_backends và filterset_fields
    def get_permissions(self):
        if self.action in ['create', 'list', 'blog', 'activate', 'register', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action in ['retrieve']:
            return serializers.UserDetailSerializer
        if self.action in ['list']:
            return serializers.UserListSerializer
        return self.serializer_class

    def get_object(self):
        return self.request.user

    @action(detail=False, methods=['post'], url_path='register')
    def register(self, request):
        # thêm file vào vstorage
        data = request.data.copy()
        if 'profile_image' in data and data['profile_image']:
            data['profile_image'] = utils.upload_file_to_vstorage(request.FILES.get('profile_image'), 'UserAvatar')
        if 'profile_bg' in data and data['profile_bg']:
            data['profile_bg'] = utils.upload_file_to_vstorage(request.FILES.get('profile_bg'), 'UserBackground')
        serializer = serializers.UserRegistrationSerializer(data=request.data, context={'request': request})
        print('tạo processing')
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Registration successful. Please check your email for the activation link."},
                        status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path=r'activate/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<code>.+)')
    def activate(self, request, uidb64=None, code=None):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and EmailVerificationCode.objects.filter(user=user, code=code, status=False).exists():
            user.is_active = True
            user.save()

            verification_code = EmailVerificationCode.objects.get(user=user, code=code)
            verification_code.status = True
            verification_code.save()  # Redirect to a specific page after successful activation
            return redirect(settings.LOGIN_SUCCESSFULLY_URL)  # 'login' should be the name of your login URL pattern
        else:
            # If the activation fails, you can redirect to an error page or render an error template
            return redirect(settings.LOGIN_FAIL_URL)

    @action(detail=False, methods=['patch'], url_path='update-profile')
    def update_profile(self, request, *args, **kwargs):
        user = self.get_object()
        data = request.data.copy()
        if 'profile_image' in data and data['profile_image']:
            data['profile_image'] = utils.upload_file_to_vstorage(request.FILES.get('profile_image'), 'UserAvatar')
        if 'profile_bg' in data and data['profile_bg']:
            data['profile_bg'] = utils.upload_file_to_vstorage(request.FILES.get('profile_bg'), 'UserBackground')
        serializer = serializers.UserUpdateSerializer(user, data=data, partial=True,
                                                      context={'request': request})
        if serializer.is_valid():
            instance=serializer.save()
            return Response(serializers.UserDetailSerializer(instance, context={'request': request}).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='details')
    def retrieve_user(self, request):
        user = self.get_object()
        serializer = serializers.UserDetailSerializer(user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    # @action(detail=False, methods=['get'], url_path='job-applications')
    # def job_applications(self, request, pk=None):
    #     user = request.user
    #     # người dung của blog
    #     job_application = JobApplication.objects.filter(user=user).order_by('-created_date')
    #     paginator = my_paginations.JobApplicationPagination()
    #     result_page = paginator.paginate_queryset(job_application, request)
    #     serializer = serializers.JobApplicationListSerializer(result_page, many=True, context={'request': request})
    #     return paginator.get_paginated_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        user_id = kwargs.get('pk')  # Lấy ID từ URL
        try:
            user = User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = serializers.UserDetailSerializer(user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='blog', permission_classes=[permissions.IsAuthenticated])
    def blog(self, request, pk=None):
        # người dung của blog
        user_blog = User.objects.get(pk=pk, is_active=True)
        blogs = utils.get_blog_list_of_user(user_blog=user_blog, user=request.user)
        paginator = my_paginations.BlogPagination()
        result_page = paginator.paginate_queryset(blogs, request)
        serializer = serializers.BlogDetailSerializer(result_page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    # @action(detail=False, methods=['get'], url_path='job-post/job-applications')
    # def job_application(self, request):
    #     user = request.user
    #
    #     # Lấy tất cả các JobPost của user
    #     job_posts = JobPost.objects.filter(user=user)
    #
    #     # Lấy tất cả các JobApplication liên quan đến các JobPost này
    #     job_applications = JobApplication.objects.filter(job_post__in=job_posts).order_by('-created_date')
    #
    #     # Phân trang các kết quả
    #     paginator = my_paginations.JobApplicationPagination()
    #     paginated_applications = paginator.paginate_queryset(job_applications, request)
    #
    #     # Serialize các kết quả
    #     serializer = serializers.JobApplicationListSerializer(paginated_applications, many=True,
    #                                                           context={'request': request})
    #
    #     # Trả về phản hồi có phân trang
    #     return paginator.get_paginated_response(serializer.data)

    @action(methods=['post'], detail=True, url_path='follow')
    def follow(self, request, pk=None):
        user = self.get_object()
        try:
            to_user = User.objects.get(pk=pk, is_active=True)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        if user == to_user:
            return Response({'error': 'You cannot follow yourself'}, status=status.HTTP_400_BAD_REQUEST)
        follow, created = Follow.objects.get_or_create(from_user=user, to_user=to_user)
        if not created:
            follow.delete()
            return Response({'message': 'Unfollowed successfully'}, status=status.HTTP_200_OK)
        else:
            return Response({'message': 'Followed successfully'}, status=status.HTTP_201_CREATED)

    @action(methods=['get'], detail=False, url_path='following')
    def following(self, request, pk=None):
        user = self.get_object()  # Lấy người dùng hiện tại
        # Lấy danh sách những người mà user đang theo dõi
        following_users = User.objects.filter(follower__from_user=user).order_by('-personal_groups__interactive')
        page = self.paginate_queryset(following_users)
        # Chúng ta cần serialize danh sách `to_user`
        serializer = serializers.UserListSerializer(page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

    @action(methods=['get'], detail=False, url_path='followers')
    def followers(self, request, pk=None):
        user = request.user  # Lấy người dùng hiện tại từ request
        # Lấy danh sách những người theo dõi user
        follower_users = User.objects.filter(following__to_user=user).order_by('-personal_groups__interactive')
        page = self.paginate_queryset(follower_users)
        serializer = serializers.UserListSerializer(page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

    @action(methods=['get'], detail=False, url_path='stranger')
    def strangers(self, request, pk=None):
        user = request.user  # Lấy user hiện tại từ request

        # Lấy danh sách người dùng có PersonalGroup với user nhưng không follow user
        strangers_with_group = User.objects.filter(
            personal_groups__user=user,  # Có PersonalGroup chung với user
        ).exclude(  # Loại bỏ những người đang following hoặc được follow bởi user
            Q(following__from_user=user) | Q(following__to_user=user)  # Thay đổi từ follower thành following
        ).distinct().order_by('-personal_groups__interactive')

        # Debugging
        print("Strangers with group:", strangers_with_group)

        # Paginate
        page = self.paginate_queryset(strangers_with_group)
        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(strangers_with_group, many=True, context={'request': request})
        return Response(serializer.data)


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
        if self.action in ['list', 'retrieve']:
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
                return Response({'detail': 'You do not have permission to view this blog.'},
                                status=status.HTTP_403_FORBIDDEN)
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
            file_type = request.data.get('file_type', None)
            # Kiểm tra loại file hợp lệ
            if file_type not in ['pdf', 'image', None]:
                return Response({'detail': 'file_type must be pdf, image, or nothing'},
                                status=status.HTTP_400_BAD_REQUEST)

            # Kiểm tra số lượng tệp tin pdf chỉ được <=1 tùy thuộc vào loại tệp
            if file_type == 'pdf' and len(medias) > 1:
                return Response({'detail': 'You can only upload one PDF file.'}, status=status.HTTP_400_BAD_REQUEST)
            # Kiểm tra số lượng tệp tin image chỉ được <=4 tùy thuộc vào loại tệp

            if file_type == 'image' and len(medias) > 4:
                return Response({'detail': 'You can upload up to 4 images.'}, status=status.HTTP_400_BAD_REQUEST)

            # Kiểm tra các tệp tin dựa trên loại tệp
            for file in medias:
                extension = file.name.split('.')[-1].lower()
                if file_type == 'pdf' and extension != 'pdf':
                    return Response({'detail': 'All uploaded files must be PDF when file_type is pdf.'},
                                    status=status.HTTP_400_BAD_REQUEST)
                if file_type == 'image' and extension == 'pdf':
                    return Response({'detail': 'PDF files are not allowed when file_type is image.'},
                                    status=status.HTTP_400_BAD_REQUEST)

            # Validate and create blog instance
            blog = Blog.objects.create(
                user=user,
                content=content,
                description=description,
                visibility=visibility
            )
            for file in medias:
                file_url = utils.upload_file_to_vstorage(file, 'Blog')
                BlogMedia.objects.create(blog=blog, file=file_url)

            # Serialize the response data
            serializer = serializers.BlogSerializer(blog, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        # Lấy blog và các media liên quan trong một truy vấn
        blog = get_object_or_404(Blog, pk=pk, user=request.user)
        if request.user != blog.user:
            return Response({"detail": "You do not have permission to update this blog."},
                            status=status.HTTP_403_FORBIDDEN)

        with transaction.atomic():
            # Xử lý cập nhật blog
            serializer = self.get_serializer(blog, data=request.data, partial=True)
            if serializer.is_valid():
                updated_blog = serializer.save()

                # Xử lý xóa media
                id_media_remove = request.data.getlist('id_media_remove')
                if id_media_remove:
                    BlogMedia.objects.filter(id__in=id_media_remove, blog=updated_blog).delete()

                # Xử lý thêm media mới
                new_media = request.FILES.getlist('media')
                if new_media:
                    file_type = request.data.get('file_type', None)
                    if file_type not in ['pdf', 'image', None]:
                        return Response({'detail': 'file_type must be pdf, image, or nothing'},
                                        status=status.HTTP_400_BAD_REQUEST)

                    # Đếm số lượng media hiện tại của blog
                    media_counts = BlogMedia.objects.filter(blog=blog).aggregate(
                        total_count=Count('id'),  # lấy số lượng media
                        pdf_count=Count('id', filter=Q(file__endswith='.pdf'))  # lấy số lượng pdf
                    )
                    # lấy
                    current_media_count = media_counts['total_count']
                    pdf_count = media_counts['pdf_count']

                    if file_type == 'pdf':
                        if current_media_count + len(new_media) > 1:
                            return Response({'detail': 'You can only have up to 1 PDF file.'},
                                            status=status.HTTP_400_BAD_REQUEST)


                    elif file_type == 'image':
                        # Kiểm tra xem blog có chứa file PDF không
                        if pdf_count > 0:
                            return Response({'detail': 'Please delete all PDF files before uploading images.'},
                                            status=status.HTTP_400_BAD_REQUEST)
                        if current_media_count + len(new_media) > 4:
                            return Response({'detail': 'You can have up to 4 images total.'},
                                            status=status.HTTP_400_BAD_REQUEST)
                    from . import utils
                    for file in new_media:
                        file_url = utils.upload_file_to_vstorage(file, 'Blog')
                        BlogMedia.objects.create(blog=blog, file=file_url)

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

            # Log thông tin file trước khi upload
            if 'file' in data and data['file']:
                data['file'] = utils.upload_file_to_vstorage(data['file'], 'Comment')

            data['user'] = user.id
            serializer = serializers.CommentSerializer(data=data)

            if serializer.is_valid():
                try:
                    instance = serializer.save()
                    return Response(serializers.CommentListSerializer(instance).data, status=status.HTTP_201_CREATED)
                except Exception as e:
                    # Log lỗi cụ thể khi gặp lỗi tại bước save
                    return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        elif request.method == 'GET':
            comments = Comment.objects.filter(blog=blog, parent=None).order_by('-created_date')

            paginator = my_paginations.CommentPagination()

            result_page = paginator.paginate_queryset(comments, request)

            serializer = serializers.CommentListSerializer(result_page, many=True, context={'request': request})

            return paginator.get_paginated_response(serializer.data)


class CommentViewSet(viewsets.ViewSet, generics.UpdateAPIView, generics.DestroyAPIView):
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
            serializer = serializers.CommentListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

    def update(self, request, *args, **kwargs):
        comment = self.get_object()

        # Kiểm tra quyền chỉnh sửa
        if comment.user != request.user:
            return Response({'detail': 'You do not have permission to edit this comment.'},
                            status=status.HTTP_403_FORBIDDEN)

        # Loại bỏ trường 'parent' khỏi dữ liệu gửi đến
        data = request.data.copy()
        if 'file' in data and data['file']:
            data['file'] = utils.upload_file_to_vstorage(data['file'], 'Comment')
        if 'parent' in data:
            data.pop('parent')

        partial = True
        serializer = self.get_serializer(comment, data=data, partial=partial)

        if serializer.is_valid():
            comment.file
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        comment = self.get_object()
        if comment.user != request.user:
            return Response({'detail': 'You do not have permission to edit this comment.'},
                            status=status.HTTP_403_FORBIDDEN)
        comment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# class JobApplicationViewSet(viewsets.ViewSet, generics.UpdateAPIView, generics.DestroyAPIView):
#     queryset = JobApplication.objects.all().order_by('-created_date')
#     serializer_class = serializers.JobApplicationSerializer
#
#     # def update(self, request, *args, **kwargs):
#     #     job_application = self.get_object()
#     #     # Kiểm tra xem người dùng hiện tại có phải là người đã tạo ra JobApplication không
#     #     if request.user != job_application.user:
#     #         return Response({"detail": "You do not have permission to update this job application."},
#     #                         status=status.HTTP_403_FORBIDDEN)
#     #     serializer = serializers.JobApplicationSerializer(job_application, data=request.data, partial=True)
#     #     if serializer.is_valid():
#     #         serializer.save()
#     #         return Response({"detail": "Job application updated successfully."},status=status.HTTP_200_OK)
#     #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
#     #
#     # def destroy(self, request, pk=None):
#     #     job_application = self.get_object()
#     #     # Kiểm tra xem người dùng hiện tại có phải là người đã tạo ra JobApplication không
#     #     if request.user != job_application.user:
#     #         return Response({"detail": "You do not have permission to delete this job application."},
#     #                         status=status.HTTP_403_FORBIDDEN)
#     #     job_application.delete()
#     #     return Response(status=status.HTTP_204_NO_CONTENT)
#
#     @action(detail=True, methods=['patch'], url_path='status')
#     def update_status(self, request, pk=None):
#         job_application = self.get_object()
#         new_status = request.data.get('status')
#         # Kiểm tra quyền chỉnh sửa: Chỉ cho phép người tạo bài đăng sửa đổi nó
#         if job_application.job_post.user != request.user:
#             return Response({'detail': 'You do not have permission to change status this job application.'},
#                             status=status.HTTP_403_FORBIDDEN)
#         if new_status not in dict(JobApplication.STATUS_CHOICES).keys():
#             return Response({"error": "Invalid status value."}, status=status.HTTP_400_BAD_REQUEST)
#
#         job_application.status = new_status
#         job_application.save()
#
#         serializer = serializers.JobApplicationDetailSerializer(job_application, context={'request': request})
#         return Response(serializer.data, status=status.HTTP_200_OK)


class ChangePasswordViewSet(viewsets.ViewSet):
    queryset = User.objects.filter(is_active=True)
    serializer_class = serializers.ChangePasswordSerializer

    def get_permissions(self):
        if self.action in ['reset_password', 'verify_code']:
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
        user = User.objects.get(email=email, is_active=True)
        code = get_random_string(length=6, allowed_chars='0123456789')

        try:
            reset_code = PasswordResetCode.objects.get(user=user)
            if not reset_code.is_expired():
                return Response({"error": "Already sent verify code"}, status=status.HTTP_400_BAD_REQUEST)
        except PasswordResetCode.DoesNotExist:
            reset_code = PasswordResetCode(user=user)

        reset_code.code = code
        reset_code.status = False
        reset_code.save()

        send_verification_email(email, 'Mã xác nhận đổi mật khẩu', f'Đây là mã xác nhận của bạn: {code}'
                                                                   f'\n MÃ HIỆU LỰC NÀY CÓ TÁC DỤNG TRONG 3 PHÚT!')

        return Response({"message": "Verification code sent to your email"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='verify-code')
    def verify_code(self, request):
        serializer = serializers.VerifyCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.get(email=serializer.validated_data['email'], is_active=True)
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


# class JobPostViewSet(viewsets.ViewSet, generics.ListAPIView, generics.RetrieveAPIView, generics.UpdateAPIView,
#                      generics.CreateAPIView, generics.DestroyAPIView):
#     queryset = JobPost.objects.all().order_by('-created_date')
#     serializer_class = serializers.JobPostSerializer
#     pagination_class = my_paginations.JobPostPagination
#     permission_classes = [permissions.IsAuthenticated]  # Yêu cầu người dùng phải đăng nhập
#
#     def get_permissions(self):
#         if self.action in ['list', 'retrieve']:
#             return [permissions.AllowAny()]
#         return [permissions.IsAuthenticated()]
#
#     def get_serializer_class(self, *args, **kwargs):
#         if self.action in ['retrieve']:
#             return serializers.JobPostDetailSerializer
#         elif self.action in ['list']:
#             return serializers.JobPostListSerializer
#         return self.serializer_class
#
#     def update(self, request, *args, **kwargs):
#         job_post = self.get_object()
#
#         # Kiểm tra quyền chỉnh sửa: Chỉ cho phép người tạo bài đăng sửa đổi nó
#         if job_post.user != request.user:
#             return Response({'detail': 'You do not have permission to edit this job post.'},
#                             status=status.HTTP_403_FORBIDDEN)
#
#         # Loại bỏ trường không cho phép chỉnh sửa nếu cần
#         data = request.data.copy()
#
#         # Xử lý danh sách tag_id để thêm tag mới vào JobPost
#         tag_ids = request.data.getlist('tag_id')
#         for tag_id in tag_ids:
#             tag, created = Tag.objects.get_or_create(id=tag_id)
#             JobPostTag.objects.get_or_create(job_post=job_post, tag=tag)
#
#         # Xử lý danh sách remove_jobpost_tag_id để xóa các JobPostTag hiện có
#         remove_jobpost_tag_ids = request.data.getlist('remove_jobpost_tag_id')
#         JobPostTag.objects.filter(id__in=remove_jobpost_tag_ids, job_post=job_post).delete()
#
#         # Cập nhật JobPost với các thay đổi khác
#         serializer = self.get_serializer(job_post, data=data, partial=True)
#
#         if serializer.is_valid():
#             updated_job_post = serializer.save()  # Lưu các thay đổi
#             return Response(serializers.JobPostDetailSerializer(updated_job_post, context={'request': request}).data,
#                             status=status.HTTP_200_OK)
#
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
#
#     def create(self, request):
#         user = request.user
#         data = request.data.copy()
#         data['user'] = user.id  # Gán user hiện tại vào dữ liệu
#
#         # Lấy danh sách tag_id từ request data
#         tag_ids = request.data.getlist('tag_id', [])
#
#         serializer = serializers.JobPostSerializer(data=data)
#
#         if serializer.is_valid():
#             try:
#                 with transaction.atomic():
#                     # Tạo JobPost
#                     instance = serializer.save(user=user)
#
#                     # Thêm các tag vào JobPost
#                     for tag_id in tag_ids:
#                         try:
#                             tag = Tag.objects.get(id=tag_id)
#                             JobPostTag.objects.create(job_post=instance, tag=tag)
#                         except Tag.DoesNotExist:
#                             raise ValidationError({'tag_id': f'Tag with id {tag_id} does not exist.'})
#                         except IntegrityError:
#                             raise ValidationError({'tag_id': f'Tag with id {tag_id} already exists for this job post.'})
#
#                     # Trả về response với chi tiết JobPost
#                     return Response(serializers.JobPostDetailSerializer(instance, context={'request': request}).data,
#                                     status=status.HTTP_201_CREATED)
#
#             except ValidationError as e:
#                 return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
#
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
#
#     @action(detail=True, methods=['post', 'get'], url_path='job-applications')
#     def job_application(self, request, pk=None):
#         job_post = self.get_object()
#         user = request.user
#         try:
#             if request.method == 'POST':
#                 # Lấy từng trường dữ liệu từ request
#                 job_title = request.data.get('job_title')
#                 cv = request.FILES.get('cv')
#                 fullname = request.data.get('fullname')
#                 phone_number = request.data.get('phone_number')
#                 email = request.data.get('email')
#                 sex = request.data.get('sex')
#                 age = request.data.get('age')
#                 cv = utils.upload_file_to_vstorage(cv, "CV")
#                 # Validate dữ liệu (bạn có thể thêm các bước validate khác ở đây)
#                 if not all([job_title, cv, fullname, phone_number, email, sex, age]):
#                     return Response({"error": "Required fields not enough"}, status=status.HTTP_400_BAD_REQUEST)
#                 # Tạo JobApplication mới
#                 job_application = JobApplication.objects.create(
#                     job_post=job_post,
#                     user=user,
#                     job_title=job_title,
#                     cv=cv,
#                     fullname=fullname,
#                     phone_number=phone_number,
#                     email=email,
#                     sex=sex,
#                     age=age,
#                 )
#
#                 return Response({"message": "Successfully"}, status=status.HTTP_201_CREATED)
#
#             elif request.method == 'GET':
#                 if user != job_post.user:
#                     return Response({"detail": "You do not have permission to view these job applications."},
#                                     status=status.HTTP_403_FORBIDDEN)
#                 job_applications = JobApplication.objects.filter(job_post=job_post).order_by('-created_date')
#                 paginator = my_paginations.JobApplicationPagination()
#                 paginated_applications = paginator.paginate_queryset(job_applications, request)
#                 serializer = serializers.JobApplicationListSerializer(paginated_applications, many=True,
#                                                                       context={'request': request})
#                 return paginator.get_paginated_response(serializer.data)
#         except Exception as e:
#             print("Error occurred: ", str(e))
#             return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#
#     def destroy(self, request, *args, **kwargs):
#         job_post = self.get_object()
#         if job_post.user != request.user:
#             return Response({'detail': 'You do not have permission to delete this job post.'},
#                             status=status.HTTP_403_FORBIDDEN)
#         job_post.delete()
#         return Response(status=status.HTTP_204_NO_CONTENT)
#

class CategoryViewSet(viewsets.ViewSet, generics.ListAPIView, generics.DestroyAPIView, generics.UpdateAPIView,
                      generics.CreateAPIView):
    queryset = Category.objects.all().order_by('-created_date')
    serializer_class = serializers.CategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = my_paginations.CategoryPagination

    def get_permissions(self):
        if self.action in ['list', 'product']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def list(self, request, *args, **kwargs):
        cache_key = 'category_list'
        categories = cache.get(cache_key)
        if not categories:
            response = super().list(request, *args, **kwargs)
            categories = response.data
            cache.set(cache_key, categories, timeout=settings.CATEGORY_CACHE_TIME)  # Cache trong 24 giờ
        else:
            response = Response(categories, status=status.HTTP_200_OK)
        return response

    def retrieve(self, request, *args, **kwargs):
        category_id = kwargs.get('pk')
        cache_key = f'category_{category_id}'
        category = cache.get(cache_key)
        if not category:
            response = super().retrieve(request, *args, **kwargs)
            category = response.data
            cache.set(cache_key, category, timeout=60 * 60 * 24)  # Cache trong 24 giờ
        else:
            response = Response(category, status=status.HTTP_200_OK)
        return response

    def create(self, request, *args, **kwargs):
        if not utils.has_admin_or_manager_permission(request.user):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        response = super().create(request, *args, **kwargs)
        # Xóa cache khi thêm mới danh mục
        cache.delete('category_list')
        return response

    def update(self, request, *args, **kwargs):
        if not utils.has_admin_or_manager_permission(request.user):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        response = super().update(request, *args, **kwargs)
        cache_key = kwargs.get('pk')
        cache.delete(f'category_{cache_key}')
        cache.delete('category_list')
        return response

    def destroy(self, request, *args, **kwargs):
        if not utils.has_admin_or_manager_permission(request.user):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        response = super().destroy(request, *args, **kwargs)
        cache_key = kwargs.get('pk')
        cache.delete(f'category_{cache_key}')
        cache.delete('category_list')
        return response

    @action(methods=['get'], detail=True, url_path='products')
    def product(self, request, pk=None):
        cache_key = f'category_products_{pk}'
        cached_data = cache.get(cache_key)

        if cached_data is None:
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
            paginated_data = paginator.get_paginated_response(serializer.data)

            # Lưu dữ liệu đã phân trang vào cache
            cache.set(cache_key, paginated_data.data, timeout=settings.PRODUCT_CACHE_TIME)  # Cache trong 10 phút

            return paginated_data
        else:
            # Nếu đã có cache, trả về dữ liệu đã phân trang từ cache
            return Response(cached_data)


class ProductViewSet(viewsets.ViewSet, generics.RetrieveAPIView, generics.CreateAPIView, generics.UpdateAPIView,
                     generics.DestroyAPIView, generics.ListAPIView):
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
        if self.action in ['list', 'retrieve']:
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

                    # Thêm các media vào product
                    medias = request.FILES.getlist('media', None)
                    # kiểm tra số file có lớn hơn 4 không
                    if medias:
                        if len(medias) > 4:
                            return Response({'detail': 'You can upload up to 4 media files.'},
                                            status=status.HTTP_400_BAD_REQUEST)
                        for file in medias:
                            file_url = utils.upload_file_to_vstorage(file, 'Product')
                            ProductMedia.objects.create(product=product, media=file_url)

                    # Serialize the response data
                    response_serializer = serializers.ProductDetailSerializer(product)
                    return Response(response_serializer.data, status=status.HTTP_201_CREATED)

            except Category.DoesNotExist:
                return Response({'error': 'Category does not exist.'}, status=status.HTTP_400_BAD_REQUEST)

            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        # Lấy đối tượng sản phẩm hoặc trả về lỗi 404 nếu không tìm thấy
        product = get_object_or_404(Product, pk=pk, user=request.user)

        # Kiểm tra quyền truy cập
        if request.user != product.user:
            return Response({"detail": "You do not have permission to update this product."},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(product, data=request.data, partial=True)

        if serializer.is_valid():
            try:
                with transaction.atomic():
                    # Cập nhật sản phẩm
                    product = serializer.save()

                    # Xử lý các category_id: thêm mới các category
                    category_ids = request.data.getlist('category_id', None)
                    if category_ids:
                        # Thêm các category mới vào sản phẩm
                        for cat_id in category_ids:
                            try:
                                obj = Category.objects.get(pk=cat_id)
                                ProductCategory.objects.create(product=product, category=obj)
                            except Category.DoesNotExist:
                                return Response({'detail': f'Category with id {cat_id} does not exist.'},
                                                status=status.HTTP_400_BAD_REQUEST)
                            except IntegrityError:
                                return Response({
                                    'detail': f'ProductCategory with product {product.id} and category {cat_id} already exists.'},
                                    status=status.HTTP_400_BAD_REQUEST)

                    # Xử lý các remove_product_category_id: xóa các category
                    remove_category_ids = request.data.getlist('remove_product_category_id', None)
                    if remove_category_ids:
                        ProductCategory.objects.filter(product=product, category__id__in=remove_category_ids).delete()

                    # Xử lý các remove_product_media_id: xóa các media
                    remove_media_ids = request.data.getlist('remove_product_media_id', None)
                    if remove_media_ids:
                        ProductMedia.objects.filter(id__in=remove_media_ids).delete()

                    # Xử lý các media: thêm mới các media
                    media_files = request.FILES.getlist('media', None)
                    if media_files:
                        current_media_count = ProductMedia.objects.filter(product=product).count()
                        if current_media_count + len(media_files) > 4:
                            return Response({'detail': 'You can upload up to 4 media files.'},
                                            status=status.HTTP_400_BAD_REQUEST)
                        else:
                            # Thêm các media mới vào sản phẩm
                            for file in media_files:
                                file_url = utils.upload_file_to_vstorage(file, 'Product')
                                ProductMedia.objects.create(product=product, media=file_url)

                    return Response(serializers.ProductDetailSerializer(product).data, status=status.HTTP_200_OK)

            except Category.DoesNotExist:
                return Response({'detail': 'One or more categories do not exist.'}, status=status.HTTP_400_BAD_REQUEST)

            except Exception as e:
                return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BannerViewSet(viewsets.ViewSet, generics.ListAPIView, generics.UpdateAPIView, generics.CreateAPIView,
                    generics.DestroyAPIView):
    queryset = Banner.objects.all().order_by('-created_date')
    serializer_class = serializers.BannerSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = my_paginations.BannerPagination

    def get_permissions(self):
        if self.action in ['list']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action in ['list', 'list_banner']:
            return serializers.BannerListSerializer
        return self.serializer_class

    def get_queryset(self):
        if self.action in ['list']:
            return Banner.objects.filter(status='show').order_by('-created_date')
        return self.queryset

    def create(self, request, *args, **kwargs):
        if not utils.has_admin_or_manager_permission(request.user):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        data = request.data.copy()
        if 'image' in data and data['image']:
            data['image'] = utils.upload_file_to_vstorage(data['image'], 'Banner')
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            try:
                banner = serializer.save(user=request.user)
                # Xóa cache khi có banner mới được thêm
                cache.delete('banner_list_show')
                cache.delete('banner_list_all')
                return Response(serializers.BannerDetailSerializer(banner).data,
                                status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        if not utils.has_admin_or_manager_permission(request.user):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        banner = get_object_or_404(Banner, pk=kwargs.get('pk'))
        data = request.data.copy()
        if 'image' in data and data['image']:
            data['image'] = utils.upload_file_to_vstorage(data['image'],'Banner')
        serializer = self.get_serializer(banner, data=data, partial=True)
        if serializer.is_valid():
            try:
                banner = serializer.save()
                # Xóa cache khi có banner được cập nhật
                cache.delete('banner_list_show')
                cache.delete('banner_list_all')
                return Response(serializers.BannerDetailSerializer(banner).data,
                                status=status.HTTP_200_OK)
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        banner = get_object_or_404(Banner, pk=pk)
        if not utils.has_admin_or_manager_permission(request.user):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        try:
            banner.delete()
            # Xóa cache khi có banner bị xóa
            cache.delete('banner_list_show')
            cache.delete('banner_list_all')
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        cache_key = 'banner_list_show'
        banners = cache.get(cache_key)
        if not banners:
            response = super().list(request, *args, **kwargs)
            banners = response.data
            cache.set(cache_key, banners)
        else:
            response = Response(banners, status=status.HTTP_200_OK)
        return response

    @action(methods=['get'], url_path='list', detail=False)
    def list_banner(self, request):
        cache_key = f'banner_list_all'
        cached_data = cache.get(cache_key)

        if cached_data is None:

            # Lấy danh sách sản phẩm thuộc về danh mục đó
            banners = self.get_queryset()
            # Phân trang danh sách sản phẩm
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(banners, request)

            # Serialize danh sách sản phẩm
            serializer = self.get_serializer(page, many=True)

            # Trả về danh sách banner đã phân trang
            paginated_data = paginator.get_paginated_response(serializer.data)

            # Lưu dữ liệu đã phân trang vào cache
            cache.set(cache_key, paginated_data.data)

            return paginated_data
        else:
            # Nếu đã có cache, trả về dữ liệu đã phân trang từ cache
            return Response(cached_data)


class GroupViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = Group.objects.all()
    serializer_class = serializers.GroupSerializer  # Bạn cần định nghĩa serializer này
    permission_classes = [my_permissions.IsAdminOrManager]
    pagination_class = my_paginations.GroupPagination  # Sử dụng phân trang có sẵn của bạn
    filter_backends = [DjangoFilterBackend]

    def get_permissions(self):
        if self.action in ['all_users']:
            return [my_permissions.IsAdmin()]
        return [my_permissions.IsAdminOrManager()]

    # API để lấy tất cả thành viên nào có group
    @action(methods=['get'], detail=False, url_path='all-users-with-group')
    def all_users_with_group(self, request):
        users_with_group = User.objects.filter(groups__isnull=False, is_active=True).distinct()
        filtered_users = filters.UserAdminFilter(request.GET, queryset=users_with_group).qs  # Áp dụng bộ lọc
        paginator = my_paginations.UserPagination()
        paginated_users = paginator.paginate_queryset(filtered_users, request)
        serializer = serializers.UserListForAdminSerializer(paginated_users, many=True)
        return paginator.get_paginated_response(serializer.data)

    # API để lấy thành viên có trong một group cụ thể
    @action(methods=['get'], detail=True, url_path='users')
    def users_in_group(self, request, pk=None):
        group = self.get_object()
        users_in_group = group.user_set.all()
        filtered_users = filters.UserAdminFilter(request.GET, queryset=users_in_group).qs  # Áp dụng bộ lọc
        paginator = my_paginations.UserPagination()
        paginated_users = paginator.paginate_queryset(filtered_users, request)
        serializer = serializers.UserListSerializer(paginated_users, many=True)
        return paginator.get_paginated_response(serializer.data)

        # API để lấy tất cả user
        @action(methods=['get'], detail=False, url_path='admin/users')
        def all_users(self, request):
            users = User.objects.filter(is_active=True).order_by('-date_joined')
            filtered_users = filters.UserAdminFilter(request.GET, queryset=users).qs  # Áp dụng bộ lọc
            paginator = my_paginations.UserPagination()
            paginated_users = paginator.paginate_queryset(filtered_users, request)
            serializer = serializers.UserListForAdminSerializer(paginated_users, many=True,)
            return paginator.get_paginated_response(serializer.data)

    @action(methods=['post'], detail=True, url_path='add-user')
    def add_user(self, request, pk=None):
        group = self.get_object()
        user_ids = request.data.getlist('id')

        # Kiểm tra quyền của người dùng hiện tại đối với nhóm
        if not has_permission_to_modify_group(request.user, group):
            return Response({"error": "You do not have permission to add users to this group."},
                            status=status.HTTP_403_FORBIDDEN)

        # Bắt đầu một giao dịch để đảm bảo tính toàn vẹn của quá trình thêm người dùng
        try:
            with transaction.atomic():
                for user_id in user_ids:
                    try:
                        user = User.objects.get(pk=user_id, is_active=True)

                        # Kiểm tra xem người dùng đã thuộc nhóm nào chưa
                        if user.groups.exists():
                            return Response({"error": f"User with ID {user_id} is already in a group."},
                                            status=status.HTTP_400_BAD_REQUEST)

                        # Thêm người dùng vào nhóm
                        group.user_set.add(user)
                    except User.DoesNotExist:
                        return Response({"error": f"User with ID {user_id} not found."},
                                        status=status.HTTP_404_NOT_FOUND)

            return Response({"message": "Users have been added to the group."},
                            status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['post'], detail=True, url_path='remove-user')
    def remove_user(self, request, pk=None):
        group = self.get_object()
        user_ids = request.data.getlist('id')

        # Kiểm tra quyền của người dùng hiện tại đối với nhóm
        if not has_permission_to_modify_group(request.user, group):
            return Response({"error": "You do not have permission to remove users to this group."},
                            status=status.HTTP_403_FORBIDDEN)

        # Bắt đầu một giao dịch để đảm bảo tính toàn vẹn của quá trình xóa người dùng
        try:
            with transaction.atomic():
                for user_id in user_ids:
                    try:
                        user = User.objects.get(pk=user_id, is_active=True)

                        # Kiểm tra xem người dùng có thuộc nhóm này không
                        if not group.user_set.filter(pk=user_id).exists():
                            return Response({"error": f"User with ID {user_id} is not in the group."},
                                            status=status.HTTP_400_BAD_REQUEST)

                        # Xóa người dùng khỏi nhóm
                        group.user_set.remove(user)
                    except User.DoesNotExist:
                        return Response({"error": f"User with ID {user_id} not found."},
                                        status=status.HTTP_404_NOT_FOUND)

            return Response({"message": "Users have been removed from the group."},
                            status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='list')
    def list_groups(self, request):
        groups = self.get_queryset()
        paginator = my_paginations.GroupPagination()
        paginated_groups = paginator.paginate_queryset(groups, request)
        serializer = serializers.GroupListSerializer(paginated_groups, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)


class WebsiteViewSet(viewsets.ViewSet, generics.RetrieveAPIView, generics.UpdateAPIView):
    queryset = Website.objects.all()
    serializer_class = serializers.WebsiteSerializer
    permission_classes = [my_permissions.IsAdmin]

    def get_permissions(self):
        if self.action in ['retrieve']:
            return [permissions.AllowAny()]
        return [my_permissions.IsAdmin()]

    def get_serializer_class(self):
        if self.action in ['retrieve']:
            return serializers.WebsiteDetailSerializer
        return serializers.WebsiteSerializer

    @action(detail=True, methods=['GET'])
    def detail(self, request, pk=None):
        cache_key = f'website_config_{pk}'
        website_data = cache.get(cache_key)

        if website_data is None:
            website = self.get_object()
            serializer = serializers.WebsiteDetailSerializer(website, context={'request': request})
            website_data = serializer.data
            # Cache dữ liệu cấu hình vĩnh viễn
            cache.set(cache_key, website_data)
        return Response(website_data)

    def update(self, request, *args, **kwargs):
        website = self.get_object()
        data = request.data.copy()
        if 'img' in data and data['img']:
            data['img'] = utils.upload_file_to_vstorage(data['img'], 'GroupChat')
        serializer = self.get_serializer(website, data=data, partial=True)

        if serializer.is_valid():
            try:
                website = serializer.save()
                # Xóa cache khi có sự thay đổi
                cache_key = f'website_config_{website.pk}'
                cache.delete(cache_key)
                return Response(serializers.WebsiteDetailSerializer(website, context={'request': request}).data,
                                status=status.HTTP_200_OK)
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TagViewSet(viewsets.ViewSet, generics.ListAPIView, generics.CreateAPIView, generics.UpdateAPIView,
                 generics.DestroyAPIView):
    queryset = Tag.objects.all()
    serializer_class = serializers.TagSerializer
    permission_classes = [my_permissions.IsAdmin]
    pagination_class = my_paginations.TagPagination

    def get_permissions(self):
        if self.action in ['list']:
            return [permissions.AllowAny()]
        return [my_permissions.IsAdmin()]

    def list(self, request):
        cache_key = 'tag_list_cache'
        tags_data = cache.get(cache_key)

        if tags_data is None:
            tags = Tag.objects.all().order_by('id')
            # Phân trang danh sách sản phẩm
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(tags, request)

            # Serialize danh sách sản phẩm
            serializer = self.get_serializer(page, many=True)

            # Trả về danh sách banner đã phân trang
            paginated_data = paginator.get_paginated_response(serializer.data)

            # Lưu dữ liệu đã phân trang vào cache
            cache.set(cache_key, paginated_data.data)
            return paginated_data
        else:
            return Response(tags_data)

    def create(self, request):
        serializer = serializers.TagSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            # Xóa cache khi có tag mới được thêm
            cache.delete('tag_list_cache')
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        tag = get_object_or_404(Tag, pk=pk)
        serializer = serializers.TagSerializer(tag, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # Xóa cache khi có tag được cập nhật
            cache.delete('tag_list_cache')
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        tag = get_object_or_404(Tag, pk=pk)
        tag.delete()
        # Xóa cache khi có tag bị xóa
        cache.delete('tag_list_cache')
        return Response(status=status.HTTP_204_NO_CONTENT)


class GroupChatViewSet(viewsets.ViewSet, generics.ListAPIView, generics.CreateAPIView, generics.UpdateAPIView,
                       generics.DestroyAPIView):
    queryset = GroupChat.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.GroupChatSerializer
    pagination_class = my_paginations.SocialGroupPagination

    def get_queryset(self):
        query = self.queryset
        if self.action in ['list']:
            name = self.request.query_params.get('name', None)
            if name:
                query = query.filter(name__icontains=name)
        return query

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.GroupChatListSerializer
        return self.serializer_class

    def list(self, request, *args, **kwargs):
        user = request.user
        groups = self.get_queryset().filter(memberships__user=user).order_by('-memberships__interactive')
        # lấy pagitation
        paginator = my_paginations.SocialGroupPagination()
        # paginate groups
        paginated_groups = paginator.paginate_queryset(groups, request)
        # serialize lại dữ liệu được paginate
        serializer = self.get_serializer(paginated_groups, many=True, context={'request': request})
        # trả về kết quả được paginate
        return paginator.get_paginated_response(serializer.data)

    def create(self, request, *args, **kwargs):
        # copy dữ liệu từ body
        data = request.data.copy()
        if 'image' in data and data['image']:
            data['image'] = utils.upload_file_to_vstorage(data['image'], 'GroupChat')
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            # lấy groupchat
            group_chat = serializer.save()
            # Người tạo group sẽ trở thành owner
            GroupChatMembership.objects.create(group_chat=group_chat, user=request.user, role='owner')

        serializer = serializers.GroupChatDetailSerializer(group_chat, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        group_chat = self.get_object()

        # Kiểm tra quyền sửa (owner hoặc manager)
        membership = GroupChatMembership.objects.filter(group_chat=group_chat, user=request.user).first()
        if membership.role not in ['owner', 'manager']:
            return Response({'error': 'You do not have permission to update group.'},
                            status=status.HTTP_403_FORBIDDEN)
        data = request.data.copy()
        if 'image' in data and data['image']:
            data['image'] = utils.upload_file_to_vstorage(data['image'], 'GroupChat')
        serializer = self.get_serializer(group_chat, data=data, partial=True, context={'request': request})
        if serializer.is_valid():
            group_data = serializer.save()
            return Response(serializers.GroupChatDetailSerializer(group_data, context={'request': request}).data,
                            status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        group_chat = self.get_object()

        # Chỉ owner mới được xóa group
        is_owner = GroupChatMembership.objects.filter(
            group_chat=group_chat,
            user=request.user,
            role='owner'
        ).exists()

        if not is_owner:
            return Response(
                {'error': 'Only owner has permission to delete this group.'},
                status=status.HTTP_403_FORBIDDEN
            )
        group_chat.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['get', 'post', 'delete', 'update'], detail=True, url_path='member')
    def member(self, request, pk=None):
        group_chat = self.get_object()
        user = request.user
        # lấy role của user
        try:
            group_chat_membership = GroupChatMembership.objects.get(
                group_chat=group_chat,
                user=user)
        except GroupChatMembership.DoesNotExist:
            return Response({'error': 'You do not have permission in this group.'},
                            status=status.HTTP_403_FORBIDDEN)
        if request.method == "GET":
            members = GroupChatMembership.objects.filter(group_chat=group_chat).order_by("role", "-created_date")
            username = request.query_params.get('username', None)
            if username:
                members = members.filter(user__username__icontains=username)
            # lấy paginator
            paginator = my_paginations.UserPagination()
            # pagination dữ liệu
            paginated_members = paginator.paginate_queryset(members, request)
            # serialize dữ liệu được paginate
            serializer = serializers.GroupChatMemberListSerializer(paginated_members, many=True,
                                                                   context={'request': request})
            return paginator.get_paginated_response(serializer.data)

        elif request.method == "POST":
            # Lấy danh sách user_id để thêm người dùng
            user_ids = request.data.getlist('user_id', [])

            # Lấy danh sách user_id_remove để xóa người dùng
            user_ids_remove = request.data.getlist('user_id_remove', [])

            # Xóa người dùng khỏi group nếu có danh sách user_id_remove
            if user_ids_remove:
                # Kiểm tra quyền (chỉ owner mới được xóa)
                if group_chat_membership.role != 'owner':
                    return Response({'error': 'Only owner can delete members.'}, status=status.HTTP_403_FORBIDDEN)

                # Kiểm tra xem người dùng có tự xóa mình không
                if str(user.id) in user_ids_remove:
                    return Response({'error': 'You cannot remove yourself from the group.'},
                                    status=status.HTTP_400_BAD_REQUEST)

                for user_id in user_ids_remove:
                    try:
                        member_to_remove = GroupChatMembership.objects.get(group_chat=group_chat, user_id=user_id)
                        member_to_remove.delete()
                    except GroupChatMembership.DoesNotExist:
                        pass  # Bỏ qua nếu người dùng không phải là thành viên

            # Thêm người dùng vào group nếu có danh sách user_id
            if user_ids:
                for user_id in user_ids:
                    try:
                        new_user = User.objects.get(id=user_id)
                        try:
                            # Thêm user vào nhóm với role 'member'
                            GroupChatMembership.objects.create(group_chat=group_chat, user=new_user, role='member')
                        except IntegrityError:
                            # Bỏ qua nếu user đã là thành viên của nhóm (duplicate entry)
                            pass
                    except User.DoesNotExist:
                        pass  # Bỏ qua nếu người dùng không tồn tại

            # Trả về thông báo thành công
            return Response({"message": "Operation successful"}, status=status.HTTP_200_OK)

        elif request.method == "DELETE":

            # Nếu user là owner, cần chuyển quyền owner trước khi rời nhóm
            if group_chat_membership.role == 'owner':
                # Tìm thành viên có `created_date` lâu nhất (trừ người dùng hiện tại)
                next_owner = GroupChatMembership.objects.filter(
                    group_chat=group_chat
                ).exclude(user=user).order_by('created_date').first()

                if next_owner:
                    # Trao quyền owner cho thành viên có `created_date` lâu nhất
                    next_owner.role = 'owner'
                    next_owner.save()
                else:
                    # Nếu không còn thành viên nào khác, xóa group
                    group_chat.delete()
                group_chat_membership.delete()
            return Response(status=status.HTTP_200_OK)

        elif request.method == "PATCH":
            # Chỉ owner mới được thay đổi vai trò của thành viên khác
            if group_chat_membership.role != 'owner':
                return Response({'error': 'Only the owner can change roles.'}, status=status.HTTP_403_FORBIDDEN)

            # Lấy user_id và vai trò mới từ request
            user_id = request.data.get('user_id')
            new_role = request.data.get('role')

            if not user_id or not new_role:
                return Response({'error': 'Both user_id and role must be provided.'},
                                status=status.HTTP_400_BAD_REQUEST)

            # Kiểm tra vai trò hợp lệ
            if new_role not in ['owner', 'manager', 'member']:
                return Response({'error': 'Invalid role. Role must be "owner", "manager", or "member".'},
                                status=status.HTTP_400_BAD_REQUEST)

            try:
                # Lấy thành viên cần đổi vai trò
                member_to_update = GroupChatMembership.objects.get(group_chat=group_chat, user_id=user_id)

                # Nếu role mới là "owner", cập nhật owner hiện tại thành "member"
                if new_role == 'owner':
                    # Đổi vai trò của owner hiện tại thành member
                    group_chat_membership.role = 'member'
                    group_chat_membership.save()

                # Đổi vai trò của người dùng được chỉ định
                member_to_update.role = new_role
                member_to_update.save()

                return Response({'message': f'Role of {member_to_update.user.username} changed to {new_role}.'},
                                status=status.HTTP_200_OK)

            except GroupChatMembership.DoesNotExist:
                return Response({'error': 'The specified user is not a member of the group.'},
                                status=status.HTTP_404_NOT_FOUND)

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
