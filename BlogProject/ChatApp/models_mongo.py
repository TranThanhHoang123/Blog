import mongoengine as me
from datetime import datetime


# Model Chat
class Chat(me.Document):
    message = me.StringField(required=True)
    created_date = me.DateTimeField(default=datetime.utcnow)
    updated_date = me.DateTimeField(default=datetime.utcnow)
    user_id = me.IntField(required=True)
    group_id = me.StringField(required=True)  # Group ID của chat
    metadata = me.DictField()  # Lưu object metadata dưới dạng từ điển

    meta = {
        'collection': 'ChatApp_chat',  # Tên collection MongoDB
        'indexes': ['group_id'],  # Đánh chỉ mục theo group_id để tăng tốc tìm kiếm
        'ordering': ['-created_date']  # Sắp xếp các chat theo thứ tự thời gian
    }

