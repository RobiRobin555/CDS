// ============================================
// IMPORT.JS - Excel/PDF Import Handler
// ============================================

const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
let parsedData = [];

document.addEventListener('DOMContentLoaded', function() {
    setupDragAndDrop();
    setupFileInput();
});

// Setup drag and drop
function setupDragAndDrop() {
    if(!uploadArea) return;

    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if(files.length > 0) {
            handleFile(files[0]);
        }
    });

    // Click to upload
    uploadArea.addEventListener('click', () => {
        fileInput.click();
    });
}

// Setup file input
function setupFileInput() {
    if(!fileInput) return;

    fileInput.addEventListener('change', (e) => {
        if(e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    });
}

// Handle file upload
function handleFile(file) {
    // Validate file size (5MB max)
    if(file.size > 5 * 1024 * 1024) {
        showAlert('File quá lớn! Vui lòng chọn file nhỏ hơn 5MB', 'error');
        return;
    }

    // Validate file type
    const validTypes = [
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-excel',
        'text/csv'
    ];
    
    const validExtensions = /\.(xlsx|xls|csv)$/i;
    
    if(!validTypes.includes(file.type) && !validExtensions.test(file.name)) {
        showAlert('Định dạng file không hợp lệ! Chỉ chấp nhận .xlsx, .xls, .csv', 'error');
        return;
    }

    // Show loading
    document.getElementById('loading').classList.add('active');

    // Parse file with SheetJS
    const reader = new FileReader();
    
    reader.onload = function(e) {
        try {
            const data = new Uint8Array(e.target.result);
            const workbook = XLSX.read(data, {type: 'array'});
            
            // Get first sheet
            const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
            const jsonData = XLSX.utils.sheet_to_json(firstSheet, {header: 1});
            
            parseScheduleData(jsonData);
            
        } catch(error) {
            console.error('Parse error:', error);
            showAlert('Lỗi khi đọc file: ' + error.message, 'error');
        } finally {
            document.getElementById('loading').classList.remove('active');
        }
    };
    
    reader.onerror = function() {
        showAlert('Lỗi khi đọc file', 'error');
        document.getElementById('loading').classList.remove('active');
    };
    
    reader.readAsArrayBuffer(file);
}

// Parse schedule data from Excel
function parseScheduleData(rawData) {
    parsedData = [];
    
    // Skip header row (first row)
    for(let i = 1; i < rawData.length; i++) {
        const row = rawData[i];
        
        // Skip empty rows
        if(!row || row.length === 0 || !row[0]) continue;
        
        const schedule = {
            subject: String(row[0] || '').trim(),
            date: row[1] || '',
            startTime: row[2] || '',
            endTime: row[3] || '',
            location: String(row[4] || '').trim()
        };

        // Validate required fields
        if(schedule.subject && schedule.date && schedule.startTime && schedule.endTime) {
            // Format date
            schedule.formattedDate = formatExcelDate(schedule.date);
            
            // Create datetime strings
            schedule.start_time = `${schedule.formattedDate}T${formatExcelTime(schedule.startTime)}:00`;
            schedule.end_time = `${schedule.formattedDate}T${formatExcelTime(schedule.endTime)}:00`;
            
            parsedData.push(schedule);
        }
    }

    if(parsedData.length === 0) {
        showAlert('Không tìm thấy dữ liệu hợp lệ trong file!', 'error');
        return;
    }

    showPreview();
}

// Format Excel date to YYYY-MM-DD
function formatExcelDate(date) {
    if(!date) return '';
    
    // If already a string in dd/mm/yyyy format
    if(typeof date === 'string' && date.includes('/')) {
        const parts = date.split('/');
        if(parts.length === 3) {
            const day = parts[0].padStart(2, '0');
            const month = parts[1].padStart(2, '0');
            const year = parts[2];
            return `${year}-${month}-${day}`;
        }
    }
    
    // If Excel serial number
    if(typeof date === 'number') {
        const excelEpoch = new Date(1899, 11, 30);
        const jsDate = new Date(excelEpoch.getTime() + date * 86400000);
        return jsDate.toISOString().split('T')[0];
    }
    
    // Try to parse as date
    const parsed = new Date(date);
    if(!isNaN(parsed.getTime())) {
        return parsed.toISOString().split('T')[0];
    }
    
    return '';
}

// Format Excel time to HH:MM
function formatExcelTime(time) {
    if(!time) return '00:00';
    
    // If already a string
    if(typeof time === 'string') {
        // Remove seconds if present
        const parts = time.split(':');
        return `${parts[0].padStart(2, '0')}:${parts[1].padStart(2, '0')}`;
    }
    
    // If Excel decimal (0.5 = 12:00)
    if(typeof time === 'number') {
        const hours = Math.floor(time * 24);
        const minutes = Math.floor((time * 24 - hours) * 60);
        return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
    }
    
    return '00:00';
}

// Show preview table
function showPreview() {
    const tbody = document.getElementById('previewTableBody');
    tbody.innerHTML = '';

    parsedData.forEach((item, index) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${index + 1}</td>
            <td>${item.subject}</td>
            <td>${item.formattedDate}</td>
            <td>${formatExcelTime(item.startTime)}</td>
            <td>${formatExcelTime(item.endTime)}</td>
            <td>${item.location}</td>
        `;
        tbody.appendChild(row);
    });

    document.getElementById('previewSection').classList.add('active');
    
    showAlert(`✅ Đã phát hiện ${parsedData.length} lịch học. Vui lòng kiểm tra và xác nhận.`, 'success');
}

// Confirm import
async function confirmImport() {
    document.getElementById('loading').classList.add('active');
    
    try {
        let successCount = 0;
        let errorCount = 0;
        
        // Import each schedule
        for(const schedule of parsedData) {
            try {
                const scheduleData = {
                    subject: schedule.subject,
                    start_time: schedule.start_time,
                    end_time: schedule.end_time,
                    location: schedule.location,
                    type: 'class',
                    color: '#3788d8'
                };
                
                await api.addSchedule(scheduleData);
                successCount++;
            } catch(error) {
                console.error('Error importing schedule:', error);
                errorCount++;
            }
        }
        
        if(errorCount === 0) {
            api.showNotification(`🎉 Đã import thành công ${successCount} lịch học!`, 'success');
        } else {
            api.showNotification(`⚠️ Import hoàn tất: ${successCount} thành công, ${errorCount} lỗi`, 'warning');
        }
        
        setTimeout(() => {
            window.location.href = '/dashboard.html';
        }, 2000);
        
    } catch(error) {
        api.showNotification('❌ Lỗi khi import', 'error');
    } finally {
        document.getElementById('loading').classList.remove('active');
    }
}

// Cancel import
function cancelImport() {
    document.getElementById('previewSection').classList.remove('active');
    parsedData = [];
    fileInput.value = '';
    document.getElementById('alertContainer').innerHTML = '';
}

// Show alert
function showAlert(message, type = 'info') {
    const alertContainer = document.getElementById('alertContainer');
    if(!alertContainer) return;

    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.textContent = message;
    alertContainer.innerHTML = '';
    alertContainer.appendChild(alert);

    // Auto remove after 5 seconds
    setTimeout(() => {
        alert.remove();
    }, 5000);
}

// Download template
function downloadTemplate(type) {
    // Create template data
    const templateData = [
        ['Môn học', 'Ngày', 'Giờ bắt đầu', 'Giờ kết thúc', 'Phòng học'],
        ['Toán Cao Cấp', '16/10/2025', '08:00', '10:00', 'A201'],
        ['Lập Trình Web', '16/10/2025', '13:00', '15:00', 'B305'],
        ['Vật Lý Đại Cương', '18/10/2025', '15:00', '17:00', 'C102']
    ];

    // Create workbook
    const ws = XLSX.utils.aoa_to_sheet(templateData);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Lịch học');

    // Set column widths
    ws['!cols'] = [
        {wch: 20},
        {wch: 12},
        {wch: 12},
        {wch: 12},
        {wch: 15}
    ];

    // Download
    if(type === 'excel') {
        XLSX.writeFile(wb, 'Mau_Lich_Hoc.xlsx');
    } else {
        XLSX.writeFile(wb, 'Mau_Lich_Hoc.csv');
    }

    api.showNotification('📥 Đã tải mẫu file thành công!', 'success');
}