"""
routes/stats.py - API endpoints cho thống kê và phân tích
"""

from flask import Blueprint, request, jsonify
from models import get_db
from utils.auth import token_required
from datetime import datetime, timedelta
import json

stats_bp = Blueprint('stats', __name__)


@stats_bp.route('/overview', methods=['GET'])
@token_required
def get_overview(current_user):
    """
    Tổng quan thống kê tổng thể
    """
    user_id = current_user['user_id']
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Total schedules
        cursor.execute('''
            SELECT COUNT(*) as total FROM schedule
            WHERE user_id = ?
        ''', (user_id,))
        total_schedules = cursor.fetchone()['total']
        
        # Upcoming schedules (next 7 days)
        cursor.execute('''
            SELECT COUNT(*) as count FROM schedule
            WHERE user_id = ?
            AND start_time >= datetime('now')
            AND start_time <= datetime('now', '+7 days')
        ''', (user_id,))
        upcoming = cursor.fetchone()['count']
        
        # Total tasks
        cursor.execute('''
            SELECT COUNT(*) as total FROM tasks
            WHERE user_id = ?
        ''', (user_id,))
        total_tasks = cursor.fetchone()['total']
        
        # Pending tasks
        cursor.execute('''
            SELECT COUNT(*) as count FROM tasks
            WHERE user_id = ? AND status != 'completed'
        ''', (user_id,))
        pending_tasks = cursor.fetchone()['count']
        
        # Overdue tasks
        cursor.execute('''
            SELECT COUNT(*) as count FROM tasks
            WHERE user_id = ?
            AND status != 'completed'
            AND due_date < datetime('now')
        ''', (user_id,))
        overdue_tasks = cursor.fetchone()['count']
        
        # Completion rate
        cursor.execute('''
            SELECT 
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                COUNT(*) as total
            FROM tasks
            WHERE user_id = ?
        ''', (user_id,))
        task_stats = cursor.fetchone()
        completion_rate = (task_stats['completed'] / task_stats['total'] * 100) if task_stats['total'] > 0 else 0
    
    return jsonify({
        'overview': {
            'total_schedules': total_schedules,
            'upcoming_schedules': upcoming,
            'total_tasks': total_tasks,
            'pending_tasks': pending_tasks,
            'overdue_tasks': overdue_tasks,
            'completion_rate': round(completion_rate, 2)
        }
    }), 200


@stats_bp.route('/weekly', methods=['GET'])
@token_required
def get_weekly_stats(current_user):
    """
    Thống kê tuần này
    
    Query params:
        - week_offset: 0 (tuần này), -1 (tuần trước), 1 (tuần sau)
    """
    user_id = current_user['user_id']
    week_offset = request.args.get('week_offset', 0, type=int)
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Calculate week start/end
        offset_days = week_offset * 7
        
        # Total events this week
        cursor.execute('''
            SELECT 
                COUNT(*) as event_count,
                SUM((julianday(end_time) - julianday(start_time)) * 24) as total_hours
            FROM schedule
            WHERE user_id = ?
            AND date(start_time) >= date('now', 'weekday 0', ?)
            AND date(start_time) < date('now', 'weekday 0', ?)
        ''', (user_id, f'{offset_days - 7} days', f'{offset_days} days'))
        
        week_data = cursor.fetchone()
        
        # Events by day
        cursor.execute('''
            SELECT 
                CASE CAST(strftime('%w', start_time) AS INTEGER)
                    WHEN 0 THEN 'Sunday'
                    WHEN 1 THEN 'Monday'
                    WHEN 2 THEN 'Tuesday'
                    WHEN 3 THEN 'Wednesday'
                    WHEN 4 THEN 'Thursday'
                    WHEN 5 THEN 'Friday'
                    WHEN 6 THEN 'Saturday'
                END as day_name,
                COUNT(*) as count,
                SUM((julianday(end_time) - julianday(start_time)) * 24) as hours
            FROM schedule
            WHERE user_id = ?
            AND date(start_time) >= date('now', 'weekday 0', ?)
            AND date(start_time) < date('now', 'weekday 0', ?)
            GROUP BY strftime('%w', start_time)
            ORDER BY strftime('%w', start_time)
        ''', (user_id, f'{offset_days - 7} days', f'{offset_days} days'))
        
        by_day = cursor.fetchall()
    
    daily_stats = {row['day_name']: {
        'count': row['count'],
        'hours': round(row['hours'] or 0, 2)
    } for row in by_day}
    
    return jsonify({
        'week_stats': {
            'total_events': week_data['event_count'] or 0,
            'total_hours': round(week_data['total_hours'] or 0, 2),
            'average_hours_per_day': round((week_data['total_hours'] or 0) / 7, 2),
            'by_day': daily_stats
        }
    }), 200


@stats_bp.route('/monthly', methods=['GET'])
@token_required
def get_monthly_stats(current_user):
    """
    Thống kê tháng này
    
    Query params:
        - month_offset: 0 (tháng này), -1 (tháng trước)
    """
    user_id = current_user['user_id']
    month_offset = request.args.get('month_offset', 0, type=int)
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Total events this month
        cursor.execute('''
            SELECT 
                COUNT(*) as event_count,
                SUM((julianday(end_time) - julianday(start_time)) * 24) as total_hours
            FROM schedule
            WHERE user_id = ?
            AND date(start_time) >= date('now', 'start of month', ?)
            AND date(start_time) < date('now', 'start of month', ?)
        ''', (user_id, f'{month_offset} months', f'{month_offset + 1} months'))
        
        month_data = cursor.fetchone()
        
        # Events by week
        cursor.execute('''
            SELECT 
                strftime('%W', start_time) as week_number,
                COUNT(*) as count,
                SUM((julianday(end_time) - julianday(start_time)) * 24) as hours
            FROM schedule
            WHERE user_id = ?
            AND date(start_time) >= date('now', 'start of month', ?)
            AND date(start_time) < date('now', 'start of month', ?)
            GROUP BY strftime('%W', start_time)
            ORDER BY week_number
        ''', (user_id, f'{month_offset} months', f'{month_offset + 1} months'))
        
        by_week = cursor.fetchall()
    
    weekly_stats = [{
        'week': int(row['week_number']),
        'count': row['count'],
        'hours': round(row['hours'] or 0, 2)
    } for row in by_week]
    
    return jsonify({
        'month_stats': {
            'total_events': month_data['event_count'] or 0,
            'total_hours': round(month_data['total_hours'] or 0, 2),
            'by_week': weekly_stats
        }
    }), 200


@stats_bp.route('/subjects', methods=['GET'])
@token_required
def get_subject_stats(current_user):
    """
    Thống kê theo môn học
    """
    user_id = current_user['user_id']
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Total hours by subject
        cursor.execute('''
            SELECT 
                subject,
                COUNT(*) as class_count,
                SUM((julianday(end_time) - julianday(start_time)) * 24) as total_hours,
                AVG((julianday(end_time) - julianday(start_time)) * 24) as avg_hours,
                MIN(start_time) as first_class,
                MAX(start_time) as last_class
            FROM schedule
            WHERE user_id = ?
            GROUP BY subject
            ORDER BY total_hours DESC
        ''', (user_id,))
        
        subjects = cursor.fetchall()
    
    subject_stats = []
    for row in subjects:
        subject_stats.append({
            'subject': row['subject'],
            'class_count': row['class_count'],
            'total_hours': round(row['total_hours'] or 0, 2),
            'average_hours': round(row['avg_hours'] or 0, 2),
            'first_class': row['first_class'],
            'last_class': row['last_class']
        })
    
    return jsonify({
        'subject_stats': subject_stats,
        'total_subjects': len(subject_stats)
    }), 200


@stats_bp.route('/productivity', methods=['GET'])
@token_required
def get_productivity_stats(current_user):
    """
    Thống kê năng suất (tasks)
    
    Query params:
        - period: week, month, all (default: week)
    """
    user_id = current_user['user_id']
    period = request.args.get('period', 'week')
    
    # Determine date filter
    if period == 'week':
        date_filter = "AND date(created_at) >= date('now', '-7 days')"
    elif period == 'month':
        date_filter = "AND date(created_at) >= date('now', '-30 days')"
    else:
        date_filter = ""
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Task completion stats
        cursor.execute(f'''
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
                COUNT(CASE WHEN status = 'in_progress' THEN 1 END) as in_progress,
                COUNT(CASE WHEN priority = 'high' THEN 1 END) as high_priority,
                COUNT(CASE WHEN due_date < datetime('now') AND status != 'completed' THEN 1 END) as overdue
            FROM tasks
            WHERE user_id = ?
            {date_filter}
        ''', (user_id,))
        
        task_data = cursor.fetchone()
        
        # Average completion time
        cursor.execute(f'''
            SELECT 
                AVG(julianday(completed_at) - julianday(created_at)) as avg_days
            FROM tasks
            WHERE user_id = ?
            AND status = 'completed'
            AND completed_at IS NOT NULL
            {date_filter}
        ''', (user_id,))
        
        avg_completion = cursor.fetchone()['avg_days']
        
        # Tasks by priority
        cursor.execute(f'''
            SELECT 
                priority,
                COUNT(*) as count,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed
            FROM tasks
            WHERE user_id = ?
            {date_filter}
            GROUP BY priority
        ''', (user_id,))
        
        by_priority = cursor.fetchall()
    
    priority_stats = {row['priority']: {
        'total': row['count'],
        'completed': row['completed'],
        'completion_rate': round(row['completed'] / row['count'] * 100, 2) if row['count'] > 0 else 0
    } for row in by_priority}
    
    completion_rate = (task_data['completed'] / task_data['total'] * 100) if task_data['total'] > 0 else 0
    
    return jsonify({
        'productivity': {
            'total_tasks': task_data['total'],
            'completed': task_data['completed'],
            'pending': task_data['pending'],
            'in_progress': task_data['in_progress'],
            'high_priority': task_data['high_priority'],
            'overdue': task_data['overdue'],
            'completion_rate': round(completion_rate, 2),
            'average_completion_days': round(avg_completion or 0, 2),
            'by_priority': priority_stats
        }
    }), 200


@stats_bp.route('/busiest-days', methods=['GET'])
@token_required
def get_busiest_days(current_user):
    """
    Tìm các ngày bận nhất
    
    Query params:
        - limit: số lượng (default: 10)
        - start_date: YYYY-MM-DD (optional)
        - end_date: YYYY-MM-DD (optional)
    """
    user_id = current_user['user_id']
    limit = request.args.get('limit', 10, type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = '''
        SELECT 
            date(start_time) as day,
            COUNT(*) as event_count,
            SUM((julianday(end_time) - julianday(start_time)) * 24) as total_hours
        FROM schedule
        WHERE user_id = ?
    '''
    
    params = [user_id]
    
    if start_date:
        query += ' AND date(start_time) >= ?'
        params.append(start_date)
    
    if end_date:
        query += ' AND date(start_time) <= ?'
        params.append(end_date)
    
    query += '''
        GROUP BY date(start_time)
        ORDER BY total_hours DESC
        LIMIT ?
    '''
    params.append(limit)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        busy_days = cursor.fetchall()
    
    result = []
    for row in busy_days:
        result.append({
            'date': row['day'],
            'event_count': row['event_count'],
            'total_hours': round(row['total_hours'] or 0, 2)
        })
    
    return jsonify({
        'busiest_days': result
    }), 200


@stats_bp.route('/time-distribution', methods=['GET'])
@token_required
def get_time_distribution(current_user):
    """
    Phân bố thời gian học theo giờ trong ngày
    """
    user_id = current_user['user_id']
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                CAST(strftime('%H', start_time) AS INTEGER) as hour,
                COUNT(*) as count
            FROM schedule
            WHERE user_id = ?
            GROUP BY hour
            ORDER BY hour
        ''', (user_id,))
        
        distribution = cursor.fetchall()
    
    # Create full 24-hour distribution
    hourly_stats = {i: 0 for i in range(24)}
    for row in distribution:
        hourly_stats[row['hour']] = row['count']
    
    return jsonify({
        'time_distribution': hourly_stats,
        'peak_hours': sorted(
            [{'hour': h, 'count': c} for h, c in hourly_stats.items()],
            key=lambda x: x['count'],
            reverse=True
        )[:5]
    }), 200


@stats_bp.route('/export', methods=['GET'])
@token_required
def export_stats(current_user):
    """
    Export tất cả thống kê dạng JSON
    """
    user_id = current_user['user_id']
    
    # Gather all stats manually
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Overview
        cursor.execute('''
            SELECT COUNT(*) as total FROM schedule WHERE user_id = ?
        ''', (user_id,))
        total_schedules = cursor.fetchone()['total']
        
        cursor.execute('''
            SELECT COUNT(*) as total FROM tasks WHERE user_id = ?
        ''', (user_id,))
        total_tasks = cursor.fetchone()['total']
    
    export_data = {
        'generated_at': datetime.now().isoformat(),
        'user_id': user_id,
        'summary': {
            'total_schedules': total_schedules,
            'total_tasks': total_tasks
        },
        'note': 'Use individual endpoints for detailed stats'
    }
    
    return jsonify(export_data), 200