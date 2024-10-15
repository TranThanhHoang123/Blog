from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from BlogApp.models import *

def create_permissions(permission_list):
    """
    Tạo các quyền dựa trên danh sách đầu vào.

    :param permission_list: Danh sách các quyền cần tạo.
    :type permission_list: list
    :return: Danh sách các quyền đã được tạo hoặc tồn tại.
    """
    created_permissions = []

    for perm in permission_list:
        try:
            permission, created = Permission.objects.get_or_create(
                codename=perm['codename'],
                content_type=perm['content_type'],
                defaults=perm['defaults']
            )
            if created:
                print(f"Successfully created permission: {permission.codename}")
            else:
                print(f"Permission already exists: {permission.codename}")

            created_permissions.append(permission)

        except Exception as e:
            print(f"Error creating permission '{perm['codename']}': {e}")

    #giải phóng bộ nhớ
    del permission_list


def create_groups(group_list):
    """
    Tạo các nhóm dựa trên danh sách đầu vào và xóa danh sách sau khi đã sử dụng.

    :param group_list: Danh sách các nhóm cần tạo.
    :type group_list: list
    :return: Danh sách các nhóm đã được tạo mới.
    """
    for grp in group_list:
        try:
            # Tạo hoặc lấy nhóm dựa trên tên
            group, created = Group.objects.get_or_create(name=grp['name'])

            if created:
                # Nếu nhóm mới được tạo, tạo và lưu priority cho nhóm đó
                GroupPriority.objects.create(group=group, priority=grp['priority'])
                print(f"Successfully created group: {group.name} with priority {grp['priority']}")
            else:
                # Nếu nhóm đã tồn tại, kiểm tra và cập nhật priority nếu cần
                group_priority, created = GroupPriority.objects.get_or_create(group=group)
                if group_priority.priority != grp['priority']:
                    group_priority.priority = grp['priority']
                    group_priority.save()
                    print(f"Updated priority for group: {group.name} to {grp['priority']}")
                else:
                    print(f"Group already exists with correct priority: {group.name}")

        except Exception as e:
            print(f"Error creating or updating group '{grp['name']}': {e}")

    # Xóa mảng group_list để giải phóng bộ nhớ
    del group_list
    return


def add_permissions_to_group(group_name, permissions_list):
    """
    Thêm danh sách quyền vào nhóm dựa trên tên nhóm và danh sách mã quyền.

    :param group_name: Tên của nhóm cần thêm quyền.
    :type group_name: str
    :param permissions_list: Danh sách các từ điển chứa mã quyền.
    :type permissions_list: list
    """
    try:
        # Lấy hoặc tạo nhóm dựa trên tên
        group, created = Group.objects.get_or_create(name=group_name)
        if created:
            print(f"Successfully created group: {group.name}")
        else:
            print(f"Group already exists: {group.name}")

        # Duyệt qua danh sách quyền và thêm vào nhóm
        for perm_dict in permissions_list:
            try:
                permission = Permission.objects.get(codename=perm_dict['codename'])
                group.permissions.add(permission)
                print(f"Added permission '{permission.codename}' to group '{group.name}'")
            except Permission.DoesNotExist:
                print(f"Permission with codename '{perm_dict['codename']}' does not exist.")
        del permissions_list
    except Exception as e:
        print(f"Error processing group '{group_name}': {e}")

def create_staff_users(login_list):
    """
    Tạo các user với is_staff=True và is_superuser=False.

    :param login_list: Danh sách các từ điển chứa thông tin đăng nhập của người dùng.
    :type login_list: list
    """
    for login_info in login_list:
        username = login_info.get('username')
        password = login_info.get('password')
        email = login_info.get('email')
        if not username or not password:
            print("Username and password are required.")
            continue

        try:
            # Kiểm tra xem user có tồn tại không
            user, created = User.objects.get_or_create(
                username=username,
                email=email,
                defaults={
                    'is_staff': True,
                    'is_superuser': True,
                    'is_active':True
                }
            )

            if created:
                user.set_password(password)
                user.save()
                print(f"Successfully created staff user: {username}")
            else:
                print(f"User '{username}' already exists.")

        except Exception as e:
            print(f"Error creating user '{username}': {e}")



def create_super_users(login_list):
    """
    Tạo các user với is_staff=True và is_superuser=True.

    :param login_list: Danh sách các từ điển chứa thông tin đăng nhập của người dùng.
    :type login_list: list
    """
    for login_info in login_list:
        username = login_info.get('username')
        password = login_info.get('password')
        email = login_info.get('email')
        if not username or not password:
            print("Username and password are required.")
            continue

        try:
            # Kiểm tra xem user có tồn tại không
            user, created = User.objects.get_or_create(
                username=username,
                email = email,
                defaults={
                    'is_staff': True,
                    'is_superuser': True,
                    'is_active': True
                }
            )

            if created:
                user.set_password(password)
                user.save()
                print(f"Successfully created staff user: {username}")
            else:
                print(f"User '{username}' already exists.")

        except Exception as e:
            print(f"Error creating user '{username}': {e}")


def add_members_to_group(members_list):
    """
    Thêm các thành viên vào nhóm dựa trên username và tên nhóm.

    :param members_list: Danh sách các từ điển chứa thông tin thành viên và nhóm.
    :type members_list: list
    """
    for member_info in members_list:
        username = member_info.get('username')
        group_name = member_info.get('group')

        if not username or not group_name:
            print("Both username and group name are required.")
            continue

        try:
            # Tìm kiếm user theo username
            user = User.objects.get(username=username)

            # Tìm kiếm hoặc tạo nhóm theo tên
            group, created = Group.objects.get_or_create(name=group_name)

            # Thêm user vào nhóm
            group.user_set.add(user)
            print(f"Successfully added user '{username}' to group '{group_name}'")

        except User.DoesNotExist:
            print(f"User '{username}' does not exist.")
        except Exception as e:
            print(f"Error adding user '{username}' to group '{group_name}': {e}")


def initialize_website():
    WEBSITE = {
        'img': 'ico/default.ico',
        'about': 'Công ty',
        'phone_number': '00000',
        'mail': 'example@example.com',
        'location': 'hehe',
        'link': 'hehe'
    }

    # Kiểm tra xem một đối tượng Website đã tồn tại chưa
    if not Website.objects.exists():
        # Nếu chưa, tạo một đối tượng mới
        Website.objects.create(**WEBSITE)
        print("Website initialized.")
    else:
        print("Website already exists.")


def create_initial_tags(TAGS):
    for tag_data in TAGS:
        Tag.objects.get_or_create(**tag_data)

#init vstorage
def create_vstorage(vstote):
    # Extract information from the VSTOTE dictionary
    try:
        username = vstote.get('username')
        password = vstote.get('password')
        project_id = vstote.get('project_id')
        # Create a new Vstorage object and save it to the database
        vstorage = Vstorage.objects.create(
            VstorageCreadentialUsername=username,
            VstorageCreadentialPassword=password,
            ProjectID=project_id,
        )
        print('Initialize Vstorage completed')
    except:
        pass


from datetime import timedelta
from django.utils import timezone
import requests


def get_vstorage_token(vstorage):
    try:
        vstorage = Vstorage.objects.filter(VstorageCreadentialUsername=vstorage.get('username')).first()
    except Vstorage.DoesNotExist:
        return {"error": "Vstorage not found"}

    # URL cho API
    url = "https://hcm03.auth.vstorage.vngcloud.vn/v3/auth/tokens"

    # Header cho request
    headers = {
        'Content-Type': 'application/json'
    }

    # Body của request
    body = {
        "auth": {
            "identity": {
                "methods": ["password"],
                "password": {
                    "user": {
                        "domain": {"name": "default"},
                        "name": vstorage.VstorageCreadentialUsername,
                        "password": vstorage.VstorageCreadentialPassword
                    }
                }
            },
            "scope": {
                "project": {
                    "domain": {"name": "default"},
                    "id": vstorage.ProjectID
                }
            }
        }
    }

    # Thực hiện POST request
    response = requests.post(url, json=body, headers=headers)

    if response.status_code == 201:
        x_subject_token = response.headers.get('X-Subject-Token')
        response_data = response.json()

        # Lấy expires_at = time.now() + 1 tiếng
        expires_at = timezone.now() + timedelta(hours=1)  # Sử dụng pytz để gán múi giờ UTC

        # Lấy url từ "catalog" -> "endpoints" -> [0] -> "url"
        catalog_url = response_data['token']['catalog'][0]['endpoints'][0]['url']

        # Cập nhật lại Vstorage
        vstorage.X_Subject_Token = x_subject_token
        vstorage.url = catalog_url
        vstorage.expired_at = expires_at
        vstorage.save()

        print("Vstorage updated successfully")
    else:
        print(f"Failed to retrieve token, status code: {response.status_code}")
        print(f"detail:{response.json()}")