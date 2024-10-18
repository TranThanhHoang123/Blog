from django.contrib.auth.models import Group
from BlogApp.models import *

def create_permissions(permissions):

    for perm in permissions:
        try:
            permission, created = Permission.objects.get_or_create(
                name = perm['name'],
                description = perm['description']
            )
            if created:
                print(f"Successfully created permission: {permission.name}")
            else:
                print(f"Permission already exists: {permission.name}")

        except Exception as e:
            print(f"Error creating permission: {e}")


def create_roles(roles):
    """
    Tạo các vai trò (Role) và các quyền (Permission) dựa trên danh sách đầu vào.

    :param roles: Danh sách các vai trò cần tạo.
    :type roles: list
    :return: Danh sách các vai trò đã được tạo hoặc cập nhật.
    """
    for rol in roles:
        try:
            # Tạo hoặc lấy vai trò (Role) dựa trên tên
            role, created = Role.objects.get_or_create(
                name=rol['name'],
                defaults={'description': rol['description']}
            )

            # Cập nhật mô tả nếu vai trò đã tồn tại
            if not created:
                role.description = rol['description']
                role.save()

            # Xử lý các quyền (Permission) cho vai trò
            for perm in rol['permissions']:
                try:
                    # Lấy quyền (Permission) dựa trên tên
                    permission = Permission.objects.get(name=perm['name'])

                    # Kiểm tra xem quyền đã có trong vai trò hay chưa
                    if role.permissions.filter(id=permission.id).exists():
                        print(f"Role {role.name} already has {permission.name}.")
                    else:
                        # Thêm quyền vào vai trò nếu chưa có
                        role.permissions.add(permission)
                        print(f"Successfully added {permission.name} to role {role.name}")

                except Permission.DoesNotExist:
                    print(f"Permission {perm['name']} not exists.")

            role.save()

        except Exception as e:
            print(f"Error creating role: {e}")


def add_users_for_role(user_roles):
    """
    Gán vai trò cho người dùng dựa trên danh sách đầu vào.

    :param user_roles: Danh sách chứa tên người dùng và vai trò tương ứng.
    :type user_roles: list
    """
    for user_role in user_roles:
        try:
            # Lấy user dựa trên username
            user = User.objects.get(username=user_role['username'])

            # Lấy role dựa trên tên vai trò
            role = Role.objects.get(name=user_role['role'])

            # Kiểm tra xem người dùng đã có role nào chưa
            if hasattr(user, 'user_role'):
                print(f"User {user.username} already has role {user.user_role.role.name}.")
            else:
                # Tạo vai trò cho người dùng nếu chưa có
                UserRole.objects.create(user=user, role=role)
                print(f"Successfully assigned role {role.name} to user {user.username}")

        except User.DoesNotExist:
            print(f"User {user_role['username']} not exists.")
        except Role.DoesNotExist:
            print(f"Role {user_role['role']} not exists.")
        except Exception as e:
            print(f"Error assigning role to user: {e}")


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
        vstorage = Vstorage.objects.get(VstorageCreadentialUsername=vstorage['username'])
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