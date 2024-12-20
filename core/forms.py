from django import forms
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator
from django.utils import timezone
from .models import Course, Exam, Lecturer
from django import forms
from .models import CourseOutcome
import os
from .models import ExamPaper
from django.contrib.auth.forms import SetPasswordForm
from django.core.exceptions import ValidationError
from .models import Student, ExamResult


class ExamUploadForm(forms.Form):
    """Sınav yükleme formu"""
    EXAM_TYPES = [
        ('VIZE', 'Vize'),
        ('FINAL', 'Final'),
        ('BUTUNLEME', 'Bütünleme'),
        ('MAZERET', 'Mazeret'),
    ]

    SEMESTER_CHOICES = [
        ('GUZ', 'Güz'),
        ('BAHAR', 'Bahar'),
    ]

    # Temel form alanları
    upload_type = forms.ChoiceField(
        choices=[('new', 'Yeni Sınav'), ('existing', 'Mevcut Sınav')],
        widget=forms.RadioSelect,
        label='Yükleme Türü',
        error_messages={
            'required': 'Lütfen yükleme türünü seçin.',
        }
    )

    existing_exam_id = forms.IntegerField(
        required=False,
        widget=forms.Select,
        label='Mevcut Sınav'
    )

    course = forms.ModelChoiceField(
        queryset=Course.objects.all(),
        empty_label="Ders seçiniz",
        required=True,
        label='Ders',
        error_messages={
            'required': 'Lütfen bir ders seçin.',
            'invalid_choice': 'Lütfen geçerli bir ders seçin.',
        }
    )

    semester = forms.ChoiceField(
        choices=SEMESTER_CHOICES,
        required=True,
        widget=forms.RadioSelect,
        label='Dönem',
        error_messages={
            'required': 'Lütfen dönemi seçin.',
            'invalid_choice': 'Lütfen geçerli bir dönem seçin.',
        }
    )

    exam_type = forms.ChoiceField(
        choices=EXAM_TYPES,
        required=True,
        widget=forms.RadioSelect,
        label='Sınav Türü',
        error_messages={
            'required': 'Lütfen sınav türünü seçin.',
            'invalid_choice': 'Lütfen geçerli bir sınav türü seçin.',
        }
    )

    exam_date = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Sınav Tarihi',
        error_messages={
            'required': 'Lütfen sınav tarihini seçin.',
            'invalid': 'Lütfen geçerli bir tarih seçin.',
        }
    )

    exam_files = forms.FileField(
        required=True,
        label='Sınav Dosyaları',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])],
        error_messages={
            'required': 'Lütfen sınav dosyalarını yükleyin.',
            'invalid_extension': 'Yalnızca PDF, JPG, JPEG ve PNG dosyaları yükleyebilirsiniz.',
        }
    )

    student_list = forms.FileField(
        required=True,
        validators=[FileExtensionValidator(allowed_extensions=['xls', 'xlsx'])],
        label='Öğrenci Listesi (Excel)',
        error_messages={
            'required': 'Lütfen öğrenci listesi Excel dosyasını yükleyin.',
            'invalid_extension': 'Yalnızca XLS ve XLSX dosyaları yükleyebilirsiniz.',
        }
    )

    def clean_exam_date(self):
        """Sınav tarihi validasyonu"""
        exam_date = self.cleaned_data.get('exam_date')

        if exam_date:
            if exam_date > timezone.now().date():
                raise forms.ValidationError('Sınav tarihi bugünden ileri bir tarih olamaz.')

            # En fazla 1 yıl önceki sınavları kabul et
            one_year_ago = timezone.now().date() - timezone.timedelta(days=365)
            if exam_date < one_year_ago:
                raise forms.ValidationError('En fazla 1 yıl önceki sınavları yükleyebilirsiniz.')

        return exam_date

    def clean(self):
        """Form genel validasyonu"""
        cleaned_data = super().clean()
        upload_type = cleaned_data.get('upload_type')
        existing_exam_id = cleaned_data.get('existing_exam_id')
        course = cleaned_data.get('course')
        semester = cleaned_data.get('semester')
        exam_type = cleaned_data.get('exam_type')

        if upload_type == 'existing':
            if not existing_exam_id:
                raise forms.ValidationError('Mevcut sınav seçeneği için bir sınav seçmelisiniz.')
        else:
            # Yeni sınav için aynı dersin aynı dönemde aynı tür sınavı var mı kontrol et
            if course and semester and exam_type:
                if Exam.objects.filter(
                        course=course,
                        semester=semester,
                        exam_type=exam_type
                ).exists():
                    raise forms.ValidationError(
                        'Bu ders için seçilen dönemde bu tür sınav zaten mevcut.'
                    )

        return cleaned_data


class OutcomeAddForm(forms.Form):
    question_number = forms.ChoiceField(
        label="Soru Numarası",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    outcome = forms.ModelChoiceField(
        queryset=CourseOutcome.objects.none(),
        label="Ders Kazanımı",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    contribution_percentage = forms.IntegerField(
        label="Katkı Yüzdesi",
        min_value=1,
        max_value=100,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    def __init__(self, exam, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['question_number'].choices = [
            (i, f"Soru {i}") for i in range(1, exam.question_count + 1)
        ]
        self.fields['outcome'].queryset = CourseOutcome.objects.filter(
            course=exam.course
        )


class ExamPaperUploadForm(forms.ModelForm):
    class Meta:
        model = ExamPaper
        fields = ['file']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['file'].widget.attrs.update({
            'class': 'form-control',
            'accept': 'application/pdf'
        })

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Dosya boyutu kontrolü (örneğin 5MB)
            if file.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Dosya boyutu 5MB\'dan büyük olamaz.')

            # Dosya uzantısı kontrolü
            ext = os.path.splitext(file.name)[1]
            if ext.lower() != '.pdf':
                raise forms.ValidationError('Sadece PDF dosyaları yüklenebilir.')

        return file


class LoginForm(forms.Form):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Parolanızı girin'
        }),
        label='Parola'
    )

    def __init__(self, *args, **kwargs):
        self.lecturer = kwargs.pop('lecturer', None)
        super().__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if self.lecturer and not self.lecturer.user.check_password(password):
            raise ValidationError('Parola yanlış!')
        return password

    def get_user(self):
        return self.lecturer.get_user_auth() if self.lecturer else None


class FirstPasswordForm(forms.Form):
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Yeni parolanızı girin'
        }),
        label='Yeni Parola'
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Yeni parolanızı tekrar girin'
        }),
        label='Yeni Parola (Tekrar)'
    )

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 and password2:
            if password1 != password2:
                raise ValidationError('Parolalar eşleşmiyor!')
            if len(password1) < 8:
                raise ValidationError('Parola en az 8 karakter olmalıdır!')
        return cleaned_data


class CustomSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Yeni parolanızı girin'
        })
        self.fields['new_password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Yeni parolanızı tekrar girin'
        })


class ManualExamResultForm(forms.Form):
    student_number = forms.CharField(
        label='Öğrenci Numarası',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Örn: 21253501'
        }),
        max_length=20
    )

    def __init__(self, exam=None, request=None, *args, **kwargs):
        self.request = request
        self.exam = exam
        super().__init__(*args, **kwargs)

        if exam:
            # Her soru için puan alanı oluştur
            for i, max_score in enumerate(exam.question_scores, 1):
                field_name = f'question_{i}'
                self.fields[field_name] = forms.DecimalField(
                    label=f'Soru {i}',
                    max_digits=5,
                    decimal_places=2,
                    min_value=0,
                    max_value=max_score,
                    widget=forms.NumberInput(attrs={
                        'class': 'form-control question-score text-center',
                        'data_max': str(max_score),
                        'step': '0.5',
                        'placeholder': '0.00'
                    })
                )

    def clean(self):
        cleaned_data = super().clean()
        student_number = cleaned_data.get('student_number')

        if student_number:
            # Öğrenci numarasının formatını kontrol et
            if not student_number.isdigit():
                raise ValidationError('Öğrenci numarası sadece rakamlardan oluşmalıdır.')

            try:
                student = Student.objects.get(student_number=student_number)
                # Session'daki başarısız öğrenci listesinde bu numara var mı kontrol et
                if self.request:  # request varsa kontrol et
                    failed_students = self.request.session.get('failed_ocr_students', [])
                    if student_number not in failed_students:
                        raise ValidationError(
                            'Bu öğrenci numarası, OCR ile okunamayan öğrenciler listesinde bulunmuyor.')
            except Student.DoesNotExist:
                raise ValidationError('Bu öğrenci numarası sistemde kayıtlı değil.')

            # Bu öğrencinin bu sınav için zaten kaydı var mı kontrol et
            if ExamResult.objects.filter(student=student, exam=self.exam).exists():
                raise ValidationError('Bu öğrencinin bu sınav için zaten bir kaydı var.')

        # Soru puanlarını kontrol et
        question_scores = []
        total_score = 0

        if self.exam and self.exam.question_scores:
            for i in range(1, len(self.exam.question_scores) + 1):
                field_name = f'question_{i}'
                score = cleaned_data.get(field_name)

                if score is not None:
                    max_score = self.exam.question_scores[i - 1]
                    if score > max_score:
                        self.add_error(field_name, f'Puan, maksimum değer olan {max_score}\'dan büyük olamaz.')
                    question_scores.append(float(score))
                    total_score += float(score)

            if total_score > 100:
                raise ValidationError('Toplam puan 100\'den büyük olamaz.')

        cleaned_data['question_scores'] = question_scores
        cleaned_data['total_score'] = total_score
        cleaned_data['student'] = student if student_number else None

        return cleaned_data
