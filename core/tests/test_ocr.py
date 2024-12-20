from pdf2image import convert_from_path
from PIL import Image
import pytesseract
import re
from datetime import datetime
import os

# Tesseract'ın yolu (Windows için)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def process_exam_file(file_path):
    """
    OCR işlemi yaparak sınav kağıdındaki bilgileri okur.
    Ad soyad bilgisi parse ediliyor ancak final sözlükte yer almıyor.
    """
    # Eğer dosya PDF ise önce resme dönüştür
    if file_path.lower().endswith('.pdf'):
        images = convert_from_path(file_path, poppler_path=r'C:\poppler-24.08.0\Library\bin')
        img = images[0]  # İlk sayfayı kullan
    else:
        img = Image.open(file_path)

    # OCR ile metni al
    text = pytesseract.image_to_string(img)
    print(f"OCR'den alınan metin:\n{text}\n")

    # OCR sonucunda bozuk karakterleri düzeltme (Örneğin § -> g)
    text = text.replace("§", "g")

    # "Ad Soyad" ve "Ogrenci No" bilgisini ayıkla
    student_info_match = re.search(
        r'Ad Soyad:\s*([\w\sçöşğüıÇÖŞĞÜİ-]+)\s*O\w+renci No:\s*(\d+)',
        text,
        re.IGNORECASE
    )

    student_name = None
    student_number = None

    if student_info_match:
        student_name = student_info_match.group(1).strip() if student_info_match.group(1).strip() else "Bilinmiyor"
        student_number = student_info_match.group(2).strip()

    # Sınav tarihi
    exam_date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', text)
    exam_date = None
    if exam_date_match:
        raw_date = exam_date_match.group(1)  # DD.MM.YYYY formatındaki tarih
        exam_date = datetime.strptime(raw_date, '%d.%m.%Y').strftime('%Y-%m-%d')  # YYYY-MM-DD formatına dönüştür

    # Puan tablosunu bul (soru puanları ve öğrenci puanları)
    text = text.replace("é", "")
    scores_match = re.findall(r"^(\d+(?: \d+)*?)\s*$", text, re.MULTILINE)

    question_scores = []
    student_scores = []

    if len(scores_match) >= 2:
        question_scores = list(map(int, scores_match[0].split()))
        student_scores = list(map(int, scores_match[1].split()))

    return {
        'number': student_number,
        'date': exam_date,
        'question_scores': question_scores,
        'student_scores': student_scores,
    }

if __name__ == "__main__":
    # Test için dosya yolu girin
    test_file_path = r"C:\Users\can\Desktop\image.png"
    if not os.path.exists(test_file_path):
        print("Görüntü bulunamadı, lütfen dosya yolunu kontrol edin.")
    else:
        result = process_exam_file(test_file_path)
        print("OCR Sonuçları (final sözlük):")
        print(result)
