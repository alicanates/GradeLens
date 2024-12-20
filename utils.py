from google.cloud import vision
import os
import io
from PIL import Image
import re
from datetime import datetime
from pdf2image import convert_from_path


def get_project_root():
    """Proje kök dizinini bulur"""
    try:
        current_path = os.path.abspath(__file__)
    except NameError:
        current_path = os.path.abspath(os.getcwd())

    project_root = os.path.dirname(os.path.dirname(current_path))
    return project_root


def initialize_vision_client():
    """Google Cloud Vision istemcisini başlatır"""
    try:
        credentials_path = os.getenv('GOOGLE_CLOUD_CREDENTIALS_PATH')

        print(f"Aranan kimlik dosyası yolu: {credentials_path}")

        if not os.path.exists(credentials_path):
            raise FileNotFoundError(f"Kimlik dosyası bulunamadı: {credentials_path}")

        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        client = vision.ImageAnnotatorClient()
        return client
    except Exception as e:
        print(f"Vision Client başlatılamadı: {str(e)}")
        return None


def test_credentials():
    """Kimlik dosyası yolunu test eder"""
    try:
        credentials_path = os.getenv('GOOGLE_CLOUD_CREDENTIALS_PATH')

        if not credentials_path:
            print("GOOGLE_CLOUD_CREDENTIALS_PATH çevre değişkeni ayarlanmamış.")
            return None

        print(f"Kimlik dosyası mevcut mu?: {os.path.exists(credentials_path)}")
        print(f"Çalışma dizini: {os.getcwd()}")

        return credentials_path
    except Exception as e:
        print(f"Test sırasında hata: {str(e)}")
        return None


def process_exam_file(file_path, course_code, semester):
    """
    Google Cloud Vision API kullanarak sınav kağıdındaki bilgileri okur.
    Dinamik soru sayısı desteği ve boşluk içeren öğrenci numarasını
    8 basamakla sınırlamak için ek kontrol içerir.
    """

    try:
        client = initialize_vision_client()
        if not client:
            raise Exception("Vision Client başlatılamadı")

        # poppler_path'i çevre değişkeninden al
        poppler_path = os.getenv('POPPLER_PATH')
        if not poppler_path or not os.path.exists(poppler_path):
            print("Uyarı: poppler_path bulunamadı, varsayılan PATH kullanılacak.")
            poppler_path = None

        # PDF ise resme dönüştür
        if file_path.lower().endswith('.pdf'):
            images = convert_from_path(file_path, poppler_path=poppler_path)
            img = images[0]  # İlk sayfayı kullan
            temp_path = os.path.join(os.path.dirname(file_path), "temp_image.jpg")
            img.save(temp_path)
            file_path = temp_path

        # Resmi oku
        with io.open(file_path, 'rb') as image_file:
            content = image_file.read()

        image = vision.Image(content=content)
        context = vision.ImageContext(
            language_hints=['tr'],
            text_detection_params=vision.TextDetectionParams(
                enable_text_detection_confidence_score=True
            )
        )

        response = client.document_text_detection(image=image, image_context=context)
        text = response.full_text_annotation.text

        # Eğer geçici dosya yarattıysak sil
        if file_path.endswith("temp_image.jpg"):
            os.remove(file_path)

        print(f"OCR'den alınan metin:\n{text}\n")

        # OCR düzeltmeleri
        text = text.replace("§", "g")
        text = text.replace("O§", "Og")
        text = text.replace("é", "")

        # Öğrenci bilgilerini bul - boşluklu ve bazen fazla karakterli no için gelişmiş düzen
        student_info_match = re.search(
            r'Ad\s*Soyad:?\s*([\w\sçöşğüıÇÖŞĞÜİ-]+).*?(?:Ogrenci|Öğrenci|Ögrenci)\s*No:?\s*(\d+(?:\s*\d+)*)',
            text,
            re.IGNORECASE | re.DOTALL
        )

        student_name = "Bilinmiyor"
        student_number = None

        if student_info_match:
            s_name = student_info_match.group(1).strip()
            student_number_raw = student_info_match.group(2).strip()
            # Boşlukları ve rakam dışı karakterleri temizle
            student_number = re.sub(r'\D', '', student_number_raw)
            # İlk 8 basamağı al
            if len(student_number) > 8:
                student_number = student_number[:8]
            student_name = s_name if s_name else "Bilinmiyor"
            print(f"Bulunan öğrenci no: {student_number}")
        else:
            student_name = "Bilinmiyor"
            student_number = None

        # Sınav tarihi
        exam_date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', text)
        exam_date = None
        if exam_date_match:
            raw_date = exam_date_match.group(1)
            exam_date = datetime.strptime(raw_date, '%d.%m.%Y').strftime('%Y-%m-%d')

        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            # 'Sorul' → 'Soru1'
            line = re.sub(r'\bSorul\b', 'Soru1', line, flags=re.IGNORECASE)
            cleaned_lines.append(line.strip())

        # Başlıkları bul (SoruX + Toplam)
        soru_lines = []
        header_found = False
        header_line_index = -1
        for i, line in enumerate(cleaned_lines):
            if line.lower().startswith('soru'):
                soru_lines.append(line)
            if 'Toplam' in line:
                soru_lines.append('Toplam')
                header_found = True
                header_line_index = i
                print(f"Başlık(lar) bulundu: {soru_lines}")
                break

        total_sorular = 0
        if header_found and 'Toplam' in soru_lines:
            total_sorular = len(soru_lines) - 1

        score_data = []
        if header_found and total_sorular > 0:
            # Her satır (total_sorular + 1) sayıdan oluşmalı
            expected_count = total_sorular + 1
            numeric_lines = []
            for line in cleaned_lines[header_line_index + 1:]:
                if line.isdigit():
                    numeric_lines.append(int(line))
                    if len(numeric_lines) == expected_count:
                        score_data.append(numeric_lines)
                        numeric_lines = []

        print(f"Bulunan tüm puan satırları: {score_data}")

        question_scores = []
        student_scores = []

        if len(score_data) >= 2:
            first_row = score_data[0]
            second_row = score_data[1]

            # Eğer her iki satırın son elemanı 100 ise onu toplam kabul edip çıkar
            if first_row[-1] == 100 and second_row[-1] == 100:
                question_scores = first_row[:-1]
                student_scores = second_row[:-1]
            else:
                # Aksi halde son elemanı toplam varsayıp, onu hariç tutuyoruz
                question_scores = first_row[:-1]
                student_scores = second_row[:-1]

        print(f"Soru puanları: {question_scores}")
        print(f"Öğrenci puanları: {student_scores}")

        # Soru puanlarının toplamını kontrol et
        if question_scores:
            total = sum(question_scores)
            if total != 100:
                print(f"Uyarı: Soru puanlarının toplamı 100 değil, {total}")

        return {
            'student_number': student_number,
            'student_name': student_name,
            'exam_date': exam_date,
            'question_scores': question_scores,
            'student_scores': student_scores,
            'course_code': course_code,
            'semester': semester
        }

    except Exception as e:
        print(f"OCR işlemi sırasında hata oluştu: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def cleanup_temp_files():
    """Geçici dosyaları temizler"""
    if os.path.exists("temp_image.jpg"):
        os.remove("temp_image.jpg")
