"""
utils/conflict_detector.py - Phát hiện xung đột lịch học
"""

from models import get_db
from datetime import datetime


def detect_schedule_conflicts(user_id, start_time, end_time, exclude_id=None):
    """
    Kiểm tra xem có lịch nào trùng thời gian không
    
    Args:
        user_id: ID của user
        start_time: Thời gian bắt đầu (string ISO format)
        end_time: Thời gian kết thúc (string ISO format)
        exclude_id: ID của schedule cần bỏ qua khi check (dùng khi update)
    
    Returns:
        List các schedule bị conflict
    """
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Query tìm các lịch trùng
        # Trùng khi:
        # 1. Lịch mới bắt đầu trong khoảng lịch cũ
        # 2. Lịch mới kết thúc trong khoảng lịch cũ
        # 3. Lịch mới bao trùm lịch cũ
        
        if exclude_id:
            cursor.execute('''
                SELECT id, subject, start_time, end_time, location, type, color
                FROM schedule
                WHERE user_id = ?
                AND id != ?
                AND (
                    (start_time < ? AND end_time > ?) OR
                    (start_time < ? AND end_time > ?) OR
                    (start_time >= ? AND end_time <= ?)
                )
            ''', (user_id, exclude_id, 
                  end_time, start_time,
                  end_time, start_time,
                  start_time, end_time))
        else:
            cursor.execute('''
                SELECT id, subject, start_time, end_time, location, type, color
                FROM schedule
                WHERE user_id = ?
                AND (
                    (start_time < ? AND end_time > ?) OR
                    (start_time < ? AND end_time > ?) OR
                    (start_time >= ? AND end_time <= ?)
                )
            ''', (user_id, 
                  end_time, start_time,
                  end_time, start_time,
                  start_time, end_time))
        
        conflicts = cursor.fetchall()
    
    # Convert to list of dicts
    conflict_list = []
    for row in conflicts:
        conflict_list.append({
            'id': row['id'],
            'subject': row['subject'],
            'start_time': row['start_time'],
            'end_time': row['end_time'],
            'location': row['location'],
            'type': row['type'],
            'color': row['color']
        })
    
    return conflict_list


def get_conflict_details(conflict_schedules, new_start, new_end):
    """
    Phân tích chi tiết các xung đột và đưa ra gợi ý
    
    Args:
        conflict_schedules: List các schedule bị conflict
        new_start: Thời gian bắt đầu của lịch mới
        new_end: Thời gian kết thúc của lịch mới
    
    Returns:
        Dict chứa thông tin chi tiết và suggestions
    """
    if not conflict_schedules:
        return {
            'has_conflict': False,
            'message': 'No conflicts detected'
        }
    
    suggestions = []
    
    for conflict in conflict_schedules:
        overlap_type = determine_overlap_type(
            new_start, new_end,
            conflict['start_time'], conflict['end_time']
        )
        
        suggestion = generate_suggestion(conflict, overlap_type)
        suggestions.append(suggestion)
    
    return {
        'has_conflict': True,
        'count': len(conflict_schedules),
        'conflicts': conflict_schedules,
        'suggestions': suggestions
    }


def determine_overlap_type(new_start, new_end, existing_start, existing_end):
    """
    Xác định loại overlap giữa 2 khoảng thời gian
    
    Returns:
        - 'complete_overlap': Lịch mới trùng hoàn toàn
        - 'start_overlap': Đầu lịch mới trùng
        - 'end_overlap': Cuối lịch mới trùng
        - 'contained': Lịch mới nằm trong lịch cũ
        - 'contains': Lịch mới bao trùm lịch cũ
    """
    new_start_dt = datetime.fromisoformat(new_start)
    new_end_dt = datetime.fromisoformat(new_end)
    exist_start_dt = datetime.fromisoformat(existing_start)
    exist_end_dt = datetime.fromisoformat(existing_end)
    
    if new_start_dt == exist_start_dt and new_end_dt == exist_end_dt:
        return 'complete_overlap'
    elif new_start_dt >= exist_start_dt and new_end_dt <= exist_end_dt:
        return 'contained'
    elif new_start_dt <= exist_start_dt and new_end_dt >= exist_end_dt:
        return 'contains'
    elif new_start_dt < exist_end_dt and new_end_dt > exist_end_dt:
        return 'start_overlap'
    elif new_end_dt > exist_start_dt and new_start_dt < exist_start_dt:
        return 'end_overlap'
    
    return 'unknown'


def generate_suggestion(conflict, overlap_type):
    """
    Tạo gợi ý dựa trên loại conflict
    """
    suggestions_map = {
        'complete_overlap': f"Trùng hoàn toàn với '{conflict['subject']}'. Hãy chọn thời gian khác.",
        'contained': f"Nằm trong khoảng thời gian của '{conflict['subject']}'. Xem xét dời sang thời gian khác.",
        'contains': f"Bao trùm lịch '{conflict['subject']}'. Có thể rút ngắn hoặc chia nhỏ lịch.",
        'start_overlap': f"Đầu giờ trùng với '{conflict['subject']}'. Gợi ý: Bắt đầu sau {conflict['end_time']}.",
        'end_overlap': f"Cuối giờ trùng với '{conflict['subject']}'. Gợi ý: Kết thúc trước {conflict['start_time']}.",
    }
    
    return {
        'conflict_with': conflict['subject'],
        'overlap_type': overlap_type,
        'suggestion': suggestions_map.get(overlap_type, 'Có xung đột. Vui lòng kiểm tra lại thời gian.')
    }


def find_free_slots(user_id, date, duration_minutes=60):
    """
    Tìm các khoảng thời gian trống trong ngày
    
    Args:
        user_id: ID của user
        date: Ngày cần tìm (YYYY-MM-DD)
        duration_minutes: Độ dài tối thiểu của khoảng trống (mặc định 60 phút)
    
    Returns:
        List các khoảng thời gian trống
    """
    from datetime import timedelta
    
    # Giờ làm việc mặc định: 7:00 - 22:00
    start_of_day = datetime.fromisoformat(f"{date} 07:00:00")
    end_of_day = datetime.fromisoformat(f"{date} 22:00:00")
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT start_time, end_time
            FROM schedule
            WHERE user_id = ?
            AND date(start_time) = ?
            ORDER BY start_time ASC
        ''', (user_id, date))
        
        schedules = cursor.fetchall()
    
    free_slots = []
    current_time = start_of_day
    
    for schedule in schedules:
        schedule_start = datetime.fromisoformat(schedule['start_time'])
        schedule_end = datetime.fromisoformat(schedule['end_time'])
        
        # Nếu có khoảng trống trước schedule này
        if current_time < schedule_start:
            gap_minutes = (schedule_start - current_time).total_seconds() / 60
            
            if gap_minutes >= duration_minutes:
                free_slots.append({
                    'start': current_time.isoformat(),
                    'end': schedule_start.isoformat(),
                    'duration_minutes': int(gap_minutes)
                })
        
        # Di chuyển current_time đến sau schedule này
        if schedule_end > current_time:
            current_time = schedule_end
    
    # Kiểm tra khoảng trống cuối ngày
    if current_time < end_of_day:
        gap_minutes = (end_of_day - current_time).total_seconds() / 60
        
        if gap_minutes >= duration_minutes:
            free_slots.append({
                'start': current_time.isoformat(),
                'end': end_of_day.isoformat(),
                'duration_minutes': int(gap_minutes)
            })
    
    return free_slots


def get_busiest_days(user_id, start_date, end_date):
    """
    Tìm các ngày bận nhất trong khoảng thời gian
    
    Args:
        user_id: ID của user
        start_date: Ngày bắt đầu (YYYY-MM-DD)
        end_date: Ngày kết thúc (YYYY-MM-DD)
    
    Returns:
        List các ngày và tổng thời gian học
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                date(start_time) as day,
                COUNT(*) as event_count,
                SUM((julianday(end_time) - julianday(start_time)) * 24) as total_hours
            FROM schedule
            WHERE user_id = ?
            AND date(start_time) BETWEEN ? AND ?
            GROUP BY date(start_time)
            ORDER BY total_hours DESC
        ''', (user_id, start_date, end_date))
        
        busy_days = cursor.fetchall()
    
    result = []
    for row in busy_days:
        result.append({
            'date': row['day'],
            'event_count': row['event_count'],
            'total_hours': round(row['total_hours'], 2)
        })
    
    return result