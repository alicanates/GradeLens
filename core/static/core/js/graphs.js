document.addEventListener('DOMContentLoaded', function() {
    const dataSourceSelect = document.getElementById('dataSourceSelect');
    const dimensionsContainer = document.getElementById('dimensionsContainer');
    const metricsContainer = document.getElementById('metricsContainer');
    const chartTypeSelect = document.getElementById('chartTypeSelect');
    const generateChartBtn = document.getElementById('generateChartBtn');
    const chartContainer = document.getElementById('chartContainer');

    let currentChart = null;
    let metadataCache = null;

    // Metadata'yı yükle
    async function loadMetadata() {
        try {
            const response = await fetch('/api/graph-metadata/');
            if (!response.ok) throw new Error('Metadata yüklenemedi');
            metadataCache = await response.json();
            updateSelectionUI();
        } catch (error) {
            console.error('Metadata yükleme hatası:', error);
            alert('Metadata yüklenirken bir hata oluştu.');
        }
    }

    // Seçim arayüzünü güncelle
    function updateSelectionUI() {
        if (!metadataCache) return;

        const selectedSource = dataSourceSelect.value;
        const sourceConfig = metadataCache.data_sources.find(s => s.id === selectedSource);
        const examSelectionContainer = document.getElementById('examSelectionContainer');

        if (!sourceConfig) return;

        // Soru Analizi seçiliyse sınav seçimini göster
        if (selectedSource === 'question_analysis') {
            examSelectionContainer.style.display = 'block';
            const examSelect = document.getElementById('examSelect');
            examSelect.innerHTML = `
                <option value="">Sınav seçiniz</option>
                ${metadataCache.exams.map(exam => `
                    <option value="${exam.id}">${exam.name}</option>
                `).join('')}
            `;
        } else {
            examSelectionContainer.style.display = 'none';
        }

        // Boyutları güncelle
        dimensionsContainer.innerHTML = sourceConfig.dimensions.map(dim => `
            <div class="form-check">
                <input class="form-check-input dimension-checkbox" type="checkbox" value="${dim}" id="dim_${dim}">
                <label class="form-check-label" for="dim_${dim}">
                    ${formatLabel(dim)}
                </label>
            </div>
        `).join('');

        // Metrikleri güncelle
        metricsContainer.innerHTML = sourceConfig.metrics.map(metric => `
            <div class="form-check">
                <input class="form-check-input metric-checkbox" type="checkbox" value="${metric}" id="metric_${metric}">
                <label class="form-check-label" for="metric_${metric}">
                    ${formatLabel(metric)}
                </label>
            </div>
        `).join('');
    }

    // Etiketleri formatla
    function formatLabel(key) {
        const labels = {
            'course': 'Ders',
            'exam_type': 'Sınav Türü',
            'semester': 'Dönem',
            'student': 'Öğrenci',
            'question_number': 'Soru Numarası',
            'avg_score': 'Ortalama Puan',
            'max_score': 'En Yüksek Puan',
            'min_score': 'En Düşük Puan',
            'student_count': 'Öğrenci Sayısı',
            'exam_count': 'Sınav Sayısı',
            'success_rate': 'Başarı Oranı'
        };
        return labels[key] || key;
    }

    // Sınav türünü formatla
    function formatExamType(examType) {
        const examTypes = {
            'VIZE': 'Vize',
            'FINAL': 'Final',
            'BUTUNLEME': 'Bütünleme',
            'MAZERET': 'Mazeret'
        };
        return examTypes[examType] || examType;
    }

    // Dönem formatla
    function formatSemester(semester) {
        const semesters = {
            'GUZ': 'Güz',
            'BAHAR': 'Bahar'
        };
        return semesters[semester] || semester;
    }

    // Grafik verilerini yükle
    async function loadChartData() {
        const selectedDimensions = [...document.querySelectorAll('.dimension-checkbox:checked')].map(cb => cb.value);
        const selectedMetrics = [...document.querySelectorAll('.metric-checkbox:checked')].map(cb => cb.value);

        if (!selectedDimensions.length || !selectedMetrics.length) {
            alert('Lütfen en az bir boyut ve bir metrik seçin.');
            return null;
        }

        try {
            const params = new URLSearchParams();
            params.append('source', dataSourceSelect.value);
            selectedDimensions.forEach(dim => params.append('dimensions[]', dim));
            selectedMetrics.forEach(metric => params.append('metrics[]', metric));

            // Soru analizi için sınav ID'sini ekle
            if (dataSourceSelect.value === 'question_analysis') {
                const examId = document.getElementById('examSelect').value;
                if (!examId) {
                    alert('Lütfen bir sınav seçin.');
                    return null;
                }
                params.append('exam_id', examId);
            }

            const response = await fetch(`/api/graph-data/?${params}`);
            if (!response.ok) throw new Error('Veri yüklenemedi');
            return await response.json();
        } catch (error) {
            console.error('Veri yükleme hatası:', error);
            alert('Veriler yüklenirken bir hata oluştu.');
            return null;
        }
    }

    // Grafiği oluştur
    async function generateChart() {
        const selectedDimensions = [...document.querySelectorAll('.dimension-checkbox:checked')].map(cb => cb.value);
        const selectedMetrics = [...document.querySelectorAll('.metric-checkbox:checked')].map(cb => cb.value);

        if (!selectedDimensions.length || !selectedMetrics.length) {
            alert('Lütfen en az bir boyut ve bir metrik seçin.');
            return;
        }

        const data = await loadChartData();
        if (!data) return;

        // Eğer mevcut bir grafik varsa temizle
        if (currentChart) {
            currentChart.destroy();
        }

        const chartType = chartTypeSelect.value;

        // Her ders/öğrenci için sabit renk atamak üzere renk paleti
        const colorPalette = {
            primary: [
                '#2196F3',  // Mavi
                '#FF9800',  // Turuncu
                '#4CAF50',  // Yeşil
                '#F44336',  // Kırmızı
                '#9C27B0',  // Mor
                '#00BCD4',  // Camgöbeği
                '#FFC107',  // Amber
                '#795548',  // Kahverengi
                '#607D8B',  // Mavi Gri
                '#E91E63'   // Pembe
            ],
            secondary: [
                '#1976D2',  // Koyu Mavi
                '#FF5722',  // Koyu Turuncu
                '#388E3C',  // Koyu Yeşil
                '#D32F2F',  // Koyu Kırmızı
                '#7B1FA2',  // Koyu Mor
                '#0097A7',  // Koyu Camgöbeği
                '#FFA000',  // Koyu Amber
                '#5D4037',  // Koyu Kahverengi
                '#455A64',  // Koyu Mavi Gri
                '#C2185B'   // Koyu Pembe
            ]
        };

        // Etiketleri ve benzersiz tanımlayıcıları oluştur
        const uniqueLabels = [...new Set(data.map(item => {
            if (item.question_number) {
                return `${item.exam_code} - Soru ${item.question_number}`;
            } else {
                const parts = [];

                // Sınav türü
                if (item.exam__exam_type) {
                    parts.push(formatExamType(item.exam__exam_type));
                }

                // Dönem
                if (item.exam__semester) {
                    parts.push(formatSemester(item.exam__semester));
                }

                // Ders bilgisi
                if (item.exam__course__code && item.exam__course__name) {
                    parts.push(`${item.exam__course__code} - ${item.exam__course__name}`);
                }

                // Öğrenci bilgisi
                if (item.student__student_number && item.student__full_name) {
                    parts.push(`${item.student__full_name} (${item.student__student_number})`);
                }

                return parts.join(' - ') || 'N/A';
            }
        }))];

        const chartData = {
            labels: uniqueLabels,
            datasets: selectedMetrics.map((metric, metricIndex) => {
                const metricMap = {
                    'max_score': 'max_score',
                    'min_score': 'min_score',
                    'avg_score': 'avg_score',
                    'student_count': 'student_count',
                    'exam_count': 'exam_count',
                    'success_rate': 'success_rate'
                };

                // Her veri noktası için renk ata
                const colors = uniqueLabels.map((_, index) => {
                    // Metrik indeksine göre birincil veya ikincil renk seç
                    const colorSet = metricIndex === 0 ? colorPalette.primary : colorPalette.secondary;
                    return colorSet[index % colorSet.length];
                });

                return {
                    label: formatLabel(metric),
                    data: data.map(item => parseFloat(item[metricMap[metric]] || 0)),
                    backgroundColor: colors,
                    borderColor: chartType === 'pie' ? 'rgba(255, 255, 255, 0.5)' : colors,
                    borderWidth: chartType === 'pie' ? 2 : 1
                };
            })
        };

        const ctx = document.getElementById('chartContainer').getContext('2d');
        currentChart = new Chart(ctx, {
            type: chartType,
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: true,
                        text: 'Veri Analizi'
                    }
                },
                scales: chartType !== 'pie' ? {
                    y: {
                        beginAtZero: true
                    }
                } : {}
            }
        });
    }

    // Event Listeners
    dataSourceSelect.addEventListener('change', updateSelectionUI);
    generateChartBtn.addEventListener('click', generateChart);

    // Export butonları için event listeners
    document.getElementById('exportPNG').addEventListener('click', () => {
        if (!currentChart) return;
        const link = document.createElement('a');
        link.download = 'grafik.png';
        link.href = currentChart.canvas.toDataURL('image/png');
        link.click();
    });

    document.getElementById('exportPDF').addEventListener('click', () => {
        if (!currentChart) return;
        const canvas = currentChart.canvas;
        const imgData = canvas.toDataURL('image/png');

        // jsPDF'i window.jspdf'den al
        const { jsPDF } = window.jspdf;

        const pdf = new jsPDF({
            orientation: canvas.width > canvas.height ? 'l' : 'p',
            unit: 'px',
            format: [canvas.width, canvas.height]
        });

        pdf.addImage(imgData, 'PNG', 0, 0, canvas.width, canvas.height);
        pdf.save('grafik.pdf');
    });

    // Başlangıç yüklemesi
    loadMetadata();
});