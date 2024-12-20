from django.urls import path
from . import views

urlpatterns = [
    # Ana sayfa ve kullanıcı yönetimi
    path('', views.home, name='home'),
    path('kullanici-secimi/', views.user_select, name='user_select'),
    path('giris/<str:username>/', views.login, name='login'),
    path('ilk-parola/<str:username>/', views.first_password, name='first_password'),
    path('parola-sifirla/<str:username>/', views.password_reset, name='password_reset'),
    path('cikis/', views.logout, name='logout'),

    # Sınav yönetimi
    path('sinav-yukle/', views.exam_upload, name='exam_upload'),
    path('sinav-listesi/', views.exam_list, name='exam_list'),
    path('sinav-analiz/<int:exam_id>/', views.exam_analysis, name='exam_analysis'),
    path('sinav-sil/<int:exam_id>/', views.exam_delete, name='exam_delete'),

    # Öğrenci yönetimi
    path('ogrenci-listesi/', views.student_list, name='student_list'),
    path('ogrenci-analiz/<str:student_number>/', views.student_analysis, name='student_analysis'),
    path('ogrenci-analiz/<str:student_number>/sinav-kagidi-yukle/', views.upload_exam_paper, name='upload_exam_paper'),
    path('ogrenci-analiz/<str:student_number>/sinav-kagidi-goruntule/', views.view_exam_paper, name='view_exam_paper'),
    path('ogrenci-analiz/<str:student_number>/sinav-kagidi-indir/', views.download_exam_paper,
         name='download_exam_paper'),
    # urls.py'a eklenecek
    path('manuel-sinav-girisi/', views.manual_exam_result, name='manual_exam_result'),

    # Kazanım yönetimi
    path('kazanimlar/', views.outcomes_view, name='outcomes'),
    path('kazanim-ekle/<int:exam_id>/', views.add_outcome, name='add_outcome'),
    path('kazanim-goster/<int:exam_id>/', views.show_outcomes, name='show_outcomes'),
    # urls.py
    path('kazanim-sil/<int:exam_id>/', views.delete_outcomes, name='delete_outcomes'),

    # Raporlama ve grafikler
    path('raporlar/', views.reports, name='reports'),
    path('grafikler/', views.graphs, name='graphs'),

    # API endpoints
    path('api/graph-data/', views.get_graph_data, name='graph_data'),
    path('api/graph-metadata/', views.get_graph_metadata, name='graph_metadata'),
]
