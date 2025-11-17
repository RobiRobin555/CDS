"""
routes/schedule.py - API endpoints cho quản lý lịch học
"""

from flask import Blueprint, request, jsonify
from models import get_db
from utils.auth import token_required
from utils.conflict_detector import detect_schedule_conflicts
from datetime import datetime
import json
from utils.validators import (
    validate_schedule_payload_basic,
    validate_schedule_type,
    validate_date_str,
    validate_datetime_str,
)

schedule_bp = Blueprint('schedule', __name__)


@schedule_bp.route('', methods=['GET'])
@token_required
def get_schedules(current_user):
    """
    Lấy danh sách lịch học của user
    
    Query params:
        - start_date: YYYY-MM-DD (optional)
        - end_date: YYYY-MM-DD (optional)
        - type: class/exam/meeting/other (optional)
    """
    user_id = current_user['user_id']
    
    # Lấy query parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    schedule_type = request.args.get('type')
    # Validate filters
    ok, msg = validate_schedule_type(schedule_type) if schedule_type else (True, "OK")
    if not ok:
        return jsonify({'error': msg}), 400
    if start_date:
        ok, msg = validate_date_str(start_date)
        if not ok:
            return jsonify({'error': msg}), 400
    if end_date:
        ok, msg = validate_date_str(end_date)
        if not ok:
            return jsonify({'error': msg}), 400
    
    # Build dynamic query
    query = 'SELECT * FROM schedule WHERE user_id = ?'
    params = [user_id]
    
    if start_date:
        query += ' AND start_time >= ?'
        params.append(start_date)
    
    if end_date:
        query += ' AND start_time <= ?'
        params.append(end_date)
    
    if schedule_type:
        query += ' AND type = ?'
        params.append(schedule_type)
    
    query += ' ORDER BY start_time ASC'
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        schedules = cursor.fetchall()
    
    # Convert to list of dicts
    schedule_list = []
    for row in schedules:
        schedule_list.append({
            'id': row['id'],
            'subject': row['subject'],
            'description': row['description'],
            'start_time': row['start_time'],
            'end_time': row['end_time'],
            'location': row['location'],
            'type': row['type'],
            'recurring': row['recurring'],
            'color': row['color'],
            'reminder_time': row['reminder_time'],
            'created_at': row['created_at']
        })
    
    return jsonify({
        'count': len(schedule_list),
        'schedules': schedule_list
    }), 200


@schedule_bp.route('', methods=['POST'])
@token_required
def create_schedule(current_user):
    """
    Tạo lịch học mới
    
    Request Body:
    {
        "subject": "Toán Cao Cấp",
        "description": "Chương 3: Tích phân",
        "start_time": "2025-10-20 08:00:00",
        "end_time": "2025-10-20 10:00:00",
        "location": "Phòng A101",
        "type": "class",
        "recurring": null,
        "color": "#FF5733",
        "reminder_time": 30
    }
    """
    data = request.get_json()
    user_id = current_user['user_id']
    
    # Validate required fields
    required_fields = ['subject', 'start_time', 'end_time']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Parse and validate datetime
    ok, msg = validate_datetime_str(data['start_time'])
    if not ok:
        return jsonify({'error': msg}), 400
    ok, msg = validate_datetime_str(data['end_time'])
    if not ok:
        return jsonify({'error': msg}), 400
    start_time = datetime.fromisoformat(data['start_time'])
    end_time = datetime.fromisoformat(data['end_time'])
    if end_time <= start_time:
        return jsonify({'error': 'end_time must be after start_time'}), 400
    
    # Check for conflicts (không chặn tạo lịch)
    conflicts = detect_schedule_conflicts(
        user_id,
        data['start_time'],
        data['end_time']
    )
    conflicts_detected = len(conflicts) > 0
    
    # Extract fields
    subject = data['subject']
    description = data.get('description', '')
    location = data.get('location', '')
    schedule_type = data.get('type', 'class')
    recurring = data.get('recurring')
    color = data.get('color', '#3788d8')
    reminder_time = data.get('reminder_time', 30)
    
    # Validate business fields
    ok, msg = validate_schedule_payload_basic({
        'subject': subject,
        'type': schedule_type,
        'reminder_time': reminder_time,
        'color': color,
        'location': location,
        'description': description,
    })
    if not ok:
        return jsonify({'error': msg}), 400

    # Validate recurring format if provided
    if recurring:
        try:
            recurring_data = json.loads(recurring) if isinstance(recurring, str) else recurring
            if not isinstance(recurring_data, dict):
                return jsonify({'error': 'Invalid recurring format'}), 400
        except json.JSONDecodeError:
            return jsonify({'error': 'Invalid recurring JSON'}), 400
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO schedule 
            (user_id, subject, description, start_time, end_time, location, 
             type, recurring, color, reminder_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, subject, description, data['start_time'], data['end_time'],
              location, schedule_type, json.dumps(recurring) if recurring else None, 
              color, reminder_time))
        
        schedule_id = cursor.lastrowid
    
    return jsonify({
        'message': 'Schedule created successfully',
        'schedule_id': schedule_id,
        'conflicts_detected': conflicts_detected,
        'conflicts': conflicts if conflicts_detected else []
    }), 201


@schedule_bp.route('/<int:schedule_id>', methods=['GET'])
@token_required
def get_schedule_detail(current_user, schedule_id):
    """Lấy chi tiết một lịch học"""
    user_id = current_user['user_id']
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM schedule 
            WHERE id = ? AND user_id = ?
        ''', (schedule_id, user_id))
        
        schedule = cursor.fetchone()
    
    if not schedule:
        return jsonify({'error': 'Schedule not found'}), 404
    
    return jsonify({
        'schedule': {
            'id': schedule['id'],
            'subject': schedule['subject'],
            'description': schedule['description'],
            'start_time': schedule['start_time'],
            'end_time': schedule['end_time'],
            'location': schedule['location'],
            'type': schedule['type'],
            'recurring': schedule['recurring'],
            'color': schedule['color'],
            'reminder_time': schedule['reminder_time'],
            'created_at': schedule['created_at']
        }
    }), 200


@schedule_bp.route('/<int:schedule_id>', methods=['PUT'])
@token_required
def update_schedule(current_user, schedule_id):
    """
    Cập nhật lịch học
    
    Request Body: (các field optional)
    {
        "subject": "New Subject",
        "start_time": "2025-10-21 09:00:00",
        ...
    }
    """
    user_id = current_user['user_id']
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Kiểm tra schedule có tồn tại và thuộc về user không
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM schedule 
            WHERE id = ? AND user_id = ?
        ''', (schedule_id, user_id))
        
        existing = cursor.fetchone()
        
        if not existing:
            return jsonify({'error': 'Schedule not found'}), 404
        
        # Nếu cập nhật thời gian, kiểm tra định dạng và xung đột (không chặn cập nhật)
        conflicts = []
        conflicts_detected = False
        if 'start_time' in data or 'end_time' in data:
            new_start = data.get('start_time', existing['start_time'])
            new_end = data.get('end_time', existing['end_time'])

            # Validate datetime
            ok, msg = validate_datetime_str(new_start)
            if not ok:
                return jsonify({'error': msg}), 400
            ok, msg = validate_datetime_str(new_end)
            if not ok:
                return jsonify({'error': msg}), 400
            start_dt = datetime.fromisoformat(new_start)
            end_dt = datetime.fromisoformat(new_end)
            if end_dt <= start_dt:
                return jsonify({'error': 'end_time must be after start_time'}), 400

            # Check conflict (exclude current schedule) - chỉ cảnh báo
            conflicts = detect_schedule_conflicts(
                user_id, new_start, new_end, exclude_id=schedule_id
            )
            conflicts_detected = len(conflicts) > 0
        
        # Build update query
        allowed_fields = ['subject', 'description', 'start_time', 'end_time', 
                         'location', 'type', 'recurring', 'color', 'reminder_time']
        updates = {k: v for k, v in data.items() if k in allowed_fields}
        
        if not updates:
            return jsonify({'error': 'No valid fields to update'}), 400

        # Validate basic fields if present
        basic_payload = {
            'subject': updates.get('subject', existing['subject']),
            'type': updates.get('type', existing['type']),
            'reminder_time': updates.get('reminder_time', existing['reminder_time']),
            'color': updates.get('color', existing['color']),
            'location': updates.get('location', existing['location']),
            'description': updates.get('description', existing['description']),
        }
        ok, msg = validate_schedule_payload_basic(basic_payload)
        if not ok:
            return jsonify({'error': msg}), 400
        
        # Handle recurring field (JSON)
        if 'recurring' in updates and updates['recurring']:
            updates['recurring'] = json.dumps(updates['recurring'])
        
        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [schedule_id, user_id]
        
        cursor.execute(f'''
            UPDATE schedule
            SET {set_clause}
            WHERE id = ? AND user_id = ?
        ''', values)
    
    return jsonify({
        'message': 'Schedule updated successfully',
        'conflicts_detected': conflicts_detected,
        'conflicts': conflicts if conflicts_detected else []
    }), 200


@schedule_bp.route('/<int:schedule_id>', methods=['DELETE'])
@token_required
def delete_schedule(current_user, schedule_id):
    """Xóa lịch học"""
    user_id = current_user['user_id']
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if exists
        cursor.execute('''
            SELECT id FROM schedule 
            WHERE id = ? AND user_id = ?
        ''', (schedule_id, user_id))
        
        if not cursor.fetchone():
            return jsonify({'error': 'Schedule not found'}), 404
        
        # Delete
        cursor.execute('''
            DELETE FROM schedule 
            WHERE id = ? AND user_id = ?
        ''', (schedule_id, user_id))
    
    return jsonify({
        'message': 'Schedule deleted successfully'
    }), 200


@schedule_bp.route('/conflicts', methods=['GET'])
@token_required
def check_conflicts(current_user):
    """
    Kiểm tra xung đột lịch học
    
    Query params:
        - start_time: YYYY-MM-DD HH:MM:SS
        - end_time: YYYY-MM-DD HH:MM:SS
        - exclude_id: int (optional - bỏ qua schedule này khi check)
    """
    user_id = current_user['user_id']
    
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')
    exclude_id = request.args.get('exclude_id', type=int)
    
    if not start_time or not end_time:
        return jsonify({'error': 'Missing start_time or end_time'}), 400
    
    conflicts = detect_schedule_conflicts(
        user_id, start_time, end_time, exclude_id
    )
    
    return jsonify({
        'has_conflicts': len(conflicts) > 0,
        'count': len(conflicts),
        'conflicts': conflicts
    }), 200


@schedule_bp.route('/upcoming', methods=['GET'])
@token_required
def get_upcoming_schedules(current_user):
    """
    Lấy các lịch sắp diễn ra (trong 7 ngày tới)
    """
    user_id = current_user['user_id']
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM schedule
            WHERE user_id = ?
            AND start_time >= datetime('now')
            AND start_time <= datetime('now', '+7 days')
            ORDER BY start_time ASC
            LIMIT 20
        ''', (user_id,))
        
        schedules = cursor.fetchall()
    
    schedule_list = []
    for row in schedules:
        schedule_list.append({
            'id': row['id'],
            'subject': row['subject'],
            'start_time': row['start_time'],
            'end_time': row['end_time'],
            'location': row['location'],
            'type': row['type'],
            'color': row['color']
        })
    
    return jsonify({
        'count': len(schedule_list),
        'schedules': schedule_list
    }), 200
