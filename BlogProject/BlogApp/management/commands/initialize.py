from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

class Command(BaseCommand):
    help = 'Khởi tạo quyền và nhóm'

    def handle(self, *args, **kwargs):
        # Khởi tạo Django
        from django.conf import settings
        import django
        django.setup()

        # Tạo quyền 'admin' nếu chưa tồn tại
        try:
            content_type = ContentType.objects.get_for_model(Permission)
            permission, created = Permission.objects.get_or_create(
                codename='admin',
                content_type=content_type,
                defaults={'name': 'Admin Permission'}
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating permission: {e}'))
            return

        # Tạo nhóm 'admin' nếu chưa tồn tại
        group, created = Group.objects.get_or_create(name='admin')

        # Thêm quyền vào nhóm nếu quyền chưa tồn tại trong nhóm
        if not group.permissions.filter(codename='admin').exists():
            group.permissions.add(permission)

        self.stdout.write(self.style.SUCCESS('Successfully initialized permissions and groups'))
