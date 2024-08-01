from rest_framework import serializers
from .models import *
from . import my_paginations
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
    liked = serializers.SerializerMethodField()

    class Meta(BlogSerializer.Meta):
        fields = ['user'] + BlogSerializer.Meta.fields + ['created_date', 'updated_date', 'liked']

    def get_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            user = request.user
            return Like.objects.filter(blog=obj, user=user).exists()
        return False


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['id', 'blog', 'user', 'content', 'file', 'parent', 'created_date', 'updated_date']
        read_only_fields = ['user', 'created_date', 'updated_date']

class CommentListSerializer(CommentSerializer):
    user = UserListSerializer()
    file = serializers.SerializerMethodField()

    def get_file(self, obj):
        if obj.file:
            # Lấy tên file hình ảnh từ đường dẫn được lưu trong trường image
            file = obj.file.name
            return self.context['request'].build_absolute_uri(f"/static/{file}")

    class Meta(CommentSerializer.Meta):
       pass


class BlogDetailWithCommentsSerializer(serializers.Serializer):
    blog = BlogDetailSerializer()
    comments = serializers.SerializerMethodField()

    def get_comments(self, obj):
        request = self.context['request']
        comments = Comment.objects.filter(blog=obj).order_by('-created_date')
        paginator = my_paginations.CommentPagination()
        page = paginator.paginate_queryset(comments, request)
        serializer = CommentListSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data).data

    def to_representation(self, instance):
        representation = {
            'blog': BlogDetailSerializer(instance, context=self.context).data,
            'comments': self.get_comments(instance)
        }
        return representation