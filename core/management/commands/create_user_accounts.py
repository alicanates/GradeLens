from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Lecturer


class Command(BaseCommand):
    help = 'Mevcut öğretim üyeleri için User nesneleri oluşturur'

    def handle(self, *args, **kwargs):
        lecturers = Lecturer.objects.filter(user__isnull=True)
        created_count = 0

        for lecturer in lecturers:
            try:
                user = User.objects.create_user(
                    username=lecturer.username,
                    password=None  # Parola null olarak ayarlanır
                )
                lecturer.user = user
                lecturer.save()
                created_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f'"{lecturer.full_name}" için User nesnesi oluşturuldu.'
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f'HATA - "{lecturer.full_name}" için User nesnesi oluşturulamadı: {str(e)}'
                ))

        self.stdout.write(self.style.SUCCESS(
            f'Toplam {created_count} User nesnesi oluşturuldu.'
        ))