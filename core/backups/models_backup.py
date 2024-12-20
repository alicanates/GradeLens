from django.db import models
from django.core.exceptions import ValidationError

class Lecturer(models.Model):
    username = models.CharField(max_length=50, unique=True, verbose_name="Kullanıcı Adı")
    full_name = models.CharField(max_length=100, verbose_name="Ad Soyad")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Öğretim Üyesi"
        verbose_name_plural = "Öğretim Üyeleri"

    def __str__(self):
        return self.username

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
    student_number = models.CharField(max_length=20, unique=True, verbose_name="Öğrenci No")
    full_name = models.CharField(max_length=100, verbose_name="Ad Soyad")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Öğrenci"
        verbose_name_plural = "Öğrenciler"

    def __str__(self):
        return f"{self.student_number} - {self.full_name}"

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
        null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Sınav"
        verbose_name_plural = "Sınavlar"
        unique_together = ['course', 'semester', 'exam_type']  # Aynı dersin aynı dönemde aynı türde birden fazla sınavı olamaz

    def __str__(self):
        return f"{self.course.code}_{self.semester} - {self.get_exam_type_display()}"

class ExamResult(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, verbose_name="Sınav")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name="Öğrenci")
    total_score = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Toplam Puan")
    question_scores = models.JSONField(verbose_name="Soru Bazlı Puanlar")
    is_passed = models.BooleanField(default=False, verbose_name="Geçti mi?")
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        # Negatif toplam puan kontrolü
        if self.total_score < 0:
            raise ValidationError("Toplam puan negatif olamaz.")
        # Soru puanlarının liste olup olmadığını kontrol et
        if not isinstance(self.question_scores, list):
            raise ValidationError("Soru puanları bir liste olmalıdır.")
        # Soru puanlarının sayısal değerlerden oluşup oluşmadığını kontrol et
        if not all(isinstance(score, (int, float)) for score in self.question_scores):
            raise ValidationError("Her bir soru puanı sayısal bir değer olmalıdır.")
        # Toplam puan ve soru puanlarının toplamının eşleşmesi
        if sum(self.question_scores) != float(self.total_score):
            raise ValidationError("Toplam puan ile soru puanlarının toplamı uyuşmuyor.")

    def __str__(self):
        return f"{self.student} - {self.exam} - {self.total_score}"

    class Meta:
        unique_together = ('exam', 'student')
        indexes = [
            models.Index(fields=['exam', 'student']),
        ]

    class Meta:
        verbose_name = "Sınav Sonucu"
        verbose_name_plural = "Sınav Sonuçları"
        unique_together = ['exam', 'student']  # Bir öğrencinin aynı sınavda birden fazla sonucu olamaz

    def __str__(self):
        return f"{self.exam} - {self.student}"