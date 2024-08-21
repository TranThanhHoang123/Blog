from rest_framework.permissions import BasePermission
from django.contrib.auth.models import Group
class IsAdminOrManager(BasePermission):
    """
    Custom permission to only allow access to authenticated users who are admin, manager, or superuser.
    """
    def has_permission(self, request, view):
        # Kiểm tra xem người dùng đã đăng nhập chưa
        if not request.user.is_authenticated:
            return False

        # Kiểm tra nếu người dùng là superuser
        if request.user.is_superuser:
            return True

        # Kiểm tra xem người dùng có thuộc nhóm 'admin' hoặc 'manager' không
        return Group.objects.filter(user=request.user, name__in=['admin', 'manager']).exists()


class IsAdmin(BasePermission):
    """
    admin or superuser.
    """
    def has_permission(self, request, view):
        # Kiểm tra xem người dùng đã đăng nhập chưa
        if not request.user.is_authenticated:
            return False

        # Kiểm tra nếu người dùng là superuser
        if request.user.is_superuser:
            return True

        # Kiểm tra xem người dùng có thuộc nhóm 'admin' hoặc 'manager' không
        return Group.objects.filter(user=request.user, name='admin').exists()


class IsActiveUser(BasePermission):
    def has_permission(self, request, view):
        # Kiểm tra xem người dùng đã xác thực và is_active là True
        return bool(request.user and request.user.is_authenticated and request.user.is_active)