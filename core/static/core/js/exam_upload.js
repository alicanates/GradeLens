document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('examUploadForm');
    const uploadTypeInputs = document.querySelectorAll('input[name="upload_type"]');
    const existingExamSelect = document.getElementById('existing_exam_select');
    const newExamFields = document.getElementById('new_exam_fields');
    const examFilesInput = document.getElementById('exam_files');
    const studentListInput = document.getElementById('student_list');

    // Form alanlarını toggle et
    function toggleFormFields() {
        const selectedValue = document.querySelector('input[name="upload_type"]:checked').value;
        if (selectedValue === 'existing') {
            existingExamSelect.style.display = 'block';
            newExamFields.style.display = 'none';
            // Yeni sınav alanlarını opsiyonel yap
            document.querySelectorAll('#new_exam_fields select, #new_exam_fields input').forEach(element => {
                element.removeAttribute('required');
            });
            // Mevcut sınav seçimini zorunlu yap
            document.getElementById('existing_exam_id').setAttribute('required', '');
        } else {
            existingExamSelect.style.display = 'none';
            newExamFields.style.display = 'block';
            // Yeni sınav alanlarını zorunlu yap
            document.querySelectorAll('#new_exam_fields select, #new_exam_fields input').forEach(element => {
                if (element.getAttribute('data-required') !== 'false') {
                    element.setAttribute('required', '');
                }
            });
            // Mevcut sınav seçimini opsiyonel yap
            document.getElementById('existing_exam_id').removeAttribute('required');
        }
    }

    // Dosya validasyonu
    function validateFiles(input, allowedExtensions, maxSize) {
        const files = input.files;
        const errors = [];

        if (files.length === 0) {
            errors.push('Lütfen dosya seçin.');
            return errors;
        }

        for (let file of files) {
            // Dosya uzantısı kontrolü
            const extension = file.name.split('.').pop().toLowerCase();
            if (!allowedExtensions.includes(extension)) {
                errors.push(`"${file.name}" dosyası için geçersiz uzantı. İzin verilen uzantılar: ${allowedExtensions.join(', ')}`);
            }

            // Dosya boyutu kontrolü (maxSize MB)
            if (file.size > maxSize * 1024 * 1024) {
                errors.push(`"${file.name}" dosyası çok büyük. Maksimum dosya boyutu: ${maxSize}MB`);
            }
        }

        return errors;
    }

    // Hata mesajı gösterme
    function showError(input, message) {
        const formGroup = input.closest('.form-group');
        const errorDiv = formGroup.querySelector('.invalid-feedback') || document.createElement('div');
        errorDiv.className = 'invalid-feedback';
        errorDiv.textContent = message;
        input.classList.add('is-invalid');
        
        if (!formGroup.querySelector('.invalid-feedback')) {
            input.parentNode.appendChild(errorDiv);
        }
    }

    // Başarı durumunu gösterme
    function showSuccess(input) {
        input.classList.remove('is-invalid');
        input.classList.add('is-valid');
        const errorDiv = input.parentNode.querySelector('.invalid-feedback');
        if (errorDiv) {
            errorDiv.remove();
        }
    }

    // Sürükle-bırak işlevselliği
    const uploadArea = document.querySelector('.upload-area');

    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('border-primary');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('border-primary');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('border-primary');
        
        const files = e.dataTransfer.files;
        examFilesInput.files = files;

        // Dosya validasyonu
        const errors = validateFiles(examFilesInput, ['pdf', 'jpg', 'jpeg', 'png'], 10);
        if (errors.length > 0) {
            showError(examFilesInput, errors.join('\n'));
            return;
        }

        showSuccess(examFilesInput);
        updateFileList(files);
    });

    // Dosya listesi güncelleme
    function updateFileList(files) {
        const fileMessage = document.createElement('div');
        fileMessage.className = 'text-success mt-2';
        fileMessage.textContent = `${files.length} dosya seçildi`;

        // Varsa eski mesajı kaldır
        const oldMessage = uploadArea.querySelector('.text-success');
        if (oldMessage) {
            oldMessage.remove();
        }
        uploadArea.appendChild(fileMessage);
    }

    // Form submit kontrolü
    form.addEventListener('submit', function(event) {
        let isValid = true;

        // Sınav dosyaları kontrolü
        const examFileErrors = validateFiles(examFilesInput, ['pdf', 'jpg', 'jpeg', 'png'], 10);
        if (examFileErrors.length > 0) {
            isValid = false;
            showError(examFilesInput, examFileErrors.join('\n'));
        } else {
            showSuccess(examFilesInput);
        }

        // Excel dosyası kontrolü
        const studentListErrors = validateFiles(studentListInput, ['xls', 'xlsx'], 5);
        if (studentListErrors.length > 0) {
            isValid = false;
            showError(studentListInput, studentListErrors.join('\n'));
        } else {
            showSuccess(studentListInput);
        }

        // Gerekli alan kontrolü
        const requiredInputs = form.querySelectorAll('[required]');
        requiredInputs.forEach(input => {
            if (!input.value) {
                isValid = false;
                showError(input, 'Bu alan zorunludur.');
            } else {
                showSuccess(input);
            }
        });

        if (!isValid) {
            event.preventDefault();
            event.stopPropagation();
        }
    });

    // Upload type değişikliklerini izle
    uploadTypeInputs.forEach(input => {
        input.addEventListener('change', toggleFormFields);
    });

    // Sayfa yüklendiğinde form alanlarını ayarla
    toggleFormFields();
});