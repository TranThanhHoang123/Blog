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
        fields = ['first_name','last_name','phone_number', 'location', 'about', 'profile_image', 'profile_bg', 'link']
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
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
    user = UserListSerializer()
    liked = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    class Meta:
        model = Blog
        fields = ['user', 'id', 'content', 'description', 'visibility', 'likes_count', 'comment_count', 'media', 'liked']
        extra_kwargs = {
            'user':{'readonly': True},
            'content': {'required': True},
            'description': {'required': True},
            'likes_count': {'readonly': True},
            'comment_count': {'readonly': True},
            'liked': {'readonly': True},
        }

    def get_likes_count(self, obj):
        return Like.objects.filter(blog=obj).count()

    def get_comment_count(self, obj):
        return Comment.objects.filter(blog=obj).count()

    def get_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            user = request.user
            return Like.objects.filter(blog=obj, user=user).exists()
        return False

class BlogDetailSerializer(BlogSerializer):
    user = UserListSerializer()
    liked = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()

    class Meta:
        model = Blog
        fields = ['user', 'id', 'content', 'description', 'visibility', 'likes_count', 'comment_count', 'media', 'created_date', 'updated_date', 'liked']

    def get_likes_count(self, obj):
        # Đã được tính trong QuerySet, không cần thiết phải làm lại ở đây
        return obj.likes_count

    def get_comment_count(self, obj):
        # Đã được tính trong QuerySet, không cần thiết phải làm lại ở đây
        return obj.comment_count

    def get_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            user = request.user
            return obj.likes_user > 0  # `likes_user` được tính trong QuerySet
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


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is not correct")
        return value

    def validate_new_password(self, value):
        if self.context['request'].user.check_password(value):
            raise serializers.ValidationError("New password cannot be the same as the old password.")
        return value

    class Meta:
        fields = ['old_password', 'new_password']


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email not found.")
        return value


class VerifyCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True)

    def validate(self, data):
        try:
            user = User.objects.get(email=data['email'])
            reset_code = PasswordResetCode.objects.get(user=user, code=data['code'])
        except (User.DoesNotExist, PasswordResetCode.DoesNotExist):
            raise serializers.ValidationError("Invalid email or code.")

        if reset_code.is_expired():
            raise serializers.ValidationError("Verification code expired.")

        if reset_code.status:
            raise serializers.ValidationError("Verification code already used.")

        return data


class JobPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPost
        fields = "__all__"
        extra_kwargs = {
            'user': {'read_only': True},
        }

class JobPostDetailSerializer(serializers.ModelSerializer):
    user = UserListSerializer()
    class Meta:
        model = JobPost
        fields = "__all__"


class JobPostListSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)  # Hiển thị thông tin người dùng, chỉ đọc

    class Meta:
        model = JobPost
        exclude = ['job_detail']  # Loại bỏ trường `job_detail`


class JobApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobApplication
        fields = "__all__"
        extra_kwargs = {
            'user': {'read_only': True},
            'status': {'required': False,'read_only': True},
            'fullname': {'required': True},
            'phone_number': {'required': True},
            'email': {'required': True},
            'sex': {'required': True},
            'age': {'required': True},
        }


class JobApplicationDetailSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    cv = serializers.SerializerMethodField()
    job_post = JobPostListSerializer()
    def get_cv(self, obj):
        if obj.cv:
            # Lấy tên file hình ảnh từ đường dẫn được lưu trong trường image
            cv = obj.cv.name
            return self.context['request'].build_absolute_uri(f"/static/{cv}")
    class Meta:
        model = JobApplication
        fields = '__all__'


class JobApplicationListSerializer(serializers.ModelSerializer):
    user = UserListSerializer()
    cv = serializers.SerializerMethodField()

    def get_cv(self, obj):
        if obj.cv:
            # Lấy tên file hình ảnh từ đường dẫn được lưu trong trường image
            cv = obj.cv.name
            return self.context['request'].build_absolute_uri(f"/static/{cv}")
    class Meta:
        model = JobApplication
        fields = ['id', 'user','fullname','job_title', 'cv', 'status','created_date']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'



# class CompanySerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Company
#         fields = ['name','founding_date', 'workers_number', 'location', 'mail', 'phone_number', 'link']
#
# class CompanyDetailSerializer(CompanySerializer):
#     founder = UserListSerializer()
#     class Meta(CompanySerializer.Meta):
#         fields = ['id','founder'] + CompanySerializer.Meta.fields + ['status']
#
# class CompanyListSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Company
#         fields = ['id','name','founding_date', 'workers_number', 'location','status']
#
#
# class CompanyStatusUpdateSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Company
#         fields = ['status']
# class RecruitmentSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Recruitment
#         fields = '__all__'
#         read_only_fields = ['owner','company','status']
#
# class RecruitmentDetailSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Recruitment
#         fields = '__all__'
#
#
# class RecruitmentListSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Recruitment
#         fields = ['id','job_title','salary_range','status','created_date','updated_date']