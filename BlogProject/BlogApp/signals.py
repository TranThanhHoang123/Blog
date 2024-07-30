from django.db.models.signals import pre_save
from django.dispatch import receiver
import os
from django.conf import settings
from .models import User


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
