# Generated by Django 5.1.1 on 2024-10-07 14:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('BlogApp', '0020_alter_website_img'),
    ]

    operations = [
        migrations.AlterField(
            model_name='jobapplication',
            name='cv',
            field=models.URLField(max_length=1024),
        ),
        migrations.AlterField(
            model_name='website',
            name='img',
            field=models.URLField(max_length=1024),
        ),
    ]
