# Generated by Django 5.1.1 on 2024-10-08 05:49

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('BlogApp', '0021_alter_jobapplication_cv_alter_website_img'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productmedia',
            name='media',
            field=models.URLField(max_length=1024, validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])]),
        ),
    ]