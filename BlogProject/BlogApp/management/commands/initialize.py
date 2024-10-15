from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from . import utils
# Khởi tạo các quyền
PERMISSIONS = [
    {
        'codename': 'admin',
        'content_type': ContentType.objects.get_for_model(Group),
        'defaults': {'name': 'Admin Permission'}
    },
    {
        'codename': 'manager',
        'content_type': ContentType.objects.get_for_model(Group),
        'defaults': {'name': 'Manager Permission'}
    },
]
# Khởi tạo các Group
GROUPS = [
    {
        'name': 'admin',
        'priority':0
    },
    {
        'name': 'manager',
        'priority':1
    },
]
# Khởi tạo các quyền của admin
PERMISSIONS_GROUP_ADMIN = [
    {
        'codename': 'admin',
    },
]
# Khởi tạo các quyền của manager
PERMISSIONS_GROUP_MANAGER = [
    {
        'codename': 'manager',
    },
]
# Khởi tạo các account của admin
LOGIN = [
    {
        'username': 'Songnhatnguyen2024',
        'email':'admin@example.com',
        'password': 'SNN@2024'
    },
    {
        'username': 'H2htechenergy2024',
        'email':'admin@example.com',
        'password': '123'
    },
]
# Khởi tạo các account system admin
LOGIN_SYS_ADMIN = [
    {
        'username': 'sysadmin@zzz',
        'email':'Xlrdevteam03@gmail.com',
        'password': 'efu15v@gsdm#$'
    },
]
# Khởi tạo thành viên vào nhóm
MEMBERS = [
    {
        'username': 'Songnhatnguyen2024',
        'group': 'admin'
    },
    {
        'username': 'H2htechenergy2024',
        'group': 'admin'
    },
    {
        'username': 'sysadmin@zzz',
        'group': 'admin'
    }
]
#khởi tạo website
WEBSITE = {
    'img':'ico/default.ico',
    'about':'Công ty',
    'phone_number':'00000',
    'mail':'example@example.com',
    'location':'hehe',
    'link':'hehe'
}
TAGS = [
    {
        'name':'full-time'
    },
    {
        'name':'part-time'
    },
    {
        'name':'remote'
    }
]
VSTOTE = {
    'username':'1f0862c',
    'password':'y4PkwJq*',
    'project_id':'e2739f2170d44cfc8cfebf9aa23752b6',
}
class Command(BaseCommand):
    help = 'Khởi tạo quyền và nhóm'

    def handle(self, *args, **kwargs):
        # Khởi tạo Django
        from django.conf import settings
        import django
        django.setup()

        # Tạo quyền từ danh sách PERMISSIONS
        utils.create_permissions(PERMISSIONS)
        # Tạo group từ danh sách GROUPS
        utils.create_groups(GROUPS)
        # Thêm quyền vào nhóm 'admin'
        utils.add_permissions_to_group('admin', PERMISSIONS_GROUP_ADMIN)
        # Thêm quyền vào nhóm 'manager'
        utils.add_permissions_to_group('manager', PERMISSIONS_GROUP_MANAGER)

        #tạo staff user
        utils.create_staff_users(LOGIN)

        # tạo super user
        utils.create_super_users(LOGIN_SYS_ADMIN)

        # thêm member đến group
        utils.add_members_to_group(MEMBERS)
        self.stdout.write(self.style.SUCCESS('Successfully initialized permissions and groups'))

        # khởi tạo website
        utils.initialize_website()
        self.stdout.write(self.style.SUCCESS('Successfully initialized website'))

        #khởi tạo tag
        utils.create_initial_tags(TAGS)
        #khỏi tạo vstorage
        utils.create_vstorage(VSTOTE)
        #lấy token vstorage
        result = utils.get_vstorage_token(VSTOTE)
        print(result)
        self.stdout.write(self.style.SUCCESS('Successfully initialized tags'))