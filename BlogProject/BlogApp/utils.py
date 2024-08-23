from django.contrib.auth.hashers import check_password
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from oauth2_provider.models import AccessToken, RefreshToken
from django.core.mail import send_mail
from django.db.models import Count, Q
from .models import *
from django.conf import settings

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

def send_verification_email(to_email, subject, message):
    send_mail(
        #Tiêu đề
        subject,
        #Nội dung
        message,
        #thangf gửi
        settings.EMAIL_HOST_USER,
        #thằng nhận
        [to_email],
        fail_silently=False,
    )

def send_activation_email(user, code):
    subject = 'Activate Your Account'
    message = f"Hi {user.username},\n\nPlease click the link below to activate your account:\n\n" \
              f"{settings.DOMAIN}/user/activate/{urlsafe_base64_encode(force_bytes(user.pk))}/{code}/\n\n" \
              f"The activation link will expire in 3 minutes.\n\nBest regards,\nThe Team"
    send_mail(subject, message, settings.EMAIL_HOST_USER, [user.email])


from django.contrib.auth.models import Group


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
import re
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
import os
import io

def sanitize_filename(filename):
    """Xóa các ký tự đặc biệt và giữ lại các ký tự an toàn trong tên tập tin."""
    return re.sub(r'[^\w\s.-]', '', filename)

def convert_to_jpeg(file):
    try:
        # Mở tập tin hình ảnh
        image = Image.open(file)
        image = image.convert('RGB')

        # Tạo bộ đệm để lưu tập tin JPEG
        buffer = BytesIO()
        image.save(buffer, format='JPEG')
        buffer.seek(0)

        return ContentFile(buffer.read(), name=f"{os.path.splitext(file.name)[0]}.jpeg")
    except Exception as e:
        # Xử lý lỗi và giữ tập tin gốc với phần mở rộng .jpeg
        print(f"Error converting file to JPEG: {e}")
        file.seek(0)
        return ContentFile(file.read(), name=f"{os.path.splitext(file.name)[0]}.jpeg")

from PyPDF2 import PdfFileReader, PdfFileWriter
def convert_to_pdf(file):
    try:
        # Đọc nội dung file
        buffer = BytesIO(file.read())

        # Đặt tên file với phần mở rộng .pdf
        pdf_filename = f"{os.path.splitext(file.name)[0]}.pdf"

        # Trả về file dưới dạng ContentFile với phần mở rộng .pdf
        return ContentFile(buffer.getvalue(), name=pdf_filename)

    except Exception as e:
        # Xử lý lỗi và giữ tập tin gốc với phần mở rộng .pdf
        print(f"Error converting file to PDF: {e}")
        file.seek(0)
        return ContentFile(file.read(), name=f"{os.path.splitext(file.name)[0]}.pdf")