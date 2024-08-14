from django.db.models.signals import pre_save,post_delete, post_save
from django.dispatch import receiver
import os
from django.conf import settings
from .models import *
from django.contrib.auth.models import Group,Permission

@receiver(post_delete, sender=BlogMedia)
def delete_media_file(sender, instance, **kwargs):
    instance.file.delete(False)

@receiver(pre_save, sender=User)
def delete_old_files(sender, instance, **kwargs):
    if instance.pk:
        old_instance = sender.objects.get(pk=instance.pk)

        # Check if profile_image has changed
        if old_instance.profile_image and old_instance.profile_image != instance.profile_image:
            old_profile_image_path = os.path.join(settings.MEDIA_ROOT, old_instance.profile_image.name)
            if os.path.isfile(old_profile_image_path):
                os.remove(old_profile_image_path)

        # Check if profile_bg has changed
        if old_instance.profile_bg and old_instance.profile_bg != instance.profile_bg:
            old_profile_bg_path = os.path.join(settings.MEDIA_ROOT, old_instance.profile_bg.name)
            if os.path.isfile(old_profile_bg_path):
                os.remove(old_profile_bg_path)

@receiver(post_delete, sender=Comment)
def delete_comment_file(sender, instance, **kwargs):
    if instance.file:
        instance.file.delete(False)


@receiver(post_delete, sender=Comment)
def delete_comment_file(sender, instance, **kwargs):
    if instance.file:
        instance.file.delete(save=False)


@receiver(pre_save, sender=Comment)
def handle_comment_file_update(sender, instance, **kwargs):
    if instance.pk:  # Đã có bản ghi trong cơ sở dữ liệu (đang cập nhật)
        try:
            old_instance = Comment.objects.get(pk=instance.pk)
        except Comment.DoesNotExist:
            old_instance = None

        if old_instance and old_instance.file and old_instance.file != instance.file:
            old_instance.file.delete(save=False)