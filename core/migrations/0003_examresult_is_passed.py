# Generated by Django 5.1.4 on 2024-12-07 19:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_exam_question_scores'),
    ]

    operations = [
        migrations.AddField(
            model_name='examresult',
            name='is_passed',
            field=models.BooleanField(default=False, verbose_name='Geçti mi?'),
        ),
    ]