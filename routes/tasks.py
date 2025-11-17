"""
routes/tasks.py - API endpoints cho quản lý nhiệm vụ (Tasks)
"""

from flask import Blueprint, request, jsonify
from models import get_db
from utils.auth import token_required
from datetime import datetime

tasks_bp = Blueprint('tasks', __name__)


@tasks_bp.route('', methods=['GET'])
@token_required
def get_tasks(current_user):
    """
    Lấy danh sách nhiệm vụ
    
    Query params:
        - status: pending/in_progress/completed (optional)
        - priority: high/medium/low (optional)
        - due_before: YYYY-MM-DD (optional - lấy tasks có deadline trước ngày này)
    """
    user_id = current_user['user_id']
    
    # Get query parameters
    status = request.args.get('status')
    priority = request.args.get('priority')
    due_before = request.args.get('due_before')
    
    # Build dynamic query
    query = 'SELECT * FROM tasks WHERE user_id = ?'
    params = [user_id]
    
    if status:
        query += ' AND status = ?'
        params.append(status)
    
    if priority:
        query += ' AND priority = ?'
        params.append(priority)
    
    if due_before:
        query += ' AND due_date <= ?'
        params.append(due_before)
    
    query += ' ORDER BY due_date ASC, priority DESC'
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        tasks = cursor.fetchall()
    
    # Convert to list of dicts
    task_list = []
    for row in tasks:
        task_list.append({
            'id': row['id'],
            'title': row['title'],
            'description': row['description'],
            'due_date': row['due_date'],
            'priority': row['priority'],
            'status': row['status'],
            'related_schedule_id': row['related_schedule_id'],
            'completed_at': row['completed_at'],
            'created_at': row['created_at']
        })
    
    return jsonify({
        'count': len(task_list),
        'tasks': task_list
    }), 200


@tasks_bp.route('', methods=['POST'])
@token_required
def create_task(current_user):
    """
    Tạo nhiệm vụ mới
    
    Request Body:
    {
        "title": "Nộp bài tập Toán",
        "description": "Bài tập chương 3",
        "due_date": "2025-10-25 23:59:00",
        "priority": "high",
        "status": "pending",
        "related_schedule_id": 1
    }
    """
    data = request.get_json()
    user_id = current_user['user_id']
    
    # Validate required fields
    if not data or 'title' not in data:
        return jsonify({'error': 'Missing required field: title'}), 400
    
    # Validate due_date if provided
    due_date = data.get('due_date')
    if due_date:
        try:
            datetime.fromisoformat(due_date)
        except ValueError:
            return jsonify({'error': 'Invalid due_date format. Use: YYYY-MM-DD HH:MM:SS'}), 400
    
    # Validate priority
    priority = data.get('priority', 'medium')
    if priority not in ['high', 'medium', 'low']:
        return jsonify({'error': 'Invalid priority. Must be: high, medium, or low'}), 400
    
    # Validate status
    status = data.get('status', 'pending')
    if status not in ['pending', 'in_progress', 'completed']:
        return jsonify({'error': 'Invalid status'}), 400
    
    # Extract fields
    title = data['title']
    description = data.get('description', '')
    related_schedule_id = data.get('related_schedule_id')
    
    # Validate related_schedule_id if provided
    if related_schedule_id:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id FROM schedule 
                WHERE id = ? AND user_id = ?
            ''', (related_schedule_id, user_id))
            
            if not cursor.fetchone():
                return jsonify({'error': 'Related schedule not found'}), 404
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO tasks 
            (user_id, title, description, due_date, priority, status, related_schedule_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, title, description, due_date, priority, status, related_schedule_id))
        
        task_id = cursor.lastrowid
    
    return jsonify({
        'message': 'Task created successfully',
        'task_id': task_id
    }), 201


@tasks_bp.route('/<int:task_id>', methods=['GET'])
@token_required
def get_task_detail(current_user, task_id):
    """Lấy chi tiết một nhiệm vụ"""
    user_id = current_user['user_id']
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT t.*, s.subject as related_subject
            FROM tasks t
            LEFT JOIN schedule s ON t.related_schedule_id = s.id
            WHERE t.id = ? AND t.user_id = ?
        ''', (task_id, user_id))
        
        task = cursor.fetchone()
    
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    
    return jsonify({
        'task': {
            'id': task['id'],
            'title': task['title'],
            'description': task['description'],
            'due_date': task['due_date'],
            'priority': task['priority'],
            'status': task['status'],
            'related_schedule_id': task['related_schedule_id'],
            'related_subject': task['related_subject'],
            'completed_at': task['completed_at'],
            'created_at': task['created_at']
        }
    }), 200


@tasks_bp.route('/<int:task_id>', methods=['PUT'])
@token_required
def update_task(current_user, task_id):
    """
    Cập nhật nhiệm vụ
    
    Request Body: (các field optional)
    {
        "title": "New Title",
        "status": "completed",
        "priority": "low"
    }
    """
    user_id = current_user['user_id']
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if task exists
        cursor.execute('''
            SELECT * FROM tasks 
            WHERE id = ? AND user_id = ?
        ''', (task_id, user_id))
        
        existing = cursor.fetchone()
        
        if not existing:
            return jsonify({'error': 'Task not found'}), 404
        
        # Validate fields
        if 'priority' in data and data['priority'] not in ['high', 'medium', 'low']:
            return jsonify({'error': 'Invalid priority'}), 400
        
        if 'status' in data and data['status'] not in ['pending', 'in_progress', 'completed']:
            return jsonify({'error': 'Invalid status'}), 400
        
        if 'due_date' in data and data['due_date']:
            try:
                datetime.fromisoformat(data['due_date'])
            except ValueError:
                return jsonify({'error': 'Invalid due_date format'}), 400
        
        # Build update query
        allowed_fields = ['title', 'description', 'due_date', 'priority', 'status', 'related_schedule_id']
        updates = {k: v for k, v in data.items() if k in allowed_fields}
        
        if not updates:
            return jsonify({'error': 'No valid fields to update'}), 400
        
        # If status changed to completed, set completed_at
        if 'status' in updates and updates['status'] == 'completed':
            updates['completed_at'] = datetime.now().isoformat()
        elif 'status' in updates and updates['status'] != 'completed':
            updates['completed_at'] = None
        
        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [task_id, user_id]
        
        cursor.execute(f'''
            UPDATE tasks
            SET {set_clause}
            WHERE id = ? AND user_id = ?
        ''', values)
    
    return jsonify({
        'message': 'Task updated successfully'
    }), 200


@tasks_bp.route('/<int:task_id>', methods=['DELETE'])
@token_required
def delete_task(current_user, task_id):
    """Xóa nhiệm vụ"""
    user_id = current_user['user_id']
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if exists
        cursor.execute('''
            SELECT id FROM tasks 
            WHERE id = ? AND user_id = ?
        ''', (task_id, user_id))
        
        if not cursor.fetchone():
            return jsonify({'error': 'Task not found'}), 404
        
        # Delete
        cursor.execute('''
            DELETE FROM tasks 
            WHERE id = ? AND user_id = ?
        ''', (task_id, user_id))
    
    return jsonify({
        'message': 'Task deleted successfully'
    }), 200


@tasks_bp.route('/<int:task_id>/complete', methods=['PUT'])
@token_required
def mark_task_complete(current_user, task_id):
    """
    Shortcut để đánh dấu task hoàn thành
    """
    user_id = current_user['user_id']
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE tasks
            SET status = 'completed',
                completed_at = ?
            WHERE id = ? AND user_id = ?
        ''', (datetime.now().isoformat(), task_id, user_id))
        
        if cursor.rowcount == 0:
            return jsonify({'error': 'Task not found'}), 404
    
    return jsonify({
        'message': 'Task marked as completed'
    }), 200


@tasks_bp.route('/overdue', methods=['GET'])
@token_required
def get_overdue_tasks(current_user):
    """
    Lấy các task quá hạn (due_date < now và status != completed)
    """
    user_id = current_user['user_id']
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM tasks
            WHERE user_id = ?
            AND status != 'completed'
            AND due_date < datetime('now')
            ORDER BY due_date ASC
        ''', (user_id,))
        
        tasks = cursor.fetchall()
    
    task_list = []
    for row in tasks:
        task_list.append({
            'id': row['id'],
            'title': row['title'],
            'due_date': row['due_date'],
            'priority': row['priority'],
            'status': row['status']
        })
    
    return jsonify({
        'count': len(task_list),
        'overdue_tasks': task_list
    }), 200


@tasks_bp.route('/stats', methods=['GET'])
@token_required
def get_task_stats(current_user):
    """
    Thống kê nhiệm vụ
    """
    user_id = current_user['user_id']
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Total tasks
        cursor.execute('SELECT COUNT(*) as total FROM tasks WHERE user_id = ?', (user_id,))
        total = cursor.fetchone()['total']
        
        # Completed tasks
        cursor.execute('''
            SELECT COUNT(*) as completed 
            FROM tasks 
            WHERE user_id = ? AND status = 'completed'
        ''', (user_id,))
        completed = cursor.fetchone()['completed']
        
        # Pending tasks
        cursor.execute('''
            SELECT COUNT(*) as pending 
            FROM tasks 
            WHERE user_id = ? AND status = 'pending'
        ''', (user_id,))
        pending = cursor.fetchone()['pending']
        
        # Overdue tasks
        cursor.execute('''
            SELECT COUNT(*) as overdue 
            FROM tasks 
            WHERE user_id = ? 
            AND status != 'completed'
            AND due_date < datetime('now')
        ''', (user_id,))
        overdue = cursor.fetchone()['overdue']
        
        # High priority tasks
        cursor.execute('''
            SELECT COUNT(*) as high_priority 
            FROM tasks 
            WHERE user_id = ? 
            AND priority = 'high'
            AND status != 'completed'
        ''', (user_id,))
        high_priority = cursor.fetchone()['high_priority']
    
    completion_rate = (completed / total * 100) if total > 0 else 0
    
    return jsonify({
        'stats': {
            'total': total,
            'completed': completed,
            'pending': pending,
            'overdue': overdue,
            'high_priority': high_priority,
            'completion_rate': round(completion_rate, 2)
        }
    }), 200