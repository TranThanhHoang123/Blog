# Generated by Django 5.1.1 on 2024-10-07 14:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('BlogApp', '0018_alter_jobapplication_cv'),
    ]

    operations = [
        migrations.AlterField(
            model_name='groupchat',
            name='image',
            field=models.URLField(blank=True, max_length=1024, null=True),
        ),
    ]
