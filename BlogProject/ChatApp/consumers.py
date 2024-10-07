from channels.consumer import AsyncConsumer
from channels.exceptions import StopConsumer, DenyConnection
import json
from channels.layers import get_channel_layer
from .models_mongo import Chat
from BlogApp.models import User
from datetime import datetime
from asgiref.sync import sync_to_async
from .serializers import ChatSerializer
from .utils import is_user_in_group,get_group_chat,message_transform,get_or_create_personal_group
from django.utils import timezone


class ChatAsyncConsumer(AsyncConsumer):
    async def websocket_connect(self, event):
        print('websocket connected', event)

        # Lấy id_group từ URL
        if 'id_group' not in self.scope['url_route']['kwargs']:
            await self.send({
                'type': 'websocket.close'
            })
            return

        self.group_id = self.scope['url_route']['kwargs']['id_group']
        self.group_name = f"group_{self.group_id}"

        # Lấy user từ scope
        self.user = self.scope['user']

        # Kiểm tra sự tồn tại của group chat
        group_chat = await get_group_chat(self.group_id)
        if not group_chat:
            # Trả về lỗi 404 nếu group chat không tồn tại
            await self.send({
                'type': 'websocket.close',
                'text': json.dumps({"error": "Group not found"}),
            })
            raise DenyConnection("Group not found")
        self.membership = await is_user_in_group(group_chat,self.user)
        # Kiểm tra nếu người dùng có phải là thành viên của nhóm
        if self.membership:
            # Thêm vào group
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            # Chấp nhận kết nối
            await self.send({
                'type': 'websocket.accept'
            })
        else:
            # Nếu người dùng không phải là thành viên, trả về lỗi 403
            await self.send({
                'type': 'websocket.close',
                'text': json.dumps({"error": "You are not in this group"}),
            })
            raise DenyConnection("You are not in this group")

    async def websocket_receive(self, event):
        print('Message Receive', event)
        # Kiểm tra nếu tin nhắn nhận được là chuỗi JSON
        try:
            message_data = json.loads(event['text'])  # Chuyển chuỗi thành dict
            # Kiểm tra xem có trường 'message' trong dữ liệu không
            if 'message' not in message_data:
                return  # Nếu không có trường 'message', không làm gì cả
            # Lưu tin nhắn vào MongoDB
            message_data['user_id']=self.user.id
            message_data['group_id']=self.group_id
            serializer = ChatSerializer(data=message_data)
            if serializer.is_valid():
                #lưu vào mongodb
                serializer.save()
                #biến đổi dữ liệu
                transformed_data = await message_transform(serializer.data, "http://127.0.0.1:8000")
                # Gửi tin nhắn vào nhóm
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "chat.message",
                        "message": json.dumps(transformed_data),  # Chuyển dict lại thành chuỗi JSON
                    }
                )
        except json.JSONDecodeError:
            # Nếu tin nhắn không hợp lệ, không làm gì cả hoặc xử lý lỗi
            return

    async def chat_message(self, event):
        # Lấy tin nhắn từ group_send và chuyển chuỗi JSON thành dict nếu cần
        message = event['message']
        print("Received message:", message)

        # Chuyển tin nhắn đã qua xử lý gửi lại cho client
        await self.send({
            'type': 'websocket.send',
            'text': message  # Gửi lại chuỗi JSON
        })

    async def websocket_disconnect(self, event):
        print('Websocket disconnect')
        print("channel", self.channel_layer, self.channel_name, self.group_name)
        # cập nhật time
        if self.membership:  # Kiểm tra nếu membership tồn tại
            # Cập nhật thời gian tương tác
            self.membership.interactive = timezone.now()
            await sync_to_async(self.membership.save)()  # Gọi save trong context async
        # Rời khỏi nhóm trước
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        # Dừng consumer
        raise StopConsumer()

    async def close_websocket(self):
        await self.send({
            'type': 'websocket.close'
        })



class PersonalChatAsyncConsumer(AsyncConsumer):
    async def websocket_connect(self, event):
        print('websocket connected', event)

        # Lấy id_group từ URL
        if 'to_user_id' not in self.scope['url_route']['kwargs']:
            await self.send({
                'type': 'websocket.close'
            })
            return
        # Lấy user từ scope
        self.user = self.scope['user']
        self.to_user_id = self.scope['url_route']['kwargs']['to_user_id']
        # Tạo group_id dựa trên user id
        user_ids = sorted([self.user.id, self.to_user_id])
        self.group_id = f"{user_ids[0]}_{user_ids[1]}"
        # Kiểm tra sự tồn tại của group chat
        self.personal_group = await get_or_create_personal_group(from_user=self.user, to_user_id=self.to_user_id)
        # Tên nhóm
        self.group_name = f"personal_{self.group_id}"

        # Thêm vào group
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        # Chấp nhận kết nối
        await self.send({
            'type': 'websocket.accept'
        })

    async def websocket_receive(self, event):
        print('Message Receive', event)
        # Kiểm tra nếu tin nhắn nhận được là chuỗi JSON
        try:
            message_data = json.loads(event['text'])  # Chuyển chuỗi thành dict
            # Kiểm tra xem có trường 'message' trong dữ liệu không
            if 'message' not in message_data:
                return  # Nếu không có trường 'message', không làm gì cả
            # Lưu tin nhắn vào MongoDB
            message_data['user_id']=self.user.id
            message_data['group_id']=self.group_id
            serializer = ChatSerializer(data=message_data)
            if serializer.is_valid():
                #lưu vào mongodb
                serializer.save()
                #biến đổi dữ liệu
                transformed_data = await message_transform(serializer.data, "http://127.0.0.1:8000")
                # Gửi tin nhắn vào nhóm
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "chat.message",
                        "message": json.dumps(transformed_data),  # Chuyển dict lại thành chuỗi JSON
                    }
                )
        except json.JSONDecodeError:
            # Nếu tin nhắn không hợp lệ, không làm gì cả hoặc xử lý lỗi
            return

    async def chat_message(self, event):
        # Lấy tin nhắn từ group_send và chuyển chuỗi JSON thành dict nếu cần
        message = event['message']
        print("Received message:", message)

        # Chuyển tin nhắn đã qua xử lý gửi lại cho client
        await self.send({
            'type': 'websocket.send',
            'text': message  # Gửi lại chuỗi JSON
        })

    async def websocket_disconnect(self, event):
        print('Websocket disconnect')
        print("channel", self.channel_layer, self.channel_name, self.group_name)
        # cập nhật time
        if self.personal_group:
            # Cập nhật thời gian tương tác
            self.personal_group.interactive = timezone.now()
            await sync_to_async(self.personal_group.save)()  # Gọi save trong context async
        # Rời khỏi nhóm trước
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        # Dừng consumer
        raise StopConsumer()

    async def close_websocket(self):
        await self.send({
            'type': 'websocket.close'
        })