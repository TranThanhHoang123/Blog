from django.db import models
from django.contrib.auth.models import AbstractUser


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
    description = models.CharField(max_length=255)
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
