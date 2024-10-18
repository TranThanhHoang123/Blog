from rest_framework.permissions import BasePermission
from django.contrib.auth.models import Group
from .models import UserRole
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

        return UserRole.objects.filter(user=request.user,role__name="admin").exists()

class HasPermission(BasePermission):
    """
        Checks if the user has the specified permission or is an admin/superuser.
        """

    def __init__(self, permission_name=None):
        self.permission_name = permission_name
    def has_permission(self, request, view):
        # Kiểm tra xem người dùng đã đăng nhập chưa
        if not request.user.is_authenticated:
            return False

        # Kiểm tra nếu người dùng là superuser
        if request.user.is_superuser:
            return True

        # Kiểm tra nếu người dùng có role admin
        if UserRole.objects.filter(user=request.user, role__name="admin").exists():
            return True

        # Nếu có parameter permission_name, kiểm tra xem user có quyền đó không
        if self.permission_name:
            # Kiểm tra quyền từ Role
            try:
                # Kiểm tra quyền từ Role
                return request.user.user_role.role.permissions.filter(name=self.permission_name).exists()
            except UserRole.DoesNotExist:
                # Trả về False nếu user không có user_role
                return False
        return False


class IsActiveUser(BasePermission):
    def has_permission(self, request, view):
        # Kiểm tra xem người dùng đã xác thực và is_active là True
        return bool(request.user and request.user.is_authenticated and request.user.is_active)