from channels.db import database_sync_to_async
from BlogApp.models import GroupChatMembership,GroupChat,User,PersonalGroup
from django.utils import timezone
from asgiref.sync import sync_to_async

@database_sync_to_async
def is_user_in_group(group_chat, user):
    """
    Kiểm tra xem người dùng có phải là thành viên của nhóm hay không.
    Cập nhật thời gian tương tác nếu người dùng là thành viên.

    :param group_chat: Một instance của GroupChat.
    :param user: Một instance của User.
    :return: True nếu người dùng là thành viên của nhóm, False nếu không.
    """
    membership = GroupChatMembership.objects.filter(group_chat=group_chat, user=user).first()
    if membership:
        # Cập nhật trường interactive thành thời gian hiện tại
        membership.interactive = timezone.now()
        membership.save()
        return membership
    return None


@database_sync_to_async
def get_group_chat(group_chat_id):
        try:
            return GroupChat.objects.get(id=group_chat_id)
        except GroupChat.DoesNotExist:
            return None


@database_sync_to_async
def message_transform(message_data, url_path):
    try:
        # Lấy thông tin người dùng từ ID
        user = User.objects.get(id=message_data['user_id'])

        # Thêm dữ liệu người dùng vào message_data
        message_data['user'] = {
            'id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'username': user.username,
            'profile_image': user.profile_image,
            'profile_bg': user.profile_bg
        }
    except User.DoesNotExist:
        # Nếu người dùng không tồn tại, gán giá trị None cho trường user
        message_data['user'] = None

    return message_data




def is_user_in_group_sync(group_chat, user):
    """
    Kiểm tra xem người dùng có phải là thành viên của nhóm hay không.
    Cập nhật thời gian tương tác nếu người dùng là thành viên.

    :param group_chat: Một instance của GroupChat.
    :param user: Một instance của User.
    :return: True nếu người dùng là thành viên của nhóm, False nếu không.
    """
    membership = GroupChatMembership.objects.filter(group_chat=group_chat, user=user).first()
    if membership:
        # Cập nhật trường interactive thành thời gian hiện tại
        membership.interactive = timezone.now()
        membership.save()
        return True
    return False


@database_sync_to_async
def get_or_create_personal_group(from_user, to_user_id):
    # Lấy đối tượng người dùng từ ID
    to_user = User.objects.get(id=to_user_id)

    # Kiểm tra xem có nhóm nào chứa hai người dùng này không
    group = PersonalGroup.objects.filter(user=from_user).filter(user=to_user).first()

    # Nếu nhóm không tồn tại, tạo nhóm mới
    if not group:
        group = PersonalGroup.objects.create()  # Tạo nhóm mới
        group.user.add(from_user, to_user)  # Thêm 2 người dùng vào nhóm

    return group
