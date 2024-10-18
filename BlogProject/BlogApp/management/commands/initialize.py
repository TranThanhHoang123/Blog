from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from . import utils
import os
from dotenv import load_dotenv
# Nạp biến môi trường từ file .env
load_dotenv()
# Khởi tạo các quyền
MANAGER_PERMISSIONS = [
    {
        "name": "Thêm banner",
        "description": "Tạo banner quảng cáo"
    },
    {
        "name": "Xóa banner",
        "description": "Xóa banner quảng cáo"
    },
    {
        "name": "Sửa banner",
        "description": "Xóa banner quảng cáo"
    },
    {
        "name": "Thêm tag",
        "description": "Thêm tag vào hệ thống"
    },
    {
        "name": "Xóa tag",
        "description": "Xóa tag khỏi hệ thống"
    },
    {
        "name": "Sửa tag",
        "description": "Sửa tag trong hệ thống"
    },
    {
        "name": "Thêm category",
        "description": "Thêm category vào hệ thống"
    },
    {
        "name": "Xóa category",
        "description": "Xóa category khỏi hệ thống"
    },
    {
        "name": "Sửa category",
        "description": "Sửa category trong hệ thống"
    },
    {
        "name": "Xem thống kê người dùng",
        "description": "Xem thống kê tổng quát người dùng và chi tiết"
    },
    {
        "name": "Xem thống kê tin tuyển dụng",
        "description": "Xem thống kê tổng quát tin tuyển dụng và chi tiết"
    },
    {
        "name": "Xem thống kê tin sản phẩm",
        "description": "Xem thống kê tổng quát sản phẩm và chi tiết"
    },
]
ADMIN_PERMISSIONS = [
    {
        "name":"Xóa blog",
        "description":"Xóa bất kỳ bài blog nào"
    },
    {
        "name":"Xóa comment",
        "description":"Xóa bất kỳ bình luận"
    },
    {
        "name":"Xóa sản phẩm",
        "description":"Xóa bất kỳ sản phẩm nào"
    },
    {
        "name":"Xóa sản tin tuyển dụng",
        "description":"Xóa bất kỳ tin tuyển dụng nào"
    },
    {
        "name": "Xóa người dùng ra khỏi nhóm quyền",
        "description": "Xóa người dùng ra khỏi nhóm quyền(trừ nhóm admin)"
    },
    {
        "name":"Thay đổi quyền của người dùng",
        "description":"Thay đổi quyền của người dùng(trừ nhóm admin)"
    },
    {
        "name": "Xem quyền",
        "description":"Xem danh sách quyền"
    },
    {
        "name": "Xem nhóm quyền",
        "description":"Xem danh sách nhóm quyền"
    },
    {
        "name": "Xem tất cả người dùng",
        "description": "Xem danh sách tất cả người dùng"
    },
    {
        "name": "Thêm nhóm quyền",
        "description":"Xem danh sách nhóm quyền"
    },
    {
        "name": "Sửa nhóm quyền",
        "description":"Xem danh sách nhóm quyền(trừ nhóm admin)"
    },
    {
        "name": "Xóa nhóm quyền",
        "description":"Xem danh sách nhóm quyền(trừ nhóm admin)"
    },
]

ROLES = [
    {
        "name":"admin",
        "description":"Nhóm mặc đinh của admin.\nKhông thể sửa đổi, không thể xóa và thêm, xóa người dùng trong nhóm.",
        "permissions":ADMIN_PERMISSIONS+MANAGER_PERMISSIONS,
    },
    {
        "name":"manager",
        "description":"Nhóm mặc đinh của manager.\nKhông thể sửa đổi, không thể xóa quyền này.",
        "permissions":MANAGER_PERMISSIONS,
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
USERROLES = [
    {
        'username': 'Songnhatnguyen2024',
        'role': 'admin'
    },
    {
        'username': 'H2htechenergy2024',
        'role': 'admin'
    },
    {
        'username': 'sysadmin@zzz',
        'role': 'admin'
    }
]
#khởi tạo website
WEBSITE = {
    'img':'ico/default.ico',
    'about':'Công ty',
    'phone_number':'00000',
    'mail':'example@example.com',
    'location':'',
    'link':''
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
    'username':os.getenv('VSTORAGE_USERNAME'),
    'password':os.getenv('VSTORAGE_PASSWORD'),
    'project_id':os.getenv('VSTORAGE_PROJECT'),
}
class Command(BaseCommand):
    help = 'Khởi tạo quyền và nhóm'

    def handle(self, *args, **kwargs):
        # Khởi tạo Django
        from django.conf import settings
        import django
        django.setup()

        # Tạo quyền từ danh sách PERMISSIONS
        PERMISSIONS =  MANAGER_PERMISSIONS + ADMIN_PERMISSIONS
        utils.create_permissions(PERMISSIONS)
        self.stdout.write(self.style.SUCCESS('Successfully initialized permissions'))
        # Tạo group từ danh sách GROUPS
        utils.create_roles(ROLES)
        self.stdout.write(self.style.SUCCESS('Successfully initialized roles'))
        # Thêm vai trò cho user
        utils.add_users_for_role(USERROLES)
        self.stdout.write(self.style.SUCCESS('Successfully initialized user role'))
        #tạo staff user
        utils.create_staff_users(LOGIN)
        self.stdout.write(self.style.SUCCESS('Successfully initialized staff users'))
        # tạo super user
        utils.create_super_users(LOGIN_SYS_ADMIN)
        self.stdout.write(self.style.SUCCESS('Successfully initialized super users'))
        # khởi tạo website
        utils.initialize_website()
        self.stdout.write(self.style.SUCCESS('Successfully initialized website'))

        #khởi tạo tag
        utils.create_initial_tags(TAGS)
        self.stdout.write(self.style.SUCCESS('Successfully initialized tag'))
        #khỏi tạo vstorage
        utils.create_vstorage(VSTOTE)
        #lấy token vstorage
        result = utils.get_vstorage_token(VSTOTE)
        self.stdout.write(self.style.SUCCESS('Successfully initialized tags'))