# Generated by Django 5.1.1 on 2024-10-07 10:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('BlogApp', '0015_groupchat_personalgroup_groupchatmembership'),
    ]

    operations = [
        migrations.AlterField(
            model_name='blogmedia',
            name='file',
            field=models.URLField(max_length=600),
        ),
    ]
