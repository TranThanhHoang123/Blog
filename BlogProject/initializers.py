import os
import django

# Thiết lập môi trường Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BlogProject.settings')
django.setup()

from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType

def initialize_data():
    # Tạo nhóm Admin và Manager
    admin_group, _ = Group.objects.get_or_create(name='Admin')
    manager_group, _ = Group.objects.get_or_create(name='Manager')

    # Tạo quyền Admin và Manager
    admin_permission, _ = Permission.objects.get_or_create(
        codename='can_admin',
        name='Can Admin',
        content_type=ContentType.objects.get_for_model(Group)
    )

    manager_permission, _ = Permission.objects.get_or_create(
        codename='can_manager',
        name='Can Manager',
        content_type=ContentType.objects.get_for_model(Group)
    )

    # Thêm quyền Admin vào nhóm Admin
    admin_group.permissions.add(admin_permission)

    # Tạo tài khoản Admin
    sysadmin, _ = User.objects.get_or_create(username='sysadmin')
    if not sysadmin.password:
        sysadmin.set_password('sn@9@9@9@9')
        sysadmin.is_staff = True
        sysadmin.is_superuser = True
        sysadmin.save()

    snadmin, _ = User.objects.get_or_create(username='snadmin')
    if not snadmin.password:
        snadmin.set_password('sn@9@9@9@9')
        snadmin.is_staff = True
        snadmin.is_superuser = False
        snadmin.save()

    # Thêm 2 tài khoản Admin vào nhóm Admin
    sysadmin.groups.add(admin_group)
    snadmin.groups.add(admin_group)

if __name__ == '__main__':
    initialize_data()
    print("Initialization completed.")
