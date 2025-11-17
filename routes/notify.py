"""
routes/notify.py - API endpoints cho Notification Settings
"""

from flask import Blueprint, request, jsonify
from models import get_db
from utils.auth import token_required, validate_email
from services.notification_service import send_manual_notification, send_test_email_notification, send_test_telegram_notification, TELEGRAM_BOT_TOKEN
import requests
from utils.validators import validate_channels, validate_telegram_id

notify_bp = Blueprint('notify', __name__)


@notify_bp.route('/settings', methods=['GET'])
@token_required
def get_notification_settings(current_user):
    """
    Lấy cấu hình thông báo của user
    """
    user_id = current_user['user_id']
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM notification_settings
            WHERE user_id = ?
        ''', (user_id,))
        
        settings = cursor.fetchone()
    
    if not settings:
        # Tạo settings mặc định nếu chưa có
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO notification_settings (user_id)
                VALUES (?)
            ''', (user_id,))
        
        settings = {
            'email_enabled': True,
            'telegram_enabled': False,
            'in_app_enabled': True,
            'email_reminder_offset': 30,
            'telegram_reminder_offset': 30
        }
    else:
        settings = dict(settings)
    
    return jsonify({
        'settings': {
            'email_enabled': bool(settings['email_enabled']),
            'telegram_enabled': bool(settings['telegram_enabled']),
            'in_app_enabled': bool(settings['in_app_enabled']),
            'email_reminder_offset': settings.get('email_reminder_offset', 30),
            'telegram_reminder_offset': settings.get('telegram_reminder_offset', 30)
        }
    }), 200


@notify_bp.route('/settings', methods=['PUT'])
@token_required
def update_notification_settings(current_user):
    """
    Cập nhật cấu hình thông báo
    
    Request Body:
    {
        "email_enabled": true,
        "telegram_enabled": false,
        "in_app_enabled": true,
        "email_reminder_offset": 30,
        "telegram_reminder_offset": 30
    }
    """
    user_id = current_user['user_id']
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Validate fields
    allowed_fields = ['email_enabled', 'telegram_enabled', 'in_app_enabled', 'email_reminder_offset', 'telegram_reminder_offset']
    updates = {k: v for k, v in data.items() if k in allowed_fields}
    
    if not updates:
        return jsonify({'error': 'No valid fields to update'}), 400
    
    # Validate reminder_time offsets
    for field in ['email_reminder_offset', 'telegram_reminder_offset']:
        if field in updates:
            reminder_time = updates[field]
            if not isinstance(reminder_time, int) or reminder_time < 0 or reminder_time > 10080:
                return jsonify({'error': f'{field} must be between 0-10080 minutes'}), 400
    
    # Build dynamic UPDATE query
    set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
    values = list(updates.values()) + [user_id]
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if settings exist
        cursor.execute('SELECT user_id FROM notification_settings WHERE user_id = ?', (user_id,))
        
        if cursor.fetchone():
            # Update existing
            cursor.execute(f'''
                UPDATE notification_settings
                SET {set_clause}
                WHERE user_id = ?
            ''', values)
        else:
            # Insert new (shouldn't happen if auth works correctly)
            # Note: This part might need adjustment if default values are critical
            default_values = {
                'email_enabled': 1,
                'telegram_enabled': 0,
                'in_app_enabled': 1,
                'email_reminder_offset': 30,
                'telegram_reminder_offset': 30
            }
            final_values = {**default_values, **updates}

            cursor.execute('''
                INSERT INTO notification_settings 
                (user_id, email_enabled, telegram_enabled, in_app_enabled, email_reminder_offset, telegram_reminder_offset)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id,
                  final_values['email_enabled'],
                  final_values['telegram_enabled'],
                  final_values['in_app_enabled'],
                  final_values['email_reminder_offset'],
                  final_values['telegram_reminder_offset']))
    
    return jsonify({
        'message': 'Notification settings updated successfully',
        'updated_fields': list(updates.keys())
    }), 200


@notify_bp.route('/history', methods=['GET'])
@token_required
def get_notification_history(current_user):
    """
    Lấy lịch sử thông báo đã gửi
    
    Query params:
        - limit: số lượng (default: 50)
    """
    user_id = current_user['user_id']
    limit = request.args.get('limit', 50, type=int)
    try:
        limit = int(limit)
    except Exception:
        return jsonify({'error': 'limit must be an integer'}), 400
    if limit < 1 or limit > 200:
        return jsonify({'error': 'limit must be between 1 and 200'}), 400
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT n.*, s.subject
            FROM notifications n
            LEFT JOIN schedule s ON n.schedule_id = s.id
            WHERE n.user_id = ?
            ORDER BY n.created_at DESC
            LIMIT ?
        ''', (user_id, limit))
        
        notifications = cursor.fetchall()
    
    notification_list = []
    for row in notifications:
        notification_list.append({
            'id': row['id'],
            'schedule_id': row['schedule_id'],
            'subject': row['subject'],
            'message': row['message'],
            'send_time': row['send_time'],
            'sent': bool(row['sent']),
            'channel': row['channel'],
            'created_at': row['created_at']
        })
    
    return jsonify({
        'count': len(notification_list),
        'notifications': notification_list
    }), 200


@notify_bp.route('/test', methods=['POST'])
@token_required
def test_notification(current_user):
    """
    Gửi thông báo test để kiểm tra cấu hình
    
    Request Body:
    {
        "channels": ["email", "telegram", "in-app"]
    }
    """
    user_id = current_user['user_id']
    data = request.get_json()
    channels_raw = (data or {}).get('channels', ['email'])
    ok, channels_or_msg = validate_channels(channels_raw)
    if not ok:
        return jsonify({'error': channels_or_msg}), 400
    channels = channels_or_msg
    
    test_message = """🔔 Thông báo test từ SmartSchedule.AI

Đây là tin nhắn test để kiểm tra hệ thống thông báo.

Nếu bạn nhận được tin nhắn này, nghĩa là cấu hình thông báo đã hoạt động!

✅ SmartSchedule.AI
    """
    
    success_channels = send_manual_notification(user_id, test_message, channels)
    
    if success_channels:
        return jsonify({
            'message': 'Test notification sent successfully',
            'channels_sent': success_channels
        }), 200
    else:
        return jsonify({
            'error': 'Failed to send test notification',
            'hint': 'Please check your notification settings and credentials'
        }), 500


@notify_bp.route('/test-email', methods=['POST'])
@token_required
def test_email(current_user):
    """
    Gửi email notification kiểm tra đến email chỉ định hoặc mặc định
    Request Body (optional): {"email": "example@gmail.com"}
    Mặc định sẽ gửi tới email của user hiện tại
    """
    data = request.get_json(silent=True) or {}
    recipient = data.get('email', current_user['email'])
    if not recipient or not validate_email(str(recipient)):
        return jsonify({'error': 'Invalid email format'}), 400

    ok = send_test_email_notification(recipient)
    if ok:
        return jsonify({
            'message': 'Test email notification sent successfully',
            'recipient': recipient
        }), 200
    else:
        return jsonify({
            'error': 'Failed to send test email notification',
            'recipient': recipient,
            'hint': 'Check SMTP settings in environment'
        }), 500
        
@notify_bp.route('/debug-telegram', methods=['GET'])
@token_required
def debug_telegram(current_user):
    """
    Endpoint debug để kiểm tra thông tin từ Telegram API
    Trả về danh sách các cập nhật gần đây và các username/chat_id đã tìm thấy
    """
    if not TELEGRAM_BOT_TOKEN:
        return jsonify({
            'error': 'TELEGRAM_BOT_TOKEN is missing in environment variables',
            'status': 'error'
        }), 400
        
    try:
        # Lấy cập nhật gần đây từ Telegram API
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
        resp = requests.get(url, timeout=5)
        
        if resp.status_code != 200:
            return jsonify({
                'error': f'Telegram API error: {resp.status_code}',
                'response': resp.text,
                'status': 'error'
            }), 500
            
        data = resp.json()
        results = data.get('result') or []
        
        # Phân tích các cập nhật để tìm username và chat_id
        users_found = []
        for upd in results:
            msg = upd.get('message') or upd.get('channel_post') or {}
            chat = msg.get('chat') or {}
            from_user = msg.get('from') or {}
            
            chat_id = chat.get('id')
            chat_type = chat.get('type', '')
            chat_username = chat.get('username', '')
            chat_first_name = chat.get('first_name', '')
            chat_last_name = chat.get('last_name', '')
            
            from_username = from_user.get('username', '')
            from_first_name = from_user.get('first_name', '')
            from_last_name = from_user.get('last_name', '')
            
            users_found.append({
                'chat_id': chat_id,
                'chat_type': chat_type,
                'chat_username': chat_username,
                'chat_name': f"{chat_first_name} {chat_last_name}".strip(),
                'from_username': from_username,
                'from_name': f"{from_first_name} {from_last_name}".strip(),
                'message_date': msg.get('date'),
                'message_text': msg.get('text', '')[:50]  # Giới hạn độ dài tin nhắn
            })
        
        return jsonify({
            'status': 'success',
            'updates_count': len(results),
            'users_found': users_found,
            'raw_updates': results[:5]  # Giới hạn số lượng cập nhật trả về
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': f'Error: {str(e)}',
            'status': 'error'
        }), 500
@notify_bp.route('/test-telegram', methods=['POST'])
@token_required
def test_telegram(current_user):
    """
    Gửi Telegram notification kiểm tra đến ID chỉ định hoặc mặc định
    Request Body (optional): {"telegram_id": "username"}
    Mặc định sẽ gửi tới: Robin Vu
    """
    data = request.get_json(silent=True) or {}
    recipient = data.get('telegram_id', 'Robin Vu')
    ok, msg = validate_telegram_id(recipient)
    if not ok:
        return jsonify({'error': msg, 'recipient': recipient}), 400

    ok = send_test_telegram_notification(recipient)
    if ok:
        return jsonify({
            'message': 'Test Telegram notification sent successfully',
            'recipient': recipient
        }), 200
    else:
        # Kiểm tra lý do thất bại cụ thể
        from services.notification_service import TELEGRAM_BOT_TOKEN
        if not TELEGRAM_BOT_TOKEN:
            hint = "TELEGRAM_BOT_TOKEN is missing in environment variables"
        elif isinstance(recipient, str) and not recipient.isdigit() and not recipient.startswith('@'):
            hint = f"Username should start with @ symbol: @{recipient}"
        else:
            hint = "User must start a chat with the bot (t.me/ScheduleSmartAIbot) so chat_id can be resolved."
        
        return jsonify({
            'error': 'Failed to send test Telegram notification',
            'recipient': recipient,
            'hint': hint
        }), 500


@notify_bp.route('/upcoming', methods=['GET'])
@token_required
def get_upcoming_notifications(current_user):
    """
    Lấy danh sách thông báo sắp được gửi (scheduled)
    """
    user_id = current_user['user_id']
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT s.id, s.subject, s.start_time, s.location, s.reminder_time
            FROM schedule s
            WHERE s.user_id = ?
            AND s.start_time >= datetime('now')
            AND s.start_time <= datetime('now', '+7 days')
            ORDER BY s.start_time ASC
        ''', (user_id,))
        
        schedules = cursor.fetchall()
    
    upcoming = []
    for s in schedules:
        from datetime import datetime, timedelta
        start_time = datetime.fromisoformat(s['start_time'])
        notify_time = start_time - timedelta(minutes=s['reminder_time'])
        
        upcoming.append({
            'schedule_id': s['id'],
            'subject': s['subject'],
            'class_time': s['start_time'],
            'location': s['location'],
            'notify_at': notify_time.isoformat(),
            'reminder_minutes': s['reminder_time']
        })
    
    return jsonify({
        'count': len(upcoming),
        'upcoming_notifications': upcoming
    }), 200


@notify_bp.route('/stats', methods=['GET'])
@token_required
def get_notification_stats(current_user):
    """
    Thống kê thông báo
    """
    user_id = current_user['user_id']
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Total sent
        cursor.execute('''
            SELECT COUNT(*) as total FROM notifications
            WHERE user_id = ? AND sent = 1
        ''', (user_id,))
        total = cursor.fetchone()['total']
        
        # This week
        cursor.execute('''
            SELECT COUNT(*) as count FROM notifications
            WHERE user_id = ? AND sent = 1
            AND date(created_at) >= date('now', 'weekday 0', '-7 days')
        ''', (user_id,))
        this_week = cursor.fetchone()['count']
        
        # By channel
        cursor.execute('''
            SELECT channel, COUNT(*) as count
            FROM notifications
            WHERE user_id = ? AND sent = 1
            GROUP BY channel
        ''', (user_id,))
        by_channel = {row['channel']: row['count'] for row in cursor.fetchall()}
    
    return jsonify({
        'stats': {
            'total_sent': total,
            'sent_this_week': this_week,
            'by_channel': by_channel
        }
    }), 200

