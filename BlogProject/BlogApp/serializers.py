from rest_framework import serializers
from .models import *
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id','username', 'password','first_name','last_name','email', 'phone_number', 'location', 'about', 'profile_image', 'profile_bg', 'link']
        extra_kwargs = {
            'password': {'write_only': True},
            'location': {'required': False},
            'about': {'required': False},
            'profile_image': {'required': False},
            'profile_bg': {'required': False},
            'link': {'required': False},
            'form': {'required': False},
        }

    def create(self, validated_data):
        data = validated_data.copy()
        user = User(**data)
        user.set_password(data['password'])
        user.save()
        return user

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['phone_number', 'location', 'about', 'profile_image', 'profile_bg', 'link']
        extra_kwargs = {
            'phone_number': {'required': False},
            'location': {'required': False},
            'about': {'required': False},
            'profile_image': {'required': False},
            'profile_bg': {'required': False},
            'link': {'required': False},
        }
class UserDetailSerializer(UserSerializer):
    profile_image = serializers.SerializerMethodField()
    profile_bg = serializers.SerializerMethodField()

    def get_profile_image(self, obj):
        if obj.profile_image:
            # Lấy tên file hình ảnh từ đường dẫn được lưu trong trường image
            profile_image = obj.profile_image.name
            return self.context['request'].build_absolute_uri(f"/static/{profile_image}")

    def get_profile_bg(self, obj):
        if obj.profile_bg:
            # Lấy tên file hình ảnh từ đường dẫn được lưu trong trường image
            profile_bg = obj.profile_bg.name
            return self.context['request'].build_absolute_uri(f"/static/{profile_bg}")

    class Meta(UserSerializer.Meta):
        pass

class UserListSerializer(UserDetailSerializer):
    class Meta(UserDetailSerializer.Meta):
        fields = ['id','username','first_name','last_name','profile_image','profile_bg']

class BlogMediaSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()

    def get_file(self, obj):
        if obj.file:
            # Lấy tên file hình ảnh từ đường dẫn được lưu trong trường image
            file = obj.file.name
            return self.context['request'].build_absolute_uri(f"/static/{file}")

    class Meta:
        model = BlogMedia
        fields = ['id', 'file']

class BlogSerializer(serializers.ModelSerializer):
    media = BlogMediaSerializer(many=True, required=False)
    class Meta:
        model = Blog
        fields = ['id','content', 'description', 'visibility', 'likes_count', 'comments_count','media']
        extra_kwargs = {
            'content': {'required': True},
            'description': {'required': True},
            'status': {'required': True},
            'likes_count': {'read_only': True},
            'comments_count': {'read_only': True},
        }

class BlogDetailSerializer(BlogSerializer):
    user = UserListSerializer()
    class Meta(BlogSerializer.Meta):
        fields = ['user'] + BlogSerializer.Meta.fields + ['created_date','updated_date']