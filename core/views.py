# Django imports
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
from datetime import timedelta
from django.core.exceptions import ValidationError
from utils import process_exam_file
from .forms import OutcomeAddForm, ManualExamResultForm
from .models import Lecturer, Course, ExamQuestionOutcome
import os
from datetime import datetime
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import HttpResponse
import xlwt
from openpyxl import Workbook
from django.http import JsonResponse
from django.db.models import Count, Avg, Max, Min
from django.views.decorators.http import require_http_methods
from django.db.models.functions import ExtractYear, ExtractMonth
import json
from django.http import FileResponse, Http404
from .forms import ExamPaperUploadForm
from .models import ExamPaper
from django.core.files.storage import default_storage
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .forms import LoginForm, FirstPasswordForm, CustomSetPasswordForm
import logging
from .models import UserLog
from django.utils import timezone
import pandas as pd
from core.models import Student, Exam, ExamResult
from django.db import transaction

logger = logging.getLogger('user_actions')


@login_required
def home(request):
    lecturer_username = request.session.get('lecturer_username')
    if not lecturer_username:
        # Oturum yoksa user_select sayfasına yönlendir
        return redirect('user_select')

    try:
        lecturer = Lecturer.objects.get(username=lecturer_username)
        if not lecturer.user or not lecturer.is_password_created:
            # Parola oluşturulmamışsa ilk parola sayfasına yönlendir
            return redirect('first_password', username=lecturer_username)

        # Tüm kontroller başarılıysa ana sayfayı göster
        exam_count = Exam.objects.count()
        student_count = Student.objects.count()
        lecturer_count = Lecturer.objects.count()

        context = {
            'exam_count': exam_count,
            'student_count': student_count,
            'lecturer_count': lecturer_count,
        }
        return render(request, 'core/home.html', context)
    except Lecturer.DoesNotExist:
        # Hata durumunda oturumu temizle ve user_select sayfasına yönlendir
        request.session.flush()
        return redirect('user_select')


def user_select(request):
    # Eğer oturum zaten başlatılmışsa ana sayfaya yönlendir
    if request.session.get('lecturer_username'):
        return redirect('home')

    lecturers = Lecturer.objects.all().order_by('full_name')
    return render(request, 'core/user_select.html', {'lecturers': lecturers})


logger = logging.getLogger('user_actions')


def log_user_action(request, user, action, details=None):
    """Kullanıcı eylemlerini loglamak için yardımcı fonksiyon"""
    try:
        # Doğrudan veritabanına kaydet
        UserLog.objects.create(
            user=user,
            action=action,
            details=details,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        # Ayrıca log dosyasına da yaz
        logger.info(f"User: {user.username}, Action: {action}, Details: {details}")
    except Exception as e:
        logger.error(f"Log kaydı oluşturulurken hata: {str(e)}")


def login(request, username):
    lecturer = get_object_or_404(Lecturer, username=username)

    # Eğer kullanıcının henüz bir User nesnesi yoksa veya parola oluşturulmamışsa
    if not lecturer.user or not lecturer.is_password_created:
        return redirect('first_password', username=username)

    # Eğer zaten giriş yapılmışsa ana sayfaya yönlendir
    if request.session.get('lecturer_username') == username:
        return redirect('home')

    if request.method == 'POST':
        form = LoginForm(request.POST, lecturer=lecturer)
        if form.is_valid():
            # Django'nun yerleşik login fonksiyonunu kullan
            from django.contrib.auth import login as auth_login
            auth_login(request, lecturer.user)

            # Session'a kullanıcı bilgilerini kaydet
            request.session['lecturer_username'] = lecturer.username
            request.session['lecturer_name'] = lecturer.full_name

            # Giriş logunu kaydet
            log_user_action(
                request,
                lecturer,
                'LOGIN',
                f'{lecturer.full_name} ({lecturer.username}) kullanıcısı sisteme giriş yaptı'
            )

            messages.success(request, f'Hoş geldiniz, {lecturer.full_name}')
            return redirect('home')
    else:
        form = LoginForm()

    return render(request, 'core/login.html', {
        'form': form,
        'lecturer': lecturer
    })


def first_password(request, username):
    lecturer = get_object_or_404(Lecturer, username=username)

    # Eğer kullanıcı zaten parola oluşturmuşsa login sayfasına yönlendir
    if lecturer.is_password_created:
        messages.warning(request, 'Parolanız zaten oluşturulmuş.')
        return redirect('login', username=username)

    if request.method == 'POST':
        form = FirstPasswordForm(request.POST)
        if form.is_valid():
            # Eğer User nesnesi yoksa oluştur
            if not lecturer.user:
                user = User.objects.create_user(
                    username=lecturer.username,
                    password=form.cleaned_data['password1']
                )
                lecturer.user = user
            else:
                lecturer.user.set_password(form.cleaned_data['password1'])
                lecturer.user.save()

            lecturer.is_password_created = True
            lecturer.save()

            messages.success(request, 'Parolanız başarıyla oluşturuldu. Şimdi giriş yapabilirsiniz.')
            return redirect('login', username=username)
    else:
        form = FirstPasswordForm()

    return render(request, 'core/first_password.html', {
        'form': form,
        'lecturer': lecturer
    })


def password_reset(request, username):
    lecturer = get_object_or_404(Lecturer, username=username)

    # Eğer kullanıcının henüz parolası oluşturulmamışsa ilk parola oluşturma sayfasına yönlendir
    if not lecturer.is_password_created:
        return redirect('first_password', username=username)

    if request.method == 'POST':
        form = CustomSetPasswordForm(lecturer.user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Parolanız başarıyla sıfırlandı. Yeni parolanızla giriş yapabilirsiniz.')
            return redirect('login', username=username)
    else:
        form = CustomSetPasswordForm(lecturer.user)

    return render(request, 'core/password_reset.html', {
        'form': form,
        'lecturer': lecturer
    })


@login_required
def home(request):
    if not request.session.get('lecturer_username'):
        return redirect('user_select')

    exam_count = Exam.objects.count()
    student_count = Student.objects.count()
    lecturer_count = Lecturer.objects.count()

    context = {
        'exam_count': exam_count,
        'student_count': student_count,
        'lecturer_count': lecturer_count,
    }
    return render(request, 'core/home.html', context)


def logout(request):
    request.session.flush()
    messages.success(request, 'Başarıyla çıkış yaptınız.')
    return redirect('user_select')


def exam_upload(request):
    if not request.session.get('lecturer_username'):
        return redirect('user_select')

    lecturer = Lecturer.objects.get(username=request.session.get('lecturer_username'))

    if request.method == 'POST':
        try:
            upload_type = request.POST.get('upload_type')
            upload_path = None
            semester = None
            exam = None
            excel_students = set()  # Excel'deki tüm öğrenciler
            processed_students = set()  # OCR ile başarıyla işlenen öğrenciler

            if upload_type == 'existing':
                exam_id = request.POST.get('existing_exam_id')
                try:
                    exam = Exam.objects.get(id=exam_id)
                    upload_path = os.path.join(
                        settings.MEDIA_ROOT,
                        'exam_files',
                        f"{exam.course.code}_{exam.semester}_{exam.exam_type}_{exam.created_at.strftime('%Y%m%d_%H%M%S')}"
                    )
                    log_user_action(
                        request,
                        lecturer,
                        'EXAM_UPDATE',
                        f'{lecturer.full_name} tarafından {exam.course.code} dersinin mevcut sınavına veri eklendi'
                    )
                except Exam.DoesNotExist:
                    messages.error(request, 'Seçilen sınav bulunamadı.')
                    return redirect('exam_upload')

            elif upload_type == 'new':
                course_code = request.POST.get('course')
                semester = request.POST.get('semester')
                exam_type = request.POST.get('exam_type')
                exam_date = request.POST.get('exam_date')

                if not course_code:
                    messages.error(request, 'Yeni bir sınav oluşturmak için ders seçmelisiniz.')
                    return redirect('exam_upload')

                if not semester:
                    messages.error(request, 'Yeni bir sınav oluşturmak için dönem seçmelisiniz.')
                    return redirect('exam_upload')

                try:
                    course = Course.objects.get(code=course_code)
                except Course.DoesNotExist:
                    messages.error(request, 'Seçilen ders bulunamadı.')
                    return redirect('exam_upload')

                folder_name = f"{course_code}_{semester}_{exam_type}_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
                upload_path = os.path.join(settings.MEDIA_ROOT, 'exam_files', folder_name)
                exam = Exam.objects.create(
                    course=course,
                    semester=semester,
                    exam_type=exam_type,
                    exam_date=exam_date,
                    question_count=0,
                    created_at=timezone.now()
                )
                log_user_action(
                    request,
                    lecturer,
                    'EXAM_CREATE',
                    f'{lecturer.full_name} tarafından {course.code} dersi için yeni {exam.get_exam_type_display()} sınavı oluşturuldu'
                )

            # Excel dosyasından öğrenci bilgilerini kaydet
            student_list = request.FILES.get('student_list')
            if student_list:
                try:
                    df = pd.read_excel(student_list)
                    required_columns = ['Öğrenci No', 'Ad Soyad']
                    if not all(col in df.columns for col in required_columns):
                        messages.error(request, 'Excel dosyası gerekli sütunları içermiyor.')
                        return redirect('exam_upload')

                    student_count = 0
                    # Excel'deki tüm öğrenci numaralarını kaydet
                    excel_students = set(str(num).strip() for num in df['Öğrenci No'])

                    for _, row in df.iterrows():
                        student_number = str(row['Öğrenci No']).strip()
                        full_name = row['Ad Soyad'].strip()
                        student, created = Student.objects.get_or_create(
                            student_number=student_number,
                            defaults={'full_name': full_name}
                        )
                        if created:
                            student_count += 1

                    if student_count > 0:
                        log_user_action(
                            request,
                            lecturer,
                            'STUDENT_ADD',
                            f'{lecturer.full_name} tarafından {student_count} yeni öğrenci eklendi'
                        )

                except Exception as e:
                    messages.error(request, f'Excel dosyası okunurken hata oluştu: {str(e)}')
                    return redirect('exam_upload')

            # Sınav dosyalarını kaydet ve işle
            if upload_path:
                os.makedirs(upload_path, exist_ok=True)

                exam_files = request.FILES.getlist('exam_files')
                if not exam_files:
                    messages.error(request, 'Lütfen sınav dosyalarını yükleyin.')
                    return redirect('exam_upload')

                success_count = 0
                failure_count = 0
                first_file = True

                for file in exam_files:
                    file_path = os.path.join(upload_path, file.name)
                    with open(file_path, 'wb+') as destination:
                        for chunk in file.chunks():
                            destination.write(chunk)

                    result = process_exam_file(file_path, exam.course.code, semester)

                    if first_file and result['question_scores']:
                        exam.question_count = len(result['question_scores'])
                        exam.question_scores = result['question_scores']
                        try:
                            exam.full_clean()
                            exam.save()
                        except ValidationError as e:
                            messages.error(request, f"Sınav puanları geçersiz: {str(e)}")
                            return redirect('exam_upload')
                        first_file = False

                    if not result['student_number']:
                        failure_count += 1
                        continue
                    else:
                        processed_students.add(result['student_number'])

                    try:
                        student = Student.objects.get(student_number=result['student_number'])
                        exam_result = ExamResult(
                            exam=exam,
                            student=student,
                            total_score=sum(result['student_scores']),
                            question_scores=result['student_scores']
                        )
                        exam_result.full_clean()
                        exam_result.save()
                        success_count += 1
                    except (Student.DoesNotExist, ValidationError) as e:
                        failure_count += 1
                        continue

                # OCR ile okunamayan öğrencileri tespit et
                failed_ocr_students = list(excel_students - processed_students)

                if failed_ocr_students:
                    # Session'a başarısız öğrenci listesini ve sınav ID'sini kaydet
                    request.session['failed_ocr_students'] = failed_ocr_students
                    request.session['current_exam_id'] = exam.id
                    failed_msg = "Aşağıdaki öğrenci numaralarına ait sınav kağıtları okunamadı:\n"
                    failed_msg += ", ".join(failed_ocr_students)
                    messages.warning(request, failed_msg)

                log_details = f'{lecturer.full_name} tarafından {exam.course.code} dersi için '
                log_details += f'{success_count} sınav kağıdı başarıyla işlendi'
                if failure_count > 0:
                    log_details += f', {failure_count} sınav kağıdı işlenemedi'
                log_user_action(request, lecturer, 'EXAM_PROCESS', log_details)

                if success_count > 0:
                    messages.success(request, f"{success_count} dosya başarıyla işlendi.")
                if failure_count > 0:
                    messages.error(request, f"{failure_count} dosya işlenemedi.")

            if upload_type == 'existing':
                messages.success(request, 'Yeni veriler mevcut sınava başarıyla eklendi.')
            else:
                messages.success(request, 'Yeni sınav başarıyla oluşturuldu.')

            return redirect('exam_list')

        except Exception as e:
            log_user_action(
                request,
                lecturer,
                'ERROR',
                f'{lecturer.full_name} kullanıcısının sınav yükleme işleminde hata: {str(e)}'
            )
            messages.error(request, f'Bir hata oluştu: {str(e)}')
            return redirect('exam_upload')

    recent_exams = Exam.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=365)
    ).order_by('-created_at')
    courses = Course.objects.all().order_by('code')
    return render(request, 'core/exam_upload.html', {
        'courses': courses,
        'recent_exams': recent_exams
    })


def exam_list(request):
    if not request.session.get('lecturer_username'):
        return redirect('user_select')

    exams = Exam.objects.all().order_by('-created_at')
    return render(request, 'core/exam_list.html', {'exams': exams})


def student_list(request):
    if not request.session.get('lecturer_username'):
        return redirect('user_select')

    # Arama parametresini al
    search_query = request.GET.get('search', '')

    # Sıralama parametresini al
    sort_by = request.GET.get('sort', 'student_number')  # Varsayılan sıralama
    if sort_by.startswith('-'):
        sort_field = sort_by[1:]
        sort_direction = 'desc'
    else:
        sort_field = sort_by
        sort_direction = 'asc'

    # Öğrencileri filtrele ve sırala
    students = Student.objects.all()
    if search_query:
        students = students.filter(
            Q(student_number__icontains=search_query) |
            Q(full_name__icontains=search_query)
        )

    students = students.order_by(sort_by)

    # Sayfalama
    page_number = request.GET.get('page', 1)
    paginator = Paginator(students, 10)  # Her sayfada 10 öğrenci
    page_obj = paginator.get_page(page_number)

    # Excel export
    if request.GET.get('export') == 'excel':
        response = HttpResponse(content_type='application/ms-excel')
        response[
            'Content-Disposition'] = f'attachment; filename="ogrenci_listesi_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xls"'

        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet('Öğrenciler')

        # Başlıklar
        row_num = 0
        columns = ['Öğrenci No', 'Ad Soyad']
        for col_num, column_title in enumerate(columns):
            ws.write(row_num, col_num, column_title)

        # Veriler
        for student in students:
            row_num += 1
            row = [
                student.student_number,
                student.full_name,
            ]
            for col_num, cell_value in enumerate(row):
                ws.write(row_num, col_num, cell_value)

        wb.save(response)
        return response

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'sort_field': sort_field,
        'sort_direction': sort_direction,
        'total_count': students.count(),
    }
    return render(request, 'core/student_list.html', context)


def reports(request):
    if not request.session.get('lecturer_username'):
        return redirect('user_select')

    exams = Exam.objects.all()  # Tüm sınavları al
    report_data = []  # Her sınav için analiz verisi

    for exam in exams:
        exam_results = ExamResult.objects.filter(exam=exam)

        if not exam_results.exists():
            continue  # Eğer sonuç yoksa bu sınavı atla

        question_scores_list = [result.question_scores for result in exam_results]
        question_stats = []

        # Her soru için analiz yap
        for i, max_score in enumerate(exam.question_scores):
            scores = [qs[i] for qs in question_scores_list if i < len(qs)]  # Soru puanları
            avg_score = sum(scores) / len(scores) if scores else 0
            success_rate = (avg_score / max_score) * 100 if max_score > 0 else 0
            question_stats.append({
                'question_number': f"Soru {i + 1}",
                'avg_score': round(avg_score, 2),
                'success_rate': round(success_rate, 2)
            })

        report_data.append({
            'exam_id': exam.id,
            'course': exam.course.code,
            'semester': exam.get_semester_display(),
            'exam_type': exam.get_exam_type_display(),
            'exam_date': exam.exam_date.strftime('%d.%m.%Y'),
            'question_numbers': [stat['question_number'] for stat in question_stats],
            'success_rates': [stat['success_rate'] for stat in question_stats],
        })

    context = {
        'report_data': report_data,
    }
    return render(request, 'core/reports.html', context)


def exam_analysis(request, exam_id):
    if not request.session.get('lecturer_username'):
        return redirect('user_select')

    try:
        exam = Exam.objects.get(id=exam_id)
        exam_results = ExamResult.objects.filter(exam=exam)

        # Soru bazlı analiz
        if exam.question_scores:
            question_stats = []
            for i, score in enumerate(exam.question_scores):
                max_score = score
                min_score = min(result.question_scores[i] for result in exam_results)
                min_non_zero_score = min(
                    score for score in (result.question_scores[i] for result in exam_results) if score > 0)
                num_students = len(exam_results)
                if num_students > 0:
                    avg_score = sum(result.question_scores[i] for result in exam_results) / num_students
                    success_rate = (avg_score / max_score) * 100
                else:
                    avg_score = 0
                    success_rate = 0
                max_received = max(result.question_scores[i] for result in exam_results)
                question_stats.append({
                    'question_number': i + 1,
                    'question_score': max_score,  # Sorunun tam puanı
                    'max_received_score': max_received,  # Alınan en yüksek puan
                    'min_score': min_score,
                    'min_non_zero_score': min_non_zero_score,
                    'avg_score': avg_score,
                    'success_rate': success_rate
                })
        else:
            question_stats = []

        # Excel export için
        # Excel export için
        if request.GET.get('export') == 'excel':
            response = HttpResponse(content_type='application/ms-excel')
            response[
                'Content-Disposition'] = f'attachment; filename="{exam.course.code}_{exam.get_semester_display}_{exam.get_exam_type_display}_soru_analizi_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xls"'

            wb = xlwt.Workbook(encoding='utf-8')
            ws = wb.add_sheet('Soru Analizi')

            # Başlıklar
            row_num = 0
            columns = ['Soru No', 'Soru Puanı', 'Maks Puan', 'Min Puan', 'Min Sıfırdan Farklı Puan', 'Ort Puan',
                       'Başarı Oranı']
            for col_num, column_title in enumerate(columns):
                ws.write(row_num, col_num, column_title)

            # Veriler
            for stat in question_stats:
                row_num += 1
                row = [
                    f"Soru {stat['question_number']}",
                    stat['question_score'],
                    stat['max_received_score'],
                    stat['min_score'],
                    stat['min_non_zero_score'],
                    round(stat['avg_score'], 2),
                    f"{round(stat['success_rate'], 2)}%"
                ]
                for col_num, cell_value in enumerate(row):
                    ws.write(row_num, col_num, cell_value)

            wb.save(response)
            return response

        # Bölümlere göre ortalama hesaplama
        ceng_results = exam_results.filter(student__department='CENG')
        other_results = exam_results.filter(student__department='OTHER')

        # Sınav geneli analiz
        total_scores = [float(result.total_score) for result in exam_results]  # Decimal'i float'a çevir
        num_students = len(total_scores)
        if num_students > 0:
            avg_score = sum(total_scores) / num_students
            # Standart sapma hesaplaması
            variance = sum((float(x - avg_score) ** 2) for x in total_scores) / num_students
            std_dev = variance ** 0.5
            median_score = sorted(total_scores)[num_students // 2]

            highest_result = exam_results.order_by('-total_score').first()
            lowest_result = exam_results.order_by('total_score').first()

            # Bölümlere göre ortalamalar
            ceng_scores = [float(result.total_score) for result in ceng_results]
            ceng_avg = sum(ceng_scores) / len(ceng_scores) if ceng_scores else 0

            other_scores = [float(result.total_score) for result in other_results]
            other_avg = sum(other_scores) / len(other_scores) if other_scores else 0
        else:
            avg_score = 0
            std_dev = 0
            median_score = 0
            highest_result = None
            lowest_result = None
            ceng_avg = 0
            other_avg = 0

        context = {
            'exam': exam,
            'question_stats': question_stats,
            'avg_score': round(avg_score, 2),
            'std_dev': round(std_dev, 2),
            'median_score': round(median_score, 2),
            'num_students': num_students,
            'highest_result': highest_result,
            'lowest_result': lowest_result,
            'ceng_avg': round(ceng_avg, 2),
            'other_avg': round(other_avg, 2),
            'ceng_count': len(ceng_results),
            'other_count': len(other_results)
        }
        return render(request, 'core/exam_analysis.html', context)

    except Exception as e:
        messages.error(request, f'Analiz yapılırken bir hata oluştu: {str(e)}')
        return redirect('exam_list')


def student_analysis(request, student_number):
    if not request.session.get('lecturer_username'):
        return redirect('user_select')

    try:
        # Öğrenciyi bul
        student = get_object_or_404(Student, student_number=student_number)

        # Öğrencinin tüm sınav sonuçları
        exam_results = ExamResult.objects.filter(student=student).order_by('-exam__exam_date')

        # Her sınav için detaylı bilgi
        exam_details = []
        for result in exam_results:
            exam = result.exam
            success_rates = []

            # Her soru için başarı oranı hesapla
            for student_score, max_score in zip(result.question_scores, exam.question_scores):
                rate = (student_score / max_score * 100) if max_score > 0 else 0
                success_rates.append(round(rate, 2))

            exam_details.append({
                'course_code_semester': f"{exam.course.code}_{exam.get_semester_display()}",
                'course_name': exam.course.name,
                'exam_type': exam.get_exam_type_display(),
                'exam_date': exam.exam_date,
                'total_score': result.total_score,
                'success_rates': success_rates,
                'question_scores': result.question_scores,
                'max_scores': exam.question_scores
            })

        context = {
            'student': student,
            'exam_details': exam_details
        }

        return render(request, 'core/student_analysis.html', context)

    except Student.DoesNotExist:
        messages.error(request, 'Öğrenci bulunamadı.')
        return redirect('student_list')


def outcomes_view(request):
    if not request.session.get('lecturer_username'):
        return redirect('user_select')

    courses = Course.objects.all().order_by('code')
    selected_course = request.GET.get('course')
    exams = None

    if selected_course:
        exams = Exam.objects.filter(course__code=selected_course)

    context = {
        'courses': courses,
        'selected_course': selected_course,
        'exams': exams,
    }
    return render(request, 'core/outcomes.html', context)


def add_outcome(request, exam_id):
    if not request.session.get('lecturer_username'):
        return redirect('user_select')

    exam = get_object_or_404(Exam, id=exam_id)

    if request.method == 'POST':
        form = OutcomeAddForm(exam, request.POST)
        if form.is_valid():
            try:
                outcome = ExamQuestionOutcome(
                    exam=exam,
                    question_number=form.cleaned_data['question_number'],
                    outcome=form.cleaned_data['outcome'],
                    contribution_percentage=form.cleaned_data['contribution_percentage']
                )
                outcome.full_clean()
                outcome.save()
                messages.success(request, 'Kazanım başarıyla eklendi.')
                return redirect('add_outcome', exam_id=exam_id)
            except ValidationError as e:
                messages.error(request, str(e))
    else:
        form = OutcomeAddForm(exam)

    existing_outcomes = ExamQuestionOutcome.objects.filter(
        exam=exam
    ).order_by('question_number')

    context = {
        'exam': exam,
        'form': form,
        'existing_outcomes': existing_outcomes
    }
    return render(request, 'core/add_outcome.html', context)


def show_outcomes(request, exam_id):
    if not request.session.get('lecturer_username'):
        return redirect('user_select')

    exam = get_object_or_404(Exam, id=exam_id)
    outcomes = ExamQuestionOutcome.objects.filter(exam=exam).order_by('outcome__description')

    # Eğer kazanım yoksa direkt template'e yönlendir
    if not outcomes.exists():
        context = {
            'exam': exam,
            'grouped_outcomes': {},
            'max_question': 0
        }
        return render(request, 'core/show_outcomes.html', context)

    # Diğer kodlar aynı kalacak...
    grouped_outcomes = {}

    # Soru bazlı başarı oranlarını hesapla
    exam_results = ExamResult.objects.filter(exam=exam)
    question_success_rates = {}

    if exam_results.exists() and exam.question_scores:
        for i in range(len(exam.question_scores)):
            scores = [result.question_scores[i] for result in exam_results]
            max_score = exam.question_scores[i]
            avg_score = sum(scores) / len(scores) if scores else 0
            success_rate = (avg_score / max_score * 100) if max_score > 0 else 0
            question_success_rates[i + 1] = success_rate

    # Kazanımları grupla ve her soru için başarı oranlarını hesapla
    for outcome in outcomes:
        outcome_key = outcome.outcome.description
        if outcome_key not in grouped_outcomes:
            grouped_outcomes[outcome_key] = {
                'questions': {},
                'total_success_rate': 0
            }

        question_rate = question_success_rates.get(outcome.question_number, 0)
        contribution = outcome.contribution_percentage
        question_outcome_rate = (question_rate * contribution) / 100

        grouped_outcomes[outcome_key]['questions'][outcome.question_number] = {
            'success_rate': question_outcome_rate,
            'contribution': contribution
        }

    # Toplam kazanım oranlarını hesapla
    for outcome_key in grouped_outcomes:
        total_rate = sum(q['success_rate'] for q in grouped_outcomes[outcome_key]['questions'].values())
        grouped_outcomes[outcome_key]['total_success_rate'] = total_rate

    # Excel export kodu...

    context = {
        'exam': exam,
        'grouped_outcomes': grouped_outcomes,
        'max_question': max(outcome.question_number for outcome in outcomes) if outcomes else 0
    }
    return render(request, 'core/show_outcomes.html', context)


@transaction.atomic
def delete_outcomes(request, exam_id):
    if not request.session.get('lecturer_username'):
        return redirect('user_select')

    exam = get_object_or_404(Exam, id=exam_id)
    outcomes_count = ExamQuestionOutcome.objects.filter(exam=exam).count()

    try:
        # Tüm kazanımları sil
        ExamQuestionOutcome.objects.filter(exam=exam).delete()

        # Log kaydı oluştur
        lecturer = Lecturer.objects.get(username=request.session.get('lecturer_username'))
        log_user_action(
            request,
            lecturer,
            'OUTCOME_DELETE',
            f'{lecturer.full_name} tarafından {exam.course.code} dersi {exam.get_exam_type_display()} sınavının {outcomes_count} kazanımı silindi'
        )

        messages.success(request,
                         f'{exam.course.code} - {exam.get_exam_type_display()} sınavının kazanımları başarıyla silindi.')
    except Exception as e:
        messages.error(request, f'Kazanımlar silinirken bir hata oluştu: {str(e)}')

    return redirect('outcomes')


def graphs(request):
    if not request.session.get('lecturer_username'):
        return redirect('user_select')

    return render(request, 'core/graphs.html')


@require_http_methods(["GET"])
def get_graph_data(request):
    if not request.session.get('lecturer_username'):
        return JsonResponse({'error': 'Oturum gerekli'}, status=401)

    data_source = request.GET.get('source')
    dimensions = request.GET.getlist('dimensions[]', [])
    metrics = request.GET.getlist('metrics[]', [])

    try:
        if data_source == 'exam_results':
            data = get_exam_results_data(dimensions, metrics)
        elif data_source == 'student_performance':
            data = get_student_performance_data(dimensions, metrics)
        elif data_source == 'question_analysis':
            exam_id = request.GET.get('exam_id')
            data = get_question_analysis_data(dimensions, metrics, exam_id)
        else:
            return JsonResponse({'error': 'Geçersiz veri kaynağı'}, status=400)

        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def get_exam_results_data(dimensions, metrics):
    query = ExamResult.objects.all()

    # Boyut filtrelemeleri
    group_by_fields = []

    # Temel alanları her zaman ekle
    base_fields = []

    if 'course' in dimensions:
        base_fields.extend(['exam__course__code', 'exam__course__name'])
    if 'exam_type' in dimensions:
        base_fields.append('exam__exam_type')
    if 'semester' in dimensions:
        base_fields.append('exam__semester')

    # Grup alanlarını birleştir
    group_by_fields.extend(base_fields)

    # Boş olmayan benzersiz kayıtları al
    query = query.values(*group_by_fields).distinct()

    # Metrik hesaplamaları
    aggregations = {}
    if 'avg_score' in metrics:
        aggregations['avg_score'] = Avg('total_score')
    if 'max_score' in metrics:
        aggregations['max_score'] = Max('total_score')
    if 'min_score' in metrics:
        aggregations['min_score'] = Min('total_score')
    if 'student_count' in metrics:
        aggregations['student_count'] = Count('student')

    result = query.annotate(**aggregations)

    # Debug için
    print("Query result:", list(result))
    return list(result)


def get_student_performance_data(dimensions, metrics):
    query = ExamResult.objects.all()

    # Boyut seçimlerine göre group_by alanlarını ayarla
    group_by_fields = []
    if 'student' in dimensions:
        group_by_fields.extend(['student__student_number', 'student__full_name'])
    if 'course' in dimensions:
        group_by_fields.extend(['exam__course__code', 'exam__course__name'])

        # values() metodunu güncellenmiş alanlarla çağır
    query = query.values(*group_by_fields)

    # Metrikleri hesapla
    aggregations = {}
    if 'avg_score' in metrics:
        aggregations['avg_score'] = Avg('total_score')  # 'average_score' yerine 'avg_score'
    if 'exam_count' in metrics:
        aggregations['exam_count'] = Count('exam')

    result = query.annotate(**aggregations)
    # Debug için
    print("Student performance data:", list(result))
    return list(result)


def get_question_analysis_data(dimensions, metrics, exam_id):
    if not exam_id:
        return []

    try:
        exam = Exam.objects.get(id=exam_id)
    except Exam.DoesNotExist:
        return []

    query = ExamResult.objects.filter(exam=exam)
    results = []

    if not query.exists():
        return []

    for i in range(exam.question_count):
        scores = [result.question_scores[i] for result in query]
        max_possible_score = exam.question_scores[i] if exam.question_scores else 0

        # Ortalama puan hesaplama
        avg_score = sum(scores) / len(scores) if scores else 0

        # Başarı oranı hesaplama
        success_rate = (avg_score / max_possible_score * 100) if max_possible_score > 0 else 0

        result_item = {
            'exam_code': exam.course.code,
            'exam_name': exam.course.name,
            'exam_type': exam.get_exam_type_display(),
            'question_number': i + 1,
            'avg_score': round(avg_score, 2),
            'success_rate': round(success_rate, 2)
        }

        results.append(result_item)

    return results


@require_http_methods(["GET"])
def get_graph_metadata(request):
    if not request.session.get('lecturer_username'):
        return JsonResponse({'error': 'Oturum gerekli'}, status=401)

    # Aktif sınavların listesini al
    exams = Exam.objects.all().order_by('-exam_date')
    exam_list = [{
        'id': exam.id,
        'name': f"{exam.course.code} - {exam.get_exam_type_display()} ({exam.exam_date})"
    } for exam in exams]

    metadata = {
        'data_sources': [
            {
                'id': 'exam_results',
                'name': 'Sınav Sonuçları',
                'dimensions': ['course', 'exam_type', 'semester'],
                'metrics': ['avg_score', 'max_score', 'min_score', 'student_count']
            },
            {
                'id': 'question_analysis',
                'name': 'Soru Analizi',
                'dimensions': ['question_number'],
                'metrics': ['avg_score', 'success_rate']
            }
        ],
        'exams': exam_list
    }

    return JsonResponse(metadata)


def upload_exam_paper(request, student_number):
    if not request.session.get('lecturer_username'):
        return redirect('user_select')

    student = get_object_or_404(Student, student_number=student_number)

    if request.method == 'POST':
        form = ExamPaperUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # Öğrenci klasörünü oluştur
            student_folder = os.path.join('exam_papers', student_number)
            if not os.path.exists(os.path.join(settings.MEDIA_ROOT, student_folder)):
                os.makedirs(os.path.join(settings.MEDIA_ROOT, student_folder))

            # Dosya adını oluştur
            original_filename = request.FILES['file'].name
            base_name = os.path.splitext(original_filename)[0]
            extension = os.path.splitext(original_filename)[1]
            counter = 0
            filename = original_filename

            # Aynı isimli dosya varsa numaralandır
            while default_storage.exists(os.path.join(student_folder, filename)):
                counter += 1
                filename = f"{base_name}-{counter}{extension}"

            # Dosyayı kaydet
            exam_paper = form.save(commit=False)
            exam_paper.student = student
            exam_paper.file.name = os.path.join(student_folder, filename)
            exam_paper.save()

            messages.success(request, 'Sınav kağıdı başarıyla yüklendi.')
            return redirect('student_analysis', student_number=student_number)
        else:
            messages.error(request, 'Dosya yüklenirken bir hata oluştu.')

    return JsonResponse({'error': 'Geçersiz istek'}, status=400)


def view_exam_paper(request, student_number):
    if not request.session.get('lecturer_username'):
        return redirect('user_select')

    student = get_object_or_404(Student, student_number=student_number)
    exam_papers = ExamPaper.objects.filter(student=student).order_by('-upload_date')

    if not exam_papers.exists():
        messages.warning(request, 'Bu öğrenciye ait sınav kağıdı bulunamadı.')
        return redirect('student_analysis', student_number=student_number)

    latest_paper = exam_papers.first()
    try:
        file_path = latest_paper.get_file_path()
        if not os.path.exists(file_path):
            messages.error(request, 'Sınav kağıdı dosyası bulunamadı.')
            return redirect('student_analysis', student_number=student_number)

        # PDF dosyasını binary olarak oku
        with open(file_path, 'rb') as pdf_file:
            # PDF içeriğini base64 formatına çevir
            import base64
            pdf_content = base64.b64encode(pdf_file.read()).decode('utf-8')

        # PDF içeriğini context olarak template'e gönder
        context = {
            'student': student,
            'pdf_content': pdf_content
        }

        return JsonResponse({
            'pdf_content': pdf_content
        })

    except Exception as e:
        messages.error(request, f'Sınav kağıdı görüntülenirken bir hata oluştu: {str(e)}')
        return redirect('student_analysis', student_number=student_number)


def download_exam_paper(request, student_number):
    if not request.session.get('lecturer_username'):
        return redirect('user_select')

    student = get_object_or_404(Student, student_number=student_number)
    exam_papers = ExamPaper.objects.filter(student=student).order_by('-upload_date')

    if not exam_papers.exists():
        messages.warning(request, 'Bu öğrenciye ait sınav kağıdı bulunamadı.')
        return redirect('student_analysis', student_number=student_number)

    latest_paper = exam_papers.first()
    try:
        response = FileResponse(
            open(latest_paper.get_file_path(), 'rb'),
            content_type='application/pdf'
        )
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(latest_paper.file.name)}"'
        return response
    except FileNotFoundError:
        messages.error(request, 'Sınav kağıdı dosyası bulunamadı.')
        return redirect('student_analysis', student_number=student_number)


@login_required
def manual_exam_result(request):
    if not request.session.get('lecturer_username'):
        return redirect('user_select')

    exam_id = request.session.get('current_exam_id')
    if not exam_id:
        messages.error(request, 'Geçerli bir sınav seçilmemiş.')
        return redirect('exam_list')

    try:
        exam = Exam.objects.get(id=exam_id)
    except Exam.DoesNotExist:
        messages.error(request, 'Seçilen sınav bulunamadı.')
        return redirect('exam_list')

    if request.method == 'POST':
        form = ManualExamResultForm(exam=exam, request=request, data=request.POST)
        if form.is_valid():
            try:
                student = form.cleaned_data['student']

                # Sınav sonucunu kaydet
                exam_result = ExamResult.objects.create(
                    exam=exam,
                    student=student,
                    total_score=form.cleaned_data['total_score'],
                    question_scores=form.cleaned_data['question_scores']
                )

                # Başarılı öğrenciyi session'daki listeden kaldır
                failed_students = request.session.get('failed_ocr_students', [])
                if student.student_number in failed_students:
                    failed_students.remove(student.student_number)
                    request.session['failed_ocr_students'] = failed_students

                # Log kaydı oluştur
                log_user_action(
                    request,
                    Lecturer.objects.get(username=request.session.get('lecturer_username')),
                    'EXAM_RESULT_MANUAL',
                    f'Manuel olarak sınav sonucu girildi. Öğrenci: {student.student_number}, Sınav: {exam.course.code}'
                )

                messages.success(request, 'Sınav sonucu başarıyla kaydedildi.')

                # Eğer başka okumayan öğrenci kalmadıysa exam list'e yönlendir
                if not failed_students:
                    messages.success(request, 'Tüm öğrencilerin sınav sonuçları başarıyla kaydedildi.')
                    return redirect('exam_list')

                # Hala okumayan öğrenci varsa formu sıfırla
                return redirect('manual_exam_result')

            except Exception as e:
                messages.error(request, f'Kayıt sırasında bir hata oluştu: {str(e)}')
    else:
        form = ManualExamResultForm(exam=exam, request=request)

    context = {
        'form': form,
        'exam': exam,
        'failed_students': request.session.get('failed_ocr_students', [])
    }
    return render(request, 'core/manual_exam_result.html', context)


@transaction.atomic
def exam_delete(request, exam_id):
    if not request.session.get('lecturer_username'):
        return redirect('user_select')

    exam = get_object_or_404(Exam, id=exam_id)

    try:
        # İlişkili kayıtları silme işlemleri
        ExamQuestionOutcome.objects.filter(exam=exam).delete()
        ExamResult.objects.filter(exam=exam).delete()

        # Sınavı sil
        exam.delete()

        messages.success(request, f'{exam.course.code} - {exam.get_exam_type_display()} sınavı başarıyla silindi.')

        # Log kaydı oluştur
        lecturer = Lecturer.objects.get(username=request.session.get('lecturer_username'))
        log_user_action(
            request,
            lecturer,
            'EXAM_DELETE',
            f'{lecturer.full_name} tarafından {exam.course.code} dersi {exam.get_exam_type_display()} sınavı silindi'
        )

    except Exception as e:
        messages.error(request, f'Sınav silinirken bir hata oluştu: {str(e)}')

    return redirect('exam_list')
