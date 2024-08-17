from django.contrib.auth.hashers import check_password
from oauth2_provider.models import AccessToken, RefreshToken
from django.core.mail import send_mail
from django.db.models import Count, Q
from .models import *

def get_blog_details(blog_id, user):
    if user.is_anonymous:
        return Blog.objects.filter(id=blog_id).annotate(
            likes_count=Count('like',distinct=True),
            comment_count=Count('comment',distinct=True)
        ).first()
    else:
        return Blog.objects.filter(id=blog_id).annotate(
            likes_count=Count('like',distinct=True),
            comment_count=Count('comment',distinct=True),
            likes_user=Count('like', filter=Q(like__user=user))
        ).first()

def get_blog_list(user):
    if user.is_anonymous:
        return Blog.objects.filter(visibility='public').annotate(
            likes_count=Count('like',distinct=True),
            comment_count=Count('comment',distinct=True)
        ).order_by('-created_date')
    else:
        return Blog.objects.filter(Q(visibility='public') | Q(user=user)).annotate(
            likes_count=Count('like',distinct=True),
            comment_count=Count('comment',distinct=True),
            likes_user=Count('like', filter=Q(like__user=user))
        ).order_by('-created_date')

def get_blog_list_of_user(user_blog,user):
    if user.is_anonymous:
        return Blog.objects.filter(visibility='public',user=user_blog).annotate(
            likes_count=Count('like',distinct=True),
            comment_count=Count('comment',distinct=True)
        ).order_by('-created_date')
    else:
        return Blog.objects.filter(Q(visibility='public',user=user_blog)|Q(user=user)).annotate(
            likes_count=Count('like',distinct=True),
            comment_count=Count('comment',distinct=True),
            likes_user=Count('like', filter=Q(like__user=user))
        ).order_by('-created_date')


def check_client_secret(stored_secret, provided_secret):
    return check_password(provided_secret, stored_secret)

def has_admin_or_manager_permission(user):
    """
    Kiểm tra quyền của người dùng dựa trên nhóm.
    """
        # Kiểm tra xem người dùng có thuộc nhóm 'admin' hoặc 'manager' không
    return Group.objects.filter(user=user, name__in=['admin', 'manager']).exists()

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


def get_user_permissions_codes(user: User, group_id=None):
    """
    Trả về danh sách mã quyền từ nhóm mà người dùng thuộc về.
    :param user: Người dùng mà bạn muốn lấy quyền.
    :param group_id: ID của nhóm (Group) mà bạn muốn lấy quyền. Nếu không cung cấp, sẽ lấy quyền từ tất cả các nhóm mà người dùng thuộc về.
    :return: Danh sách các mã quyền (codename).
    """
    if not user.is_authenticated:
        return []

    if group_id:
        # Lấy quyền từ một nhóm cụ thể
        try:
            group = Group.objects.get(id=group_id)
            return list(group.permissions.values_list('codename', flat=True))
        except Group.DoesNotExist:
            return []  # Nếu nhóm không tồn tại, trả về danh sách rỗng
    else:
        # Lấy quyền từ tất cả các nhóm mà người dùng thuộc về
        user_groups = user.groups.all()
        permissions = set()
        for group in user_groups:
            permissions.update(group.permissions.values_list('codename', flat=True))
        return list(permissions)


def has_permission_to_modify_group(user, group):
    """
    Kiểm tra xem người dùng hiện tại có quyền chỉnh sửa nhóm hay không.

    :param user: Đối tượng người dùng hiện tại.
    :param group: Đối tượng nhóm cần kiểm tra quyền.
    :return: True nếu người dùng có quyền, False nếu không có quyền.
    """
    user_groups_priority = GroupPriority.objects.filter(group__user=user)

    if user_groups_priority.exists():
        # Nếu người dùng đã thuộc nhóm nào đó, kiểm tra mức độ ưu tiên
        user_highest_priority = user_groups_priority.order_by('priority').first().priority
        return user_highest_priority < group.grouppriority.priority

    return False  # Nếu người dùng không thuộc nhóm nào, mặc định không có quyền