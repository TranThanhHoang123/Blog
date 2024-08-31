from django.db.models import Q
from django.utils.crypto import get_random_string
from rest_framework import serializers
from .models import *
from . import my_paginations


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = '__all__'


class GroupListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name']


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'first_name', 'last_name', 'email', 'phone_number', 'location', 'about',
                  'profile_image', 'profile_bg', 'link']
        extra_kwargs = {
            'password': {'write_only': True},
            'location': {'required': False},
            'about': {'required': False},
            'profile_image': {'required': False},
            'profile_bg': {'required': False},
            'link': {'required': False},
            'form': {'required': False},
        }


from rest_framework import serializers
from .models import User, EmailVerificationCode
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_bytes

class UserRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'first_name', 'last_name', 'email', 'phone_number', 'location', 'about',
                  'profile_image', 'profile_bg', 'link']
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
            user = User.objects.create_user(**validated_data)
            user.is_active = False  # Set is_active to False by default
            user.save()

            # Create verification code
            code = get_random_string(length=6, allowed_chars='0123456789')
            EmailVerificationCode.objects.create(
                user=user,
                code=code,
                expires_at=timezone.now() + timedelta(minutes=3)
            )

            # Send activation email
            from . import utils
            utils.send_activation_email(user, code)

            return user

class ActivationSerializer(serializers.Serializer):
    uid = serializers.CharField()
    code = serializers.CharField()

    def validate(self, data):
        try:
            uid = force_bytes(urlsafe_base64_decode(data['uid']))
            user = User.objects.get(pk=uid)
            verification_code = EmailVerificationCode.objects.get(user=user, code=data['code'])

            if verification_code.is_expired():
                raise serializers.ValidationError({"code": "The activation code has expired."})
            if verification_code.status:
                raise serializers.ValidationError({"code": "The activation code has already been used."})
        except User.DoesNotExist:
            raise serializers.ValidationError({"uid": "Invalid user ID."})
        except EmailVerificationCode.DoesNotExist:
            raise serializers.ValidationError({"code": "Invalid activation code."})

        return data


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone_number', 'location', 'about', 'profile_image', 'profile_bg', 'link']
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
    groups = GroupListSerializer(many=True)

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
        fields = UserSerializer.Meta.fields + ['groups']


class UserListSerializer(UserDetailSerializer):
    class Meta(UserDetailSerializer.Meta):
        fields = ['id', 'username', 'first_name', 'last_name', 'profile_image', 'profile_bg']

class UserListForAdminSerializer(UserDetailSerializer):
    class Meta(UserDetailSerializer.Meta):
        fields = ['id', 'username', 'first_name', 'last_name', 'profile_image', 'profile_bg','phone_number','email']


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
        fields = ['user', 'id', 'content', 'description', 'visibility', 'likes_count', 'comment_count', 'media',
                  'liked']
        extra_kwargs = {
            'user': {'readonly': True},
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
        fields = ['user', 'id', 'content', 'description', 'visibility', 'likes_count', 'comment_count', 'media',
                  'created_date', 'updated_date', 'liked']

    def get_likes_count(self, obj):
        # Đã được tính trong QuerySet, không cần thiết phải làm lại ở đây
        return obj.likes_count

    def get_comment_count(self, obj):
        # Đã được tính trong QuerySet, không cần thiết phải làm lại ở đây
        return obj.comment_count

    def get_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
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
            user = User.objects.get(email=data['email'],is_active=True)
            reset_code = PasswordResetCode.objects.get(user=user, code=data['code'])
        except (User.DoesNotExist, PasswordResetCode.DoesNotExist):
            raise serializers.ValidationError("Invalid email or code.")

        if reset_code.is_expired():
            raise serializers.ValidationError("Verification code expired.")

        if reset_code.status:
            raise serializers.ValidationError("Verification code already used.")

        return data


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']

class JobPostTagSerializer(serializers.ModelSerializer):
    tag = TagSerializer()
    class Meta:
        model = JobPostTag
        fields = ['id', 'tag']

class JobPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPost
        fields = "__all__"
        extra_kwargs = {
            'user': {'read_only': True},
        }


class JobPostDetailSerializer(JobPostSerializer):
    user = UserListSerializer()
    tags = serializers.SerializerMethodField()

    def get_tags(self, obj):
        # Return the tags related to the JobPost instance
        return JobPostTagSerializer(obj.jobposttag_set.all().select_related('tag'), many=True).data

    class Meta(JobPostSerializer.Meta):
        fields = ['id','user','location','mail','phone_number','link','date','experience','quantity','job_detail','salary','content','tags']


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
            'status': {'required': False, 'read_only': True},
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
        fields = ['id', 'user', 'fullname', 'job_title','phone_number','email', 'cv', 'status', 'created_date']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class CategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

class ProductMediaSerializer(serializers.ModelSerializer):
    media = serializers.SerializerMethodField()
    def get_media(self, obj):
        if obj.media:
            # Lấy tên file hình ảnh từ đường dẫn được lưu trong trường image
            media = obj.media.name
            return self.context['request'].build_absolute_uri(f"/static/{media}")
    class Meta:
        model = ProductMedia
        fields = '__all__'  # Hoặc bạn có thể chỉ định từng trường cụ thể nếu muốn

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'
        extra_kwargs = {
            'user': {'read_only': True},
            'title': {'required': True},
            'quantity': {'required': True},
            'location': {'required': True},
            'category': {'required': True},
            'description': {'required': True},
            'price': {'required': True},
            'phone_number': {'required': True}
        }


class ProductUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'


class ProductDetailSerializer(serializers.ModelSerializer):
    medias = serializers.SerializerMethodField()
    categories = serializers.SerializerMethodField()
    user = UserListSerializer()

    # def get_file(self, obj):
    #     if obj.file:
    #         # Lấy tên file hình ảnh từ đường dẫn được lưu trong trường image
    #         file = obj.file.name
    #         return self.context['request'].build_absolute_uri(f"/static/{file}")

    def get_categories(self, obj):
        # Lấy danh sách categories liên kết với sản phẩm thông qua ProductCategory
        categories = Category.objects.filter(productcategory__product=obj)
        return CategoryListSerializer(categories, many=True, context=self.context).data

    def get_medias(self, obj):
        # Lấy danh sách categories liên kết với sản phẩm thông qua ProductCategory
        medias = ProductMedia.objects.filter(product=obj)
        return ProductMediaSerializer(medias, many=True, context=self.context).data

    class Meta:
        model = Product
        fields = ['user', 'id', 'title', 'phone_number', 'quantity', 'price', 'description', 'condition',
                  'fettle', 'location', 'created_date', 'updated_date', 'categories','medias']


class ProductListSerializer(ProductDetailSerializer):
    class Meta(ProductDetailSerializer.Meta):
        fields = ['user', 'id', 'title', 'price', 'created_date', 'updated_date', 'categories','medias']


class BannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = '__all__'
        extra_kwargs = {
            'user': {'read_only': True},
            'title': {'required': True},
            'image': {'required': True},
            'status': {'required': False},
            'description': {'required': True},
        }


class BannerDetailSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    def get_image(self, obj):
        if obj.image:
            # Lấy tên file hình ảnh từ đường dẫn được lưu trong trường image
            image = obj.image.name
            return self.context['request'].build_absolute_uri(f"/static/{image}")

    class Meta(BannerSerializer.Meta):
        pass


class BannerListSerializer(BannerDetailSerializer):
    class Meta(BannerDetailSerializer.Meta):
        fields = ['id', 'title','description','image','link']


class EmailVerificationCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailVerificationCode
        fields = ['code', 'expires_at', 'status']
        read_only_fields = ['expires_at', 'status']


class WebsiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Website
        fields = '__all__'

class WebsiteDetailSerializer(serializers.ModelSerializer):
    img = serializers.SerializerMethodField()

    def get_img(self, obj):
        if obj.img:
            # Lấy tên file hình ảnh từ đường dẫn được lưu trong trường image
            img = obj.img.name
            return self.context['request'].build_absolute_uri(f"/static/{img}")
    class Meta:
        model = Website
        fields = ['id','img', 'about', 'phone_number', 'mail', 'location', 'link']

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
