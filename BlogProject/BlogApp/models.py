from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxLengthValidator
from django.contrib.auth.models import Group
from django.core.validators import FileExtensionValidator
from datetime import timedelta
from django.utils import timezone
import requests
class BaseModel(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
class User(AbstractUser):
    phone_number = models.CharField(max_length=11,unique=False)
    email = models.CharField(max_length=40, unique=False)
    location = models.CharField(max_length=85,null=True)
    about = models.CharField(max_length=255,null=True,blank=True)
    profile_image = models.URLField(
        max_length=600,
        default="https://hcm03.vstorage.vngcloud.vn/v1/AUTH_e2739f2170d44cfc8cfebf9aa23752b6/BlogApp/UserAvatar/default.png"
    )
    profile_bg = models.URLField(
        max_length=600,
        default='https://hcm03.vstorage.vngcloud.vn/v1/AUTH_e2739f2170d44cfc8cfebf9aa23752b6/BlogApp/UserBackground/default.png'
    )
    link = models.CharField(max_length=100,null=True)
    is_active = models.BooleanField(default=False)

    class Meta:
        unique_together = ('username','email','is_active')
    def __str__(self):
        return self.username

class Follow(models.Model):
    from_user = models.ForeignKey(User, related_name='following', on_delete=models.CASCADE)  # Thay đổi related_name
    to_user = models.ForeignKey(User, related_name='follower', on_delete=models.CASCADE)  # Thay đổi related_name
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['from_user', 'to_user'], name='unique_follow')
        ]

    def __str__(self):
        return f"{self.from_user} follows {self.to_user}"

class Blog(BaseModel):
    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('private', 'Only Me'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.CharField(max_length=255)
    description = models.TextField(validators=[MaxLengthValidator(4000)])  # Giới hạn 1000 ký tự
    visibility = models.CharField(max_length=9, choices=VISIBILITY_CHOICES, default='public')

    def __str__(self):
        return self.content

class Like(models.Model):
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True,null=True)

    class Meta:
        unique_together = ('blog', 'user')

    def __str__(self):
        return f'Like by {self.user} on {self.blog}'

class Comment(BaseModel):
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.CharField(max_length=255)
    file = models.URLField(
        null=True,
        blank=True,
        max_length=1024,
    )
    parent = models.ForeignKey('self', null=True, blank=True, related_name='replies', on_delete=models.CASCADE)

    def __str__(self):
        return f'Comment by {self.user} on {self.blog}'


class BlogMedia(models.Model):
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name='media')

    file = models.URLField(max_length=600)
    def __str__(self):
        return f'Media for blog {self.blog.id}'


class Website(models.Model):
    img = models.URLField(
        max_length=1024,
    )
    about = models.TextField(validators=[MaxLengthValidator(4000)])
    phone_number = models.CharField(max_length=20)
    mail = models.EmailField(max_length=255)
    location = models.CharField(max_length=255)
    link = models.URLField(max_length=255)

    def __str__(self):
        return f"Website: {self.about}"


# class Company(models.Model):
#     STATUS_CHOICES = [
#         ('pending', 'pending'),
#         ('approved', 'approved'),
#         ('rejected', 'rejected'),
#     ]
#     name = models.CharField(max_length=60,null=True)
#     founder = models.ForeignKey(User, related_name='companies', on_delete=models.SET_NULL,null=True,blank=True)# người tạo
#     founding_date = models.DateField()
#     workers_number = models.IntegerField()
#     location = models.CharField(max_length=255)
#     mail = models.EmailField()
#     phone_number = models.CharField(max_length=20)
#     link = models.URLField()
#     status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')


# class Recruitment(BaseModel):
#     # company = models.ForeignKey(Company, related_name='recruitments', on_delete=models.CASCADE)
#     owner = models.ForeignKey(User, related_name='recruitments', on_delete=models.SET_NULL,null=True,blank=True)# người tạo
#     job_title = models.CharField(max_length=255)
#     job_description = models.TextField()
#     job_requirements = models.TextField()
#     salary_range = models.CharField(max_length=100)
#     location = models.CharField(max_length=255)
#     apply_link = models.URLField()
#     status = models.BooleanField(default=True)
#     def __str__(self):
#         return self.job_title


class JobApplication(BaseModel):
    STATUS_CHOICES = [
        ('pending', 'pending'),
        ('approved', 'approved'),
        ('rejected', 'rejected'),
    ]

    job_post = models.ForeignKey('JobPost', related_name='job_applications', on_delete=models.CASCADE,null=True)
    user = models.ForeignKey(User, related_name='job_applications', on_delete=models.CASCADE)
    job_title = models.CharField(max_length=255)
    cv = models.URLField(
        max_length=1024,
    )
    fullname = models.CharField(max_length=50)
    phone_number = models.CharField(max_length=11)
    email = models.EmailField()
    sex = models.BooleanField(default=True)
    age = models.CharField(max_length=5) # ngày sinh
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    class Meta:
        unique_together = ('job_post', 'user')

    def __str__(self):
        return f'{self.job_title} - {self.user.username}'


from datetime import timedelta
from django.utils import timezone
class PasswordResetCode(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    expires_at = models.DateTimeField()
    updated_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.expires_at = timezone.now() + timedelta(minutes=3)  # Luôn cập nhật expires_at
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expires_at


class EmailVerificationCode(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    expires_at = models.DateTimeField()
    updated_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=3)
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expires_at

class JobPost(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE,null=True)
    location = models.CharField(max_length=255)
    mail = models.EmailField(max_length=255)
    phone_number = models.CharField(max_length=15)
    link = models.URLField(max_length=255, blank=True, null=True)
    date = models.DateTimeField()
    experience = models.CharField(max_length=255)
    quantity = models.IntegerField()
    job_detail = models.TextField()
    salary = models.CharField(max_length=255)
    content = models.CharField(max_length=255,null=False,blank=False)


class Tag(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

class JobPostTag(models.Model):
    job_post = models.ForeignKey(JobPost, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('job_post', 'tag')

    def __str__(self):
        return f'{self.job_post.content} - {self.tag.name}'

class Category(BaseModel):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Product(BaseModel):
    CONDITION_CHOICES = [
        ('new', 'New'),
        ('used', 'Used'),
    ]

    FETTLE_CHOICES = [
        ('in_stock', 'In Stock'),
        ('out_of_stock', 'Out of Stock'),
    ]

    title = models.CharField(max_length=60, null=False, blank=False)
    description = models.CharField(max_length=3000, null=False, blank=False)
    quantity = models.PositiveSmallIntegerField(null=False, blank=False)
    condition = models.CharField(max_length=10, choices=CONDITION_CHOICES, default='new')
    fettle = models.CharField(max_length=20, choices=FETTLE_CHOICES, default='in_stock')
    location = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    price = models.FloatField(null=True, blank=True)
    phone_number = models.CharField(max_length=11, null=True, blank=True)

    def __str__(self):
        return self.title


class ProductMedia(models.Model):
    product = models.ForeignKey(Product, related_name='medias', on_delete=models.CASCADE)
    media = models.URLField(
        max_length=1024,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])],
        null=False,
        blank=False
    )

    def __str__(self):
        return f"{self.product.title} - {self.file.name}"


class ProductCategory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('product', 'category')  # Unique together constraint

    def __str__(self):
        return f'{self.product.title} - {self.category.name}'


class Banner(BaseModel):
    STATUS_CHOICES = [
        ('show', 'Show'),
        ('hide', 'Hide'),
    ]

    title = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    image = models.URLField(
        max_length=1024,
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES,default='hide')
    link = models.URLField(max_length=255, blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT)

    def __str__(self):
        return self.title
#phân quyền
class Permission(models.Model):
    name = models.CharField(max_length=60, unique=True, blank=False, null=False)
    description = models.CharField(max_length=1000, blank=False, null=False)

    def __str__(self):
        return self.name

class Role(models.Model):
    name = models.CharField(max_length=60, unique=True, blank=False, null=False)
    description = models.CharField(max_length=1000, blank=False, null=False)
    permissions = models.ManyToManyField(Permission, related_name='roles')

    def __str__(self):
        return self.name

class UserRole(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_role')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='users')
    def __str__(self):
        return f"{self.user.username} - {self.role.name}"


class GroupPriority(models.Model):
    group = models.OneToOneField(Group, on_delete=models.CASCADE)
    priority = models.IntegerField(
        default=3,
        help_text="Priority level: 3 (lowest) to 0 (highest)"
    )

    class Meta:
        ordering = ['priority']

    def __str__(self):
        return f"{self.group.name} (Priority: {self.priority})"


class Vstorage(models.Model):
    VstorageCreadentialUsername = models.CharField(max_length=255, unique=True)
    VstorageCreadentialPassword = models.CharField(max_length=255)
    ProjectID = models.CharField(max_length=255, unique=True)
    X_Subject_Token = models.CharField(max_length=255, blank=True, null=True)
    url = models.URLField(max_length=500, blank=True, null=True)
    expired_at = models.DateTimeField(null=True, blank=True)  # Thêm trường expired_at

    def __str__(self):
        return self.VstorageCreadentialUsername

    def is_expired(self):
        """Kiểm tra xem token có hết hạn hay chưa."""
        return self.expired_at and timezone.now() >= self.expired_at

    def get_vstorage_token(self):
        print('get_vstorage_token')
        """Lấy token từ Vstorage và cập nhật nếu cần thiết."""
        if self.is_expired():
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
                                "name": self.VstorageCreadentialUsername,
                                "password": self.VstorageCreadentialPassword
                            }
                        }
                    },
                    "scope": {
                        "project": {
                            "domain": {"name": "default"},
                            "id": self.ProjectID
                        }
                    }
                }
            }

            # Thực hiện POST request
            response = requests.post(url, json=body, headers=headers)

            if response.status_code == 201:
                print('lấy vstorage_token thành công')
                x_subject_token = response.headers.get('X-Subject-Token')
                response_data = response.json()

                # Lấy expires_at = time.now() + 1 tiếng
                expires_at = timezone.now() + timedelta(hours=1)

                # Lấy url từ "catalog" -> "endpoints" -> [0] -> "url"
                catalog_url = response_data['token']['catalog'][0]['endpoints'][0]['url']

                # Cập nhật lại Vstorage
                self.X_Subject_Token = x_subject_token
                self.url = catalog_url
                self.expired_at = expires_at
                self.save()
            else:
                print('lấy vstorage_token thất bại')
                # Raise exception nếu response không thành công
                response.raise_for_status()
# class CompanyGroup(models.Model):
#     company = models.ForeignKey(Company, related_name='groups', on_delete=models.CASCADE)
#     group = models.OneToOneField(Group, related_name='company_group', on_delete=models.CASCADE)
#     def __str__(self):
#         return f"{self.company.name} - {self.group.name}"
#     #thêm các quyền
#     class Meta:
#         permissions = [
#             ("edit_company", "Can edit company"),
#             ("add_user_to_group", "Can add user to group"),
#             ("remove_user_from_group", "Can remove user from group"),
#             ("add_recruitment", "Can add recruitment"),
#             ("delete_recruitment", "Can delete recruitment"),
#             ("change_recruitment", "Can change recruitment"),
#             ("full_access_recruitment", "Full access to recruitment"),
#             ("create_job_application", "Can create job application"),
#             ("delete_job_application", "Can delete job application"),
#             ("change_job_application_status", "Can change job application status"),
#             ("full_access_job_application", "Full access to job application"),
#         ]