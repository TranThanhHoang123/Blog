# Generated by Django 5.0.6 on 2024-08-04 09:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('BlogApp', '0011_company_founder_alter_recruitment_company'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='name',
            field=models.CharField(max_length=60, null=True),
        ),
    ]