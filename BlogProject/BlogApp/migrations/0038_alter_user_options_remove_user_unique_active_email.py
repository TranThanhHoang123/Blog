# Generated by Django 5.0.7 on 2024-08-21 05:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('BlogApp', '0037_remove_user_unique_email_is_active_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='user',
            options={'verbose_name': 'user', 'verbose_name_plural': 'users'},
        ),
        migrations.RemoveConstraint(
            model_name='user',
            name='unique_active_email',
        ),
    ]