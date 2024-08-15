from django.contrib.auth.hashers import check_password
from oauth2_provider.models import AccessToken, RefreshToken
from django.core.mail import send_mail
from django.db.models import Count, Q
from .models import *

def get_blog_details(blog_id, user):
    if user.is_anonymous:
        return Blog.objects.filter(id=blog_id).annotate(
            likes_count=Count('like'),
            comment_count=Count('comment')
        ).first()
    else:
        return Blog.objects.filter(id=blog_id).annotate(
            likes_count=Count('like'),
            comment_count=Count('comment'),
            likes_user=Count('like', filter=Q(like__user=user))
        ).first()

def get_blog_list(user):
    if user.is_anonymous:
        return Blog.objects.filter(visibility='public').annotate(
            likes_count=Count('like'),
            comment_count=Count('comment')
        ).order_by('-created_date')
    else:
        return Blog.objects.filter(Q(visibility='public') | Q(user=user)).annotate(
            likes_count=Count('like'),
            comment_count=Count('comment'),
            likes_user=Count('like', filter=Q(like__user=user))
        ).order_by('-created_date')

def get_blog_list_of_user(user_blog,user):
    if user.is_anonymous:
        return Blog.objects.filter(visibility='public',user=user_blog).annotate(
            likes_count=Count('like'),
            comment_count=Count('comment')
        ).order_by('-created_date')
    else:
        return Blog.objects.filter(Q(visibility='public',user=user_blog)|Q(user=user)).annotate(
            likes_count=Count('like'),
            comment_count=Count('comment'),
            likes_user=Count('like', filter=Q(like__user=user))
        ).order_by('-created_date')


def check_client_secret(stored_secret, provided_secret):
    return check_password(provided_secret, stored_secret)

from django.conf import settings

def send_verification_email(to_email, subject, message):
    send_mail(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        [to_email],
        fail_silently=False,
    )


from django.contrib.auth.models import Group


def get_group_permissions(group_name):
    try:
        # Lấy đối tượng nhóm theo tên
        group = Group.objects.get(name=group_name)

        # Lấy tất cả quyền gán cho nhóm
        permissions = group.permissions.all()

        # Trả về danh sách tên của quyền
        return [permission.name for permission in permissions]

    except Group.DoesNotExist:
        # Trả về thông báo nếu nhóm không tồn tại
        return None