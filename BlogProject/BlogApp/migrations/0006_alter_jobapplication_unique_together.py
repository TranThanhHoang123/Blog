# Generated by Django 5.0.7 on 2024-09-04 09:19

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('BlogApp', '0005_alter_jobapplication_age'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='jobapplication',
            unique_together={('job_post', 'user')},
        ),
    ]