from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import Avg, Max, Min, StdDev
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
import os


def validate_question_scores(scores):
    """
    Soru puanlarının geçerliliğini kontrol eder.
    - Liste olmalı
    - Boş olmamalı
    - Her bir puan pozitif olmalı
    - Toplam 100 puan olmalı
    """
    if not isinstance(scores, list):
        raise ValidationError("Soru puanları liste formatında olmalıdır.")

    if not scores:
        raise ValidationError("Soru puanları boş olamaz.")

    if not all(isinstance(score, (int, float)) for score in scores):
        raise ValidationError("Tüm puanlar sayısal değer olmalıdır.")

    if not all(score >= 0 for score in scores):
        raise ValidationError("Puanlar negatif olamaz.")

    total = sum(scores)
    if abs(total - 100) > 0.01:  # Ondalık hassasiyeti için
        raise ValidationError("Toplam puan 100 olmalıdır.")


class Lecturer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    username = models.CharField(max_length=50, unique=True, verbose_name="Kullanıcı Adı")
    full_name = models.CharField(max_length=100, verbose_name="Ad Soyad")
    is_password_created = models.BooleanField(default=False, verbose_name="Parola Oluşturuldu mu?")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Öğretim Üyesi"
        verbose_name_plural = "Öğretim Üyeleri"

    def __str__(self):
        return self.username

    def get_user_auth(self):
        """Django authentication için User nesnesini döndürür"""
        if not self.user:
            return None
        return self.user

    def save(self, *args, **kwargs):
        # User nesnesi yoksa oluştur
        if not self.user:
            from django.contrib.auth.models import User
            user = User.objects.create_user(username=self.username)
            self.user = user
        super().save(*args, **kwargs)


class Course(models.Model):
    code = models.CharField(max_length=10, verbose_name="Ders Kodu", unique=True)
    name = models.CharField(max_length=100, verbose_name="Ders Adı")
    lecturer = models.ForeignKey(
        Lecturer,
        on_delete=models.SET_NULL,
        verbose_name="Öğretim Üyesi",
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ders"
        verbose_name_plural = "Dersler"

    def __str__(self):
        return f"{self.code} - {self.name}"


class Student(models.Model):
    DEPARTMENT_CHOICES = [
        ('CENG', 'Bilgisayar Mühendisliği'),
        ('OTHER', 'Diğer')
    ]

    student_number = models.CharField(max_length=20, unique=True, verbose_name="Öğrenci No")
    full_name = models.CharField(max_length=100, verbose_name="Ad Soyad")
    courses = models.ManyToManyField(Course, verbose_name="Aldığı Dersler", blank=True)
    department = models.CharField(
        max_length=5,
        choices=DEPARTMENT_CHOICES,
        default='OTHER',
        verbose_name="Bölüm"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Öğrenci"
        verbose_name_plural = "Öğrenciler"

    def __str__(self):
        return f"{self.student_number} - {self.full_name}"

    def save(self, *args, **kwargs):
        if not self.pk:  # Yeni kayıt oluşturuluyorsa
            # Öğrenci numarasından bölüm kodunu çıkar (3-6 arası karakterler)
            department_code = self.student_number[2:5]
            # Eğer bölüm kodu 253 ise Bilgisayar Mühendisliği
            self.department = 'CENG' if department_code == '253' else 'OTHER'
        super().save(*args, **kwargs)

    def get_course_average(self, course):
        """Öğrencinin bir dersteki ortalama puanını hesaplar"""
        results = self.examresult_set.filter(exam__course=course)
        if not results.exists():
            return None
        return results.aggregate(Avg('total_score'))['total_score__avg']

    def get_all_courses_average(self):
        """Öğrencinin tüm derslerinin ortalamasını hesaplar"""
        results = self.examresult_set.all()
        if not results.exists():
            return None
        return results.aggregate(Avg('total_score'))['total_score__avg']


class Exam(models.Model):
    EXAM_TYPE_CHOICES = [
        ('VIZE', 'Vize'),
        ('FINAL', 'Final'),
        ('BUTUNLEME', 'Bütünleme'),
        ('MAZERET', 'Mazeret'),
    ]

    SEMESTER_CHOICES = [
        ('GUZ', 'Güz'),
        ('BAHAR', 'Bahar'),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, verbose_name="Ders")
    semester = models.CharField(max_length=6, choices=SEMESTER_CHOICES, verbose_name="Dönem")
    exam_type = models.CharField(max_length=10, choices=EXAM_TYPE_CHOICES, verbose_name="Sınav Türü")
    exam_date = models.DateField(verbose_name="Sınav Tarihi")
    question_count = models.PositiveIntegerField(verbose_name="Soru Sayısı")
    question_scores = models.JSONField(
        verbose_name="Soru Puanları",
        validators=[validate_question_scores],
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Sınav"
        verbose_name_plural = "Sınavlar"
        unique_together = ['course', 'semester', 'exam_type']

    def __str__(self):
        return f"{self.course.code}_{self.semester} - {self.get_exam_type_display()}"

    def get_statistics(self):
        """Sınav istatistiklerini hesaplar"""
        results = self.examresult_set.all()
        if not results.exists():
            return None

        stats = results.aggregate(
            average=Avg('total_score'),
            max_score=Max('total_score'),
            min_score=Min('total_score'),
            std_dev=StdDev('total_score')
        )

        # Medyan hesaplama
        scores = list(results.values_list('total_score', flat=True).order_by('total_score'))
        if len(scores) % 2 == 0:
            median = (scores[len(scores) // 2 - 1] + scores[len(scores) // 2]) / 2
        else:
            median = scores[len(scores) // 2]

        stats['median'] = median
        return stats

    def delete(self, *args, **kwargs):
        """Sınav silinirken ilişkili kayıtları da sil"""
        try:
            # İlişkili ExamQuestionOutcome kayıtlarını sil
            self.examquestionoutcome_set.all().delete()
            # İlişkili ExamResult kayıtlarını sil
            self.examresult_set.all().delete()
        except Exception as e:
            print(f"Silme işlemi sırasında hata: {str(e)}")
        finally:
            # Her durumda sınavı sil
            super(Exam, self).delete(*args, **kwargs)


class ExamResult(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, verbose_name="Sınav")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name="Öğrenci")
    total_score = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Toplam Puan")
    question_scores = models.JSONField(verbose_name="Soru Bazlı Puanlar")
    is_passed = models.BooleanField(default=False, verbose_name="Geçti mi?")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Sınav Sonucu"
        verbose_name_plural = "Sınav Sonuçları"
        unique_together = ['exam', 'student']  # Bir öğrencinin aynı sınavda birden fazla sonucu olamaz
        indexes = [
            models.Index(fields=['exam', 'student']),
        ]

    def __str__(self):
        return f"{self.exam} - {self.student}"

    def clean(self):
        # Temel doğrulamalar
        if self.total_score < 0:
            raise ValidationError("Toplam puan negatif olamaz.")

        if not isinstance(self.question_scores, list):
            raise ValidationError("Soru puanları bir liste olmalıdır.")

        if not all(isinstance(score, (int, float)) for score in self.question_scores):
            raise ValidationError("Her bir soru puanı sayısal bir değer olmalıdır.")

        if abs(sum(self.question_scores) - float(self.total_score)) > 0.01:
            raise ValidationError("Toplam puan ile soru puanlarının toplamı uyuşmuyor.")

        if len(self.question_scores) != self.exam.question_count:
            raise ValidationError("Soru sayısı, sınavdaki soru sayısı ile eşleşmiyor.")

    def calculate_success_rate(self):
        """Her bir soru için başarı oranını hesaplar"""
        if not self.question_scores or not self.exam.question_scores:
            return None

        success_rates = []
        for student_score, max_score in zip(self.question_scores, self.exam.question_scores):
            rate = (Decimal(student_score) / Decimal(max_score)) * 100 if max_score > 0 else 0
            success_rates.append(round(rate, 2))
        return success_rates


class CourseOutcome(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, verbose_name="Ders")
    description = models.CharField(max_length=500, verbose_name="Kazanım Açıklaması")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ders Kazanımı"
        verbose_name_plural = "Ders Kazanımları"
        ordering = ['created_at']

    def __str__(self):
        return f"{self.course.code} - {self.description[:50]}"


class ExamQuestionOutcome(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, verbose_name="Sınav")
    question_number = models.PositiveIntegerField(verbose_name="Soru Numarası")
    outcome = models.ForeignKey(CourseOutcome, on_delete=models.CASCADE, verbose_name="Ders Kazanımı")
    contribution_percentage = models.PositiveIntegerField(
        verbose_name="Katkı Yüzdesi",
        validators=[
            MinValueValidator(1, message="Katkı yüzdesi en az 1 olmalıdır"),
            MaxValueValidator(100, message="Katkı yüzdesi en fazla 100 olmalıdır")
        ]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Sınav Sorusu Kazanımı"
        verbose_name_plural = "Sınav Sorusu Kazanımları"
        unique_together = ['exam', 'question_number', 'outcome']

    def clean(self):
        # Aynı kazanım için toplam yüzde kontrolü
        total_percentage = ExamQuestionOutcome.objects.filter(
            exam=self.exam,
            outcome=self.outcome
        ).exclude(pk=self.pk).aggregate(
            total=models.Sum('contribution_percentage')
        )['total'] or 0

        if total_percentage + self.contribution_percentage > 100:
            raise ValidationError(
                "Bu kazanım için toplam katkı yüzdesi 100'ü geçemez."
            )

    def __str__(self):
        return f"Sınav: {self.exam}, Soru: {self.question_number}, Kazanım: {self.outcome}"


class ExamPaper(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name="Öğrenci")
    file = models.FileField(upload_to='exam_papers/', verbose_name="Sınav Kağıdı")
    upload_date = models.DateTimeField(auto_now_add=True, verbose_name="Yükleme Tarihi")

    class Meta:
        verbose_name = "Sınav Kağıdı"
        verbose_name_plural = "Sınav Kağıtları"

    def __str__(self):
        return f"{self.student.student_number} - {self.file.name}"

    def get_file_path(self):
        return os.path.join(settings.MEDIA_ROOT, self.file.name)


class UserLog(models.Model):
    ACTIONS = [
        ('LOGIN', 'Giriş Yapıldı'),
        ('LOGOUT', 'Çıkış Yapıldı'),
        ('EXAM_UPLOAD', 'Sınav Yüklendi'),
        ('STUDENT_ADD', 'Öğrenci Eklendi'),
        ('OUTCOME_ADD', 'Kazanım Eklendi'),
        ('VIEW_REPORT', 'Rapor Görüntülendi'),
        ('EXAM_RESULT_MANUAL', 'Manuel Sınav Sonucu Girildi'),
    ]

    user = models.ForeignKey(Lecturer, on_delete=models.SET_NULL, null=True, verbose_name="Kullanıcı")
    action = models.CharField(max_length=50, choices=ACTIONS, verbose_name="Eylem")
    details = models.TextField(blank=True, null=True, verbose_name="Detaylar")
    ip_address = models.GenericIPAddressField(null=True, verbose_name="IP Adresi")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Tarih/Saat")

    class Meta:
        verbose_name = "Kullanıcı Logu"
        verbose_name_plural = "Kullanıcı Logları"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.full_name} - {self.get_action_display()} - {self.created_at}"
