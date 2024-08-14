from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxLengthValidator
from django.contrib.auth.models import Group

class BaseModel(models.Model):
    created_date = models.DateTimeField(auto_now_add=True,null=True)
    updated_date = models.DateTimeField(auto_now=True,null=True)

    class Meta:
        abstract = True
class User(AbstractUser):
    phone_number = models.CharField(max_length=11,unique=True,null=True)
    email = models.CharField(max_length=40, unique=True)
    location = models.CharField(max_length=85,null=True)
    about = models.CharField(max_length=255,null=True,blank=True)
    profile_image = models.ImageField(upload_to='user/%Y/%m', null=True, blank=True)
    profile_bg = models.ImageField(upload_to='user/%Y/%m', null=True, blank=True)
    link = models.CharField(max_length=100,null=True)
    def __str__(self):
        return self.username


class Blog(BaseModel):
    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('private', 'Only Me'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.CharField(max_length=255)
    description = models.TextField(validators=[MaxLengthValidator(1000)])  # Giới hạn 1000 ký tự
    visibility = models.CharField(max_length=9, choices=VISIBILITY_CHOICES, default='public')
    likes_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)

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
    file = models.FileField(upload_to='comment/%Y/%m', null=True, blank=True)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='replies', on_delete=models.CASCADE)

    def __str__(self):
        return f'Comment by {self.user} on {self.blog}'


class BlogMedia(models.Model):
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name='media')
    file = models.FileField(upload_to='blog_media/%Y/%m')

    def __str__(self):
        return f'Media for blog {self.blog.id}'


class Company(models.Model):
    STATUS_CHOICES = [
        ('pending', 'pending'),
        ('approved', 'approved'),
        ('rejected', 'rejected'),
    ]
    name = models.CharField(max_length=60,null=True)
    founder = models.ForeignKey(User, related_name='companies', on_delete=models.SET_NULL,null=True,blank=True)# người tạo
    founding_date = models.DateField()
    workers_number = models.IntegerField()
    location = models.CharField(max_length=255)
    mail = models.EmailField()
    phone_number = models.CharField(max_length=20)
    link = models.URLField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')


class Recruitment(BaseModel):
    # company = models.ForeignKey(Company, related_name='recruitments', on_delete=models.CASCADE)
    owner = models.ForeignKey(User, related_name='recruitments', on_delete=models.SET_NULL,null=True,blank=True)# người tạo
    job_title = models.CharField(max_length=255)
    job_description = models.TextField()
    job_requirements = models.TextField()
    salary_range = models.CharField(max_length=100)
    location = models.CharField(max_length=255)
    apply_link = models.URLField()
    status = models.BooleanField(default=True)
    def __str__(self):
        return self.job_title


class JobApplication(BaseModel):
    STATUS_CHOICES = [
        ('pending', 'pending'),
        ('approved', 'approved'),
        ('rejected', 'rejected'),
    ]

    company = models.ForeignKey(Company, related_name='job_applications', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='job_applications', on_delete=models.CASCADE)
    job_title = models.CharField(max_length=255)
    cv = models.FileField(upload_to='cv/%Y/%m')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

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
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=3)
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expires_at


from django.db import models


class JobPost(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,null=True)
    WORK_TYPE_CHOICES = [
        ('full-time', 'full-time'),
        ('part-time', 'part-time'),
    ]
    work = models.CharField(max_length=10, choices=WORK_TYPE_CHOICES, default='full-time')
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
