# GradeLens - Sınav Analiz Sistemi
================================

Bu proje, Pamukkale Üniversitesi Bilgisayar Mühendisliği Bölümü öğretim üyelerinin sınav kağıtlarını otomatik olarak değerlendirmesini ve analiz etmesini sağlayan bir web uygulamasıdır. OCR teknolojisi kullanarak sınav kağıtlarından verileri otomatik olarak çıkarır ve kapsamlı analizler sunar.

## Özellikler
---------
- Öğretim üyesi giriş sistemi
- OCR ile sınav kağıtlarından otomatik not okuma
- Sınav sonuçlarının detaylı analizi
- Öğrenci bazlı performans takibi
- Soru bazlı başarı analizi
- Ders kazanımları takibi
- Dark mode desteği
- Responsive tasarım (masaüstü, tablet ve mobil uyumlu)
- Sınav sonuçlarının Excel'e aktarılması
- Detaylı sınav ve öğrenci analiz raporları
- Görsel ve interaktif grafikler ile veri analizi

## OCR İşlemi Hakkında
------------------
Sistem, optik karakter tanıma (OCR) için Google Cloud Vision API kullanmaktadır. OCR işlemi şu bilgileri otomatik olarak algılar:
- Sınav kağıtlarındaki öğrenci numarası
- Sınav tarihi
- Puan tablosu
- Her bir sorudan alınan puanlar
- Toplam puan

## Sistem Gereksinimleri
--------------------
- Python 3.10 veya üzeri
- pip (Python paket yöneticisi)
- Git
- Poppler (PDF işleme için)
- PostgreSQL (opsiyonel, varsayılan olarak SQLite kullanılmaktadır)

## Kurulum Adımları
---------------
1. Poppler Kurulumu:
   Windows için:
   - https://github.com/oschwartz10612/poppler-windows/releases adresinden en son Poppler sürümünü indirin
   - İndirilen dosyayı C:\poppler-xx.xx.x\ dizinine çıkarın
   - Sistem PATH'ine C:\poppler-xx.xx.x\Library\bin dizinini ekleyin

   Linux için:
   ```bash
   sudo apt-get update
   sudo apt-get install poppler-utils
   ```

2. Projeyi İndirme:
   ```bash
   git clone <proje-repo-url>
   cd gradelens
   ```

3. Sanal Ortam Oluşturma ve Aktif Etme:
   Windows için:
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

   Linux/macOS için:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

4. Gerekli Paketlerin Kurulumu:
   ```bash
   pip install -r requirements.txt
   ```

## requirements.txt İçeriği
```
# Web Framework
Django==5.0.1

# Image Processing
Pillow==10.2.0
pdf2image==1.16.3  # PDF işleme için
opencv-python==4.9.0.80  # OCR öncesi görüntü işleme için

# OCR
google-cloud-vision==3.7.1  # Google Cloud Vision API için

# Excel Processing
openpyxl==3.1.2  # Excel dosyaları için (.xlsx)
xlwt==1.3.0      # Eski Excel formatı için (.xls)
pandas==2.1.4    # Excel ve veri analizi için

# UI & Frontend
django-bootstrap5==23.4  # Bootstrap 5 entegrasyonu için

# Development & Debugging
python-dotenv==1.0.0  # Ortam değişkenleri için
django-debug-toolbar==4.2.0  # Geliştirme sırasında debugging için

# Testing
pytest==7.4.4
pytest-django==4.7.0

# Production
gunicorn==21.2.0  # Production sunucusu için
whitenoise==6.6.0  # Statik dosya sunumu için

# Security
django-cors-headers==4.3.1  # CORS yönetimi için

# Python Version
python_version = "3.10"
```

## Ortam Değişkenleri ve Konfigürasyon
--------------------------------
1. Ortam Değişkenlerinin Ayarlanması:
   - .env.example dosyasını .env olarak kopyalayın
   - .env dosyasındaki değişkenleri kendi ortamınıza göre düzenleyin:
     * SECRET_KEY: Django güvenlik anahtarı
     * DEBUG: Geliştirme modunda True, üretimde False olmalı
     * ALLOWED_HOSTS: İzin verilen host adresleri
     * GOOGLE_CLOUD_CREDENTIALS_PATH: Google Cloud Vision API kimlik bilgileri dosya yolu

2. Veritabanı Migrasyonları:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

3. Admin Kullanıcısı Oluşturma:
   ```bash
   python manage.py createsuperuser
   ```

4. Statik Dosyaları Toplama:
   ```bash
   python manage.py collectstatic
   ```

## Google Cloud Vision API Kurulumu
-------------------------------
1. Google Cloud Console'da yeni bir proje oluşturun
2. Cloud Vision API'yi etkinleştirin
3. Servis hesabı oluşturun ve JSON kimlik bilgilerini indirin
4. İndirilen JSON dosyasını proje dizininde güvenli bir yere kopyalayın
5. .env dosyasında GOOGLE_CLOUD_CREDENTIALS_PATH değişkenini güncelleyin

## Uygulamayı Çalıştırma
---------------------
Geliştirme sunucusu için:
```bash
python manage.py runserver
```

Uygulama varsayılan olarak http://127.0.0.1:8000 adresinde çalışacaktır.

## Klasör Yapısı
------------
```
gradelens/
├── core/                  # Ana uygulama kodları
├── media/                 # Yüklenen dosyalar
├── static/               # Statik dosyalar (CSS, JS, resimler)
│   ├── core/
│   │   ├── css/
│   │   ├── js/
│   │   └── images/
├── templates/            # HTML şablonları
├── logs/                 # Log dosyaları
├── credentials/          # API kimlik bilgileri
├── manage.py
├── requirements.txt
└── README.md
```

## Önemli URL'ler
-------------
- Admin paneli: /admin/
- Ana sayfa: /
- Sınav yükleme: /sinav-yukle/
- Sınav listesi: /sinav-listesi/
- Öğrenci listesi: /ogrenci-listesi/
- Sınav analiz: /sinav-analiz/<exam_id>/
- Öğrenci analiz: /ogrenci-analiz/<student_id>/
- Raporlar: /raporlar/
- Grafikler: /grafikler/

## Geliştirici Notları
------------------
- DEBUG modunda çalışırken performance.DEBUG ve security.W002 uyarılarını alabilirsiniz
- PDF dosyalarını işlerken Poppler kurulumunun doğru yapıldığından emin olun
- OCR işlemleri için Google Cloud Vision API kotanızı kontrol edin
- Büyük dosyalar yüklerken Apache/Nginx yapılandırmasındaki upload_max_filesize değerini kontrol edin

## Hata Ayıklama
------------
Uygulama loglarını logs/ dizininde bulabilirsiniz:
- debug.log: Genel uygulama logları
- error.log: Hata logları

## Güvenlik Uyarıları
-----------------
- .env dosyasını asla version kontrole eklemeyin
- Google Cloud kimlik bilgilerini güvenli tutun
- Üretim ortamında DEBUG=False olduğundan emin olun
- ALLOWED_HOSTS ayarını düzenleyin
- Hassas bilgileri içeren dosyaları .gitignore'a eklediğinizden emin olun

## Destek
------
Sorunlarınız için:
- GitHub Issues: <proje-issues-url>
- E-posta: aates21@posta.pau.edu.tr

## Lisans
------
Bu proje MIT lisansı altında lisanslanmıştır.

## Katkıda Bulunanlar
------------------
- Proje Sahibi: Ali Can Ateş
- Geliştirici: Ali Can Ateş

## Versiyon Geçmişi
---------------
- v1.0.0 - İlk sürüm (20.12.2024)
  * Temel özellikler
  * OCR entegrasyonu
  * Analiz araçları
