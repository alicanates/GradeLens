# Generated by Django 5.1.4 on 2024-12-13 17:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_userlog'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='department',
            field=models.CharField(choices=[('CENG', 'Bilgisayar Mühendisliği'), ('OTHER', 'Diğer')], default='OTHER', max_length=5, verbose_name='Bölüm'),
        ),
    ]
