from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Lecturer, Course, Student, Exam, ExamResult, CourseOutcome, ExamQuestionOutcome, UserLog

# Mevcut User modelini admin panelinden kaldır
admin.site.unregister(User)


class LecturerInline(admin.StackedInline):
    model = Lecturer
    can_delete = False
    verbose_name_plural = 'Öğretim Üyesi Bilgileri'


class CustomUserAdmin(UserAdmin):
    inlines = (LecturerInline,)
    list_display = ('username', 'get_full_name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('username', 'lecturer__full_name')
    ordering = ('username',)

    def get_full_name(self, obj):
        return obj.lecturer.full_name if hasattr(obj, 'lecturer') else ''

    get_full_name.short_description = 'Ad Soyad'


@admin.register(Lecturer)
class LecturerAdmin(admin.ModelAdmin):
    list_display = ('username', 'full_name', 'is_password_created', 'created_at')
    list_filter = ('is_password_created',)
    search_fields = ('username', 'full_name')
    readonly_fields = ('is_password_created',)

    def get_readonly_fields(self, request, obj=None):
        # Eğer yeni bir öğretim üyesi oluşturuluyorsa, user alanını düzenlenebilir yap
        if obj is None:
            return self.readonly_fields
        # Mevcut bir öğretim üyesi düzenleniyorsa, user alanını readonly yap
        return self.readonly_fields + ('user',)


# Diğer model kayıtları aynı kalacak
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'lecturer')
    list_filter = ('lecturer',)
    search_fields = ('code', 'name')


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_number', 'full_name', 'created_at')
    search_fields = ('student_number', 'full_name')


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('course', 'semester', 'exam_type', 'exam_date', 'question_count')
    list_filter = ('exam_type', 'semester')
    search_fields = ('course__code', 'course__name')


@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    list_display = ('exam', 'student', 'total_score')
    list_filter = ('exam__exam_type', 'exam__course')
    search_fields = ('student__student_number', 'student__full_name')


@admin.register(CourseOutcome)
class CourseOutcomeAdmin(admin.ModelAdmin):
    list_display = ('course', 'description', 'created_at')
    list_filter = ('course',)
    search_fields = ('course__code', 'description')


@admin.register(ExamQuestionOutcome)
class ExamQuestionOutcomeAdmin(admin.ModelAdmin):
    list_display = ('exam', 'question_number', 'outcome', 'contribution_percentage')
    list_filter = ('exam', 'outcome')
    search_fields = ('exam__course__code', 'outcome__description')


# User modelini özelleştirilmiş admin ile kaydet
admin.site.register(User, CustomUserAdmin)


@admin.register(UserLog)
class UserLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'ip_address', 'created_at')
    list_filter = ('action', 'user', 'created_at')
    search_fields = ('user__full_name', 'details', 'ip_address')
    readonly_fields = ('user', 'action', 'details', 'ip_address', 'created_at')
    ordering = ('-created_at',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
