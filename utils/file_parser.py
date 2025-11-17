"""
utils/file_parser.py - Parse Excel/PDF files để import lịch học
"""

import openpyxl
from datetime import datetime, timedelta
import re
import os


def parse_excel_schedule(file_path):
    """
    Parse file Excel lịch học
    
    Expected format:
    | Môn học | Ngày | Giờ bắt đầu | Giờ kết thúc | Phòng | Loại | Mô tả |
    
    Args:
        file_path: Đường dẫn file Excel
    
    Returns:
        List of dict schedules, hoặc dict with error
    """
    try:
        wb = openpyxl.load_workbook(file_path, read_only=True)
        sheet = wb.active
        
        schedules = []
        errors = []
        
        # Đọc header (row 1)
        headers = [cell.value for cell in sheet[1]]
        
        # Detect columns
        col_mapping = detect_excel_columns(headers)
        
        if 'error' in col_mapping:
            return {'error': col_mapping['error']}
        
        # Parse data từ row 2
        for idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
            if not row or not any(row):  # Skip empty rows
                continue
            
            try:
                schedule = parse_excel_row(row, col_mapping)
                
                if schedule:
                    schedules.append(schedule)
            except Exception as e:
                errors.append(f"Row {idx}: {str(e)}")
        
        wb.close()
        
        return {
            'schedules': schedules,
            'total': len(schedules),
            'errors': errors
        }
    
    except FileNotFoundError:
        return {'error': 'File not found'}
    except Exception as e:
        return {'error': f'Failed to parse Excel: {str(e)}'}


def detect_excel_columns(headers):
    """
    Tự động detect các cột trong Excel
    Support nhiều format header khác nhau
    """
    headers_lower = [str(h).lower() if h else '' for h in headers]
    
    mapping = {}
    
    # Môn học / Subject
    for idx, h in enumerate(headers_lower):
        if any(keyword in h for keyword in ['môn', 'subject', 'tên môn', 'course']):
            mapping['subject'] = idx
            break
    
    # Ngày / Date
    for idx, h in enumerate(headers_lower):
        if any(keyword in h for keyword in ['ngày', 'date', 'thứ']):
            mapping['date'] = idx
            break
    
    # Giờ bắt đầu / Start time
    for idx, h in enumerate(headers_lower):
        if any(keyword in h for keyword in ['bắt đầu', 'start', 'từ', 'from']):
            mapping['start_time'] = idx
            break
    
    # Giờ kết thúc / End time
    for idx, h in enumerate(headers_lower):
        if any(keyword in h for keyword in ['kết thúc', 'end', 'đến', 'to']):
            mapping['end_time'] = idx
            break
    
    # Phòng / Location
    for idx, h in enumerate(headers_lower):
        if any(keyword in h for keyword in ['phòng', 'room', 'location', 'địa điểm']):
            mapping['location'] = idx
            break
    
    # Loại / Type (optional)
    for idx, h in enumerate(headers_lower):
        if any(keyword in h for keyword in ['loại', 'type', 'hình thức']):
            mapping['type'] = idx
            break
    
    # Mô tả / Description (optional)
    for idx, h in enumerate(headers_lower):
        if any(keyword in h for keyword in ['mô tả', 'description', 'ghi chú', 'note']):
            mapping['description'] = idx
            break
    
    # Validate required fields
    required = ['subject', 'date', 'start_time', 'end_time']
    missing = [field for field in required if field not in mapping]
    
    if missing:
        return {'error': f'Missing required columns: {", ".join(missing)}'}
    
    return mapping


def parse_excel_row(row, col_mapping):
    """Parse một dòng Excel thành schedule dict"""
    
    # Extract values
    subject = row[col_mapping['subject']]
    date = row[col_mapping['date']]
    start_time = row[col_mapping['start_time']]
    end_time = row[col_mapping['end_time']]
    location = row[col_mapping['location']] if 'location' in col_mapping and col_mapping['location'] < len(row) else ''
    schedule_type = row[col_mapping['type']] if 'type' in col_mapping and col_mapping['type'] < len(row) else 'class'
    description = row[col_mapping['description']] if 'description' in col_mapping and col_mapping['description'] < len(row) else ''
    
    # Validate
    if not subject:
        return None
    
    # Parse date
    parsed_date = parse_date(date)
    if not parsed_date:
        raise ValueError(f"Invalid date format: {date}")
    
    # Parse times
    parsed_start = parse_time(start_time)
    parsed_end = parse_time(end_time)
    
    if not parsed_start or not parsed_end:
        raise ValueError(f"Invalid time format: {start_time} - {end_time}")
    
    # Combine date + time
    start_datetime = f"{parsed_date} {parsed_start}:00"
    end_datetime = f"{parsed_date} {parsed_end}:00"
    
    return {
        'subject': str(subject).strip(),
        'description': str(description).strip() if description else '',
        'start_time': start_datetime,
        'end_time': end_datetime,
        'location': str(location).strip() if location else '',
        'type': normalize_schedule_type(schedule_type),
        'color': assign_color_by_subject(subject),
        'reminder_time': 30
    }


def parse_date(date_value):
    """
    Parse date từ nhiều format khác nhau
    
    Support:
    - datetime object
    - String: YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY
    - Thứ X ngày DD/MM
    """
    if isinstance(date_value, datetime):
        return date_value.strftime('%Y-%m-%d')
    
    date_str = str(date_value).strip()
    
    # Try ISO format: YYYY-MM-DD
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%Y-%m-%d')
    except ValueError:
        pass
    
    # Try DD/MM/YYYY
    try:
        dt = datetime.strptime(date_str, '%d/%m/%Y')
        return dt.strftime('%Y-%m-%d')
    except ValueError:
        pass
    
    # Try DD-MM-YYYY
    try:
        dt = datetime.strptime(date_str, '%d-%m-%Y')
        return dt.strftime('%Y-%m-%d')
    except ValueError:
        pass
    
    # Try "Thứ X, DD/MM"
    match = re.search(r'(\d{1,2})/(\d{1,2})', date_str)
    if match:
        day, month = match.groups()
        current_year = datetime.now().year
        try:
            dt = datetime(current_year, int(month), int(day))
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            pass
    
    return None


def parse_time(time_value):
    """
    Parse time từ nhiều format
    
    Support:
    - time object
    - String: HH:MM, HH:MM:SS, HHhMM
    - Float: 8.0 -> 08:00, 14.5 -> 14:30
    """
    if hasattr(time_value, 'hour'):  # time object
        return f"{time_value.hour:02d}:{time_value.minute:02d}"
    
    if isinstance(time_value, (int, float)):
        hour = int(time_value)
        minute = int((time_value - hour) * 60)
        return f"{hour:02d}:{minute:02d}"
    
    time_str = str(time_value).strip()
    
    # Try HH:MM or HH:MM:SS
    match = re.match(r'^(\d{1,2}):(\d{2})', time_str)
    if match:
        hour, minute = match.groups()
        return f"{int(hour):02d}:{int(minute):02d}"
    
    # Try HHhMM (Vietnamese format)
    match = re.match(r'^(\d{1,2})h(\d{2})', time_str)
    if match:
        hour, minute = match.groups()
        return f"{int(hour):02d}:{int(minute):02d}"
    
    # Try just number: 8 -> 08:00
    try:
        hour = int(float(time_str))
        return f"{hour:02d}:00"
    except ValueError:
        pass
    
    return None


def normalize_schedule_type(type_value):
    """Chuẩn hóa loại lịch"""
    if not type_value:
        return 'class'
    
    type_str = str(type_value).lower().strip()
    
    type_mapping = {
        'class': ['lớp', 'class', 'học', 'lecture'],
        'exam': ['thi', 'exam', 'test', 'kiểm tra'],
        'meeting': ['họp', 'meeting', 'seminar'],
        'lab': ['lab', 'thí nghiệm', 'thực hành']
    }
    
    for normalized, keywords in type_mapping.items():
        if any(keyword in type_str for keyword in keywords):
            return normalized
    
    return 'class'


def assign_color_by_subject(subject):
    """Tự động gán màu dựa trên môn học"""
    subject_lower = subject.lower()
    
    color_map = {
        'toán': '#FF5722',
        'lý': '#2196F3',
        'hóa': '#4CAF50',
        'văn': '#9C27B0',
        'anh': '#FF9800',
        'lập trình': '#3F51B5',
        'python': '#3776AB',
        'java': '#F89820',
        'web': '#E44D26',
        'database': '#336791',
        'ai': '#FF6F00',
        'machine learning': '#FF6F00'
    }
    
    for keyword, color in color_map.items():
        if keyword in subject_lower:
            return color
    
    # Default colors
    default_colors = ['#3788d8', '#FF5733', '#4CAF50', '#9C27B0', '#FF9800']
    return default_colors[hash(subject) % len(default_colors)]


def validate_schedules(schedules):
    """
    Validate danh sách schedules trước khi import
    
    Returns:
        (valid_schedules, invalid_schedules, warnings)
    """
    valid = []
    invalid = []
    warnings = []
    
    for idx, schedule in enumerate(schedules):
        errors = []
        
        # Validate required fields
        if not schedule.get('subject'):
            errors.append('Missing subject')
        
        # Validate datetime
        try:
            start = datetime.fromisoformat(schedule['start_time'])
            end = datetime.fromisoformat(schedule['end_time'])
            
            if end <= start:
                errors.append('End time must be after start time')
            
            # Check reasonable duration (< 8 hours)
            duration = (end - start).total_seconds() / 3600
            if duration > 8:
                warnings.append(f"Row {idx+1}: Long duration ({duration:.1f} hours)")
        except Exception as e:
            errors.append(f'Invalid datetime: {e}')
        
        if errors:
            invalid.append({
                'row': idx + 1,
                'data': schedule,
                'errors': errors
            })
        else:
            valid.append(schedule)
    
    return valid, invalid, warnings


def parse_csv_schedule(file_path):
    """
    Parse CSV file (alternative to Excel)
    """
    import csv
    
    try:
        schedules = []
        errors = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for idx, row in enumerate(reader, start=2):
                try:
                    schedule = {
                        'subject': row.get('subject', row.get('Môn học', '')),
                        'start_time': f"{row['date']} {row['start_time']}:00",
                        'end_time': f"{row['date']} {row['end_time']}:00",
                        'location': row.get('location', row.get('Phòng', '')),
                        'type': normalize_schedule_type(row.get('type', 'class')),
                        'description': row.get('description', ''),
                        'color': assign_color_by_subject(row['subject']),
                        'reminder_time': 30
                    }
                    schedules.append(schedule)
                except Exception as e:
                    errors.append(f"Row {idx}: {str(e)}")
        
        return {
            'schedules': schedules,
            'total': len(schedules),
            'errors': errors
        }
    
    except Exception as e:
        return {'error': f'Failed to parse CSV: {str(e)}'}


def get_file_extension(filename):
    """Lấy extension của file"""
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''


def allowed_file(filename, allowed_extensions):
    """Kiểm tra file có được phép không"""
    return '.' in filename and get_file_extension(filename) in allowed_extensions