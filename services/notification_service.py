"""
services/notification_service.py - APScheduler + Email + Telegram + WebSocket
"""

import logging
from flask import current_app
from apscheduler.schedulers.background import BackgroundScheduler
from models import get_db
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import os
from utils.auth import validate_email

# ==================== CONFIGURATION ====================

# Email SMTP Configuration
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = os.getenv('SMTP_PORT', 587)
SMTP_EMAIL = os.getenv('SMTP_EMAIL', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')  # App Password nếu dùng Gmail

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')

# WebSocket (sẽ được set từ app.py)
socketio = None

def set_socketio(sio):
    """Set socketio instance từ app.py"""
    global socketio
    socketio = sio


# ==================== SCHEDULER ====================

scheduler = BackgroundScheduler()

def start_notification_scheduler(app):
    """Khởi động scheduler"""
    scheduler.add_job(
        func=check_and_send_reminders,
        trigger='interval',
        minutes=5,  # Chạy mỗi 5 phút
        id='notification_checker',
        replace_existing=True,
        args=[app]
    )
    scheduler.start()
    print("✅ Notification Scheduler started (running every 5 minutes)")


def stop_notification_scheduler():
    """Dừng scheduler"""
    scheduler.shutdown()
    print("❌ Notification Scheduler stopped")


# ==================== MAIN NOTIFICATION LOGIC ====================

def check_and_send_reminders(app):
    """
    Periodically checks upcoming schedules and sends reminders using raw SQL via get_db.
    Avoids ORM to match current models.py implementation.
    """
    logging.info("Scheduler: Running check_and_send_reminders job.")
    try:
        with app.app_context():
            now = datetime.now()
            logging.info(f"Scheduler: Current time is {now.strftime('%Y-%m-%d %H:%M:%S')}")

            # Fetch users with their notification settings
            with get_db() as conn:
                c = conn.cursor()
                c.execute(
                    '''
                    SELECT u.id AS user_id, u.name, u.email, u.telegram_id,
                           ns.email_enabled, ns.telegram_enabled, ns.in_app_enabled,
                           ns.email_reminder_offset, ns.telegram_reminder_offset
                    FROM users u
                    LEFT JOIN notification_settings ns ON ns.user_id = u.id
                    '''
                )
                users = c.fetchall()

            if not users:
                logging.info("Scheduler: No users found with notification settings. Skipping.")
                return

            logging.info(f"Scheduler: Found {len(users)} users with notification settings.")

            for u in users:
                user_id = u['user_id']
                user_name = u['name']
                logging.info(
                    f"Scheduler: Checking user {user_id} ({user_name}) settings: "
                    f"email_enabled={u['email_enabled']}, telegram_enabled={u['telegram_enabled']}, in_app_enabled={u['in_app_enabled']}"
                )

                # Fetch upcoming schedules for this user
                with get_db() as conn:
                    c = conn.cursor()
                    c.execute(
                        '''
                        SELECT id, subject, start_time, location, type
                        FROM schedule
                        WHERE user_id = ? AND datetime(start_time) > datetime('now')
                        ORDER BY datetime(start_time) ASC
                        '''
                    , (user_id,))
                    schedules = c.fetchall()

                if not schedules:
                    logging.info(f"Scheduler: No upcoming schedules for user {user_id}.")
                    continue

                logging.info(f"Scheduler: Found {len(schedules)} upcoming schedules for user {user_id}.")

                for s in schedules:
                    # Parse schedule start_time
                    try:
                        start_dt = datetime.strptime(s['start_time'], '%Y-%m-%d %H:%M:%S')
                    except Exception:
                        try:
                            # Fallback to fromisoformat if format differs
                            start_dt = datetime.fromisoformat(s['start_time'])
                        except Exception:
                            logging.warning(f"Scheduler: Could not parse start_time '{s['start_time']}' for schedule {s['id']}.")
                            continue

                    event_type = s.get('type') if isinstance(s, dict) else (s['type'] if 'type' in s.keys() else 'class')

                    # Email reminder
                    if u['email_enabled'] and u['email'] and u['email_reminder_offset'] is not None:
                        reminder_dt = start_dt - timedelta(minutes=int(u['email_reminder_offset']))
                        logging.info(
                            f"Scheduler: Email reminder for '{s['subject']}' at {reminder_dt.strftime('%Y-%m-%d %H:%M:%S')} (offset {u['email_reminder_offset']}m)."
                        )
                        if now >= reminder_dt and now < start_dt:
                            # Check if already sent for this schedule and offset via email
                            with get_db() as conn:
                                c = conn.cursor()
                                c.execute(
                                    '''
                                    SELECT id FROM notifications
                                    WHERE schedule_id = ? AND channel LIKE '%email%'
                                      AND reminder_offset = ?
                                    LIMIT 1
                                    '''
                                , (s['id'], int(u['email_reminder_offset'])))
                                already = c.fetchone()
                            if not already:
                                msg = (
                                    f"🔔 Nhắc nhở: '{s['subject']}' sẽ bắt đầu lúc {start_dt.strftime('%H:%M')}."
                                )
                                ok = send_email_notification(u['email'], user_name, msg,
                                                             {'id': s['id'], 'subject': s['subject'], 'start_time': s['start_time'], 'location': s['location']},
                                                             int(u['email_reminder_offset']), event_type or 'class')
                                if ok:
                                    save_notification_log(user_id, s['id'], msg, ['email'], int(u['email_reminder_offset']), event_type or 'class')
                                    logging.info(f"Scheduler: EMAIL sent for schedule '{s['subject']}' to user {user_id}.")
                                else:
                                    logging.warning(f"Scheduler: EMAIL failed for schedule '{s['subject']}' to user {user_id}.")
                            else:
                                logging.info(f"Scheduler: Email reminder already logged for schedule '{s['subject']}'.")
                        else:
                            logging.info(f"Scheduler: Not time yet for EMAIL reminder for '{s['subject']}'.")

                    # Telegram reminder
                    if u['telegram_enabled'] and u['telegram_id'] and u['telegram_reminder_offset'] is not None:
                        reminder_dt = start_dt - timedelta(minutes=int(u['telegram_reminder_offset']))
                        logging.info(
                            f"Scheduler: Telegram reminder for '{s['subject']}' at {reminder_dt.strftime('%Y-%m-%d %H:%M:%S')} (offset {u['telegram_reminder_offset']}m)."
                        )
                        if now >= reminder_dt and now < start_dt:
                            with get_db() as conn:
                                c = conn.cursor()
                                c.execute(
                                    '''
                                    SELECT id FROM notifications
                                    WHERE schedule_id = ? AND channel LIKE '%telegram%'
                                      AND reminder_offset = ?
                                    LIMIT 1
                                    '''
                                , (s['id'], int(u['telegram_reminder_offset'])))
                                already = c.fetchone()
                            if not already:
                                msg = (
                                    f"🔔 Nhắc nhở: '{s['subject']}' sẽ bắt đầu lúc {start_dt.strftime('%H:%M')}."
                                )
                                ok = send_telegram_notification(u['telegram_id'], msg,
                                                                {'id': s['id'], 'subject': s['subject'], 'start_time': s['start_time'], 'location': s['location']},
                                                                int(u['telegram_reminder_offset']), event_type or 'class')
                                if ok:
                                    save_notification_log(user_id, s['id'], msg, ['telegram'], int(u['telegram_reminder_offset']), event_type or 'class')
                                    logging.info(f"Scheduler: TELEGRAM sent for schedule '{s['subject']}' to user {user_id}.")
                                else:
                                    logging.warning(f"Scheduler: TELEGRAM failed for schedule '{s['subject']}' to user {user_id}.")
                            else:
                                logging.info(f"Scheduler: Telegram reminder already logged for schedule '{s['subject']}'.")
                        else:
                            logging.info(f"Scheduler: Not time yet for TELEGRAM reminder for '{s['subject']}'.")

                    # In-app reminder via WebSocket (optional)
                    if u['in_app_enabled']:
                        # We can choose an appropriate offset or mirror email offset
                        pass

    except Exception as e:
        logging.error(f"Scheduler: An error occurred in check_and_send_reminders: {e}", exc_info=True)


def send_notification(user_id, schedule_id, notification_type, message):
    """
    Gửi thông báo qua các kênh đã kích hoạt
    """
    user_id = schedule['user_id']
    schedule_id = schedule['id']
    
    notification_message = format_notification_message(schedule, offset_minutes)
    
    # Gửi qua các kênh
    channels_sent = []
    
    if schedule['email_enabled'] and schedule['email']:
        if send_email_notification(schedule['email'], schedule['name'], notification_message, schedule, offset_minutes, schedule.get('event_type', 'class')):
            channels_sent.append('email')
    
    if schedule['telegram_enabled'] and schedule['telegram_id']:
        if send_telegram_notification(schedule['telegram_id'], notification_message, schedule, offset_minutes, schedule.get('event_type', 'class')):
            channels_sent.append('telegram')
    
    if schedule['in_app_enabled']:
        if send_websocket_notification(user_id, notification_message, schedule, offset_minutes, schedule.get('event_type', 'class')):
            channels_sent.append('in-app')
    
    # Lưu vào database
    save_notification_log(user_id, schedule_id, notification_message, channels_sent, offset_minutes, schedule.get('event_type', 'class'))
    
    print(f"   ✅ Sent notification for '{schedule['subject']}' via {', '.join(channels_sent)}")


def _offset_text(offset_minutes: int, event_type: str) -> str:
    if event_type == 'exam':
        if offset_minutes == 10080:
            return 'Còn 1 tuần trước giờ thi'
        if offset_minutes == 4320:
            return 'Còn 3 ngày trước giờ thi'
        if offset_minutes == 1440:
            return 'Còn 1 ngày trước giờ thi'
    else:
        if offset_minutes == 60:
            return 'Còn 60 phút trước giờ học'
        if offset_minutes == 30:
            return 'Còn 30 phút trước giờ học'
    return f"Còn {offset_minutes} phút nữa"


def format_notification_message(schedule, offset_minutes: int):
    """Format tin nhắn thông báo theo loại sự kiện và mốc nhắc nhở"""
    event_type = schedule.get('event_type', 'class')
    offset_text = _offset_text(offset_minutes, event_type)

    message = f"""🔔 Nhắc nhở {('lịch thi' if event_type=='exam' else 'lịch học')}

📚 Môn: {schedule['subject']}
🕐 Thời gian: {schedule['start_time']}
📍 Địa điểm: {schedule['location']}

⏰ {offset_text}! Chuẩn bị nhé.
"""
    return message.strip()


# ==================== EMAIL NOTIFICATION ====================

def send_email_notification(email, name, message, schedule, offset_minutes: int = None, event_type: str = 'class'):
    """Gửi email notification"""
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        print("   ⚠️  SMTP not configured, skipping email")
        return False
    
    try:
        msg = MIMEMultipart('alternative')
        # Tiêu đề có mốc nhắc nhở
        offset_text = _offset_text(offset_minutes or 0, event_type)
        subject_prefix = 'Nhắc nhở thi' if event_type == 'exam' else 'Nhắc nhở học'
        msg['Subject'] = f"[SmartSchedule] {subject_prefix}: {schedule['subject']} ({offset_text})"
        msg['From'] = f"SmartSchedule.AI <{SMTP_EMAIL}>"
        msg['To'] = email
        
        # Plain text version
        text_content = f"Xin chào {name},\n\n{message}\n\n-- SmartSchedule.AI"
        
        # HTML version
        html_content = f"""
        <html>
          <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
              <h2 style="color: #2196F3; margin-top: 0;">🔔 {('Nhắc nhở lịch thi' if event_type=='exam' else 'Nhắc nhở lịch học')}</h2>
              <p>Xin chào <strong>{name}</strong>,</p>
              
              <div style="background-color: #E3F2FD; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <p style="margin: 5px 0;"><strong>📚 Môn học:</strong> {schedule['subject']}</p>
                <p style="margin: 5px 0;"><strong>🕐 Thời gian:</strong> {schedule['start_time']}</p>
                <p style="margin: 5px 0;"><strong>📍 Địa điểm:</strong> {schedule['location']}</p>
              </div>
              
              <p style="color: #FF5722; font-weight: bold;">⏰ {offset_text}! Chuẩn bị nhé.</p>
              
              <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
              <p style="color: #999; font-size: 12px;">SmartSchedule.AI - Trợ lý quản lý lịch học thông minh</p>
            </div>
          </body>
        </html>
        """
        
        msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
        
        return True
    
    except Exception as e:
        print(f"   ❌ Email send failed: {e}")
        return False


# ==================== TEST NOTIFICATIONS ====================

def send_test_email_notification(recipient_email: str):
    """Gửi email kiểm tra cấu hình SMTP đến địa chỉ chỉ định"""
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        print("   ⚠️  SMTP not configured, skipping email test")
        return False

    if not recipient_email or not validate_email(recipient_email):
        print("   ❌ Invalid test email address")
        return False

    dummy_schedule = {
        'id': 0,
        'subject': 'Test Email Notification',
        'start_time': datetime.now().isoformat(timespec='seconds'),
        'location': 'N/A'
    }

    test_message = (
        "🔔 Email kiểm tra từ SmartSchedule.AI\n\n"
        "Đây là email dùng để xác minh cấu hình SMTP hoạt động.\n"
        "Nếu bạn nhận được thư này, việc gửi mail đã thành công.\n\n"
        "— SmartSchedule.AI"
    )

    return send_email_notification(recipient_email, 'SmartSchedule Tester', test_message, dummy_schedule)


def send_test_telegram_notification(telegram_id: str):
    """Gửi Telegram notification kiểm tra cấu hình đến ID chỉ định"""
    if not TELEGRAM_BOT_TOKEN:
        print("   ⚠️  Telegram bot not configured, skipping test")
        return False

    if not telegram_id:
        print("   ❌ Invalid Telegram ID")
        return False

    dummy_schedule = {
        'id': 0,
        'subject': 'Test Telegram Notification',
        'start_time': datetime.now().isoformat(timespec='seconds'),
        'location': 'N/A'
    }

    test_message = (
        "🔔 Telegram kiểm tra từ SmartSchedule.AI\n\n"
        "Đây là tin nhắn dùng để xác minh cấu hình Telegram Bot hoạt động.\n"
        "Nếu bạn nhận được tin nhắn này, việc gửi Telegram đã thành công.\n\n"
        "— SmartSchedule.AI"
    )

    return send_telegram_notification(telegram_id, test_message, dummy_schedule)


# ==================== TELEGRAM NOTIFICATION ====================

def _resolve_chat_id_from_updates(username: str):
    """
    Tìm chat_id từ username trong getUpdates của Telegram API
    Hỗ trợ nhiều định dạng username: 'username', '@username', 'First Last'
    """
    if not username or not TELEGRAM_BOT_TOKEN:
        return None
        
    try:
        # Chuẩn hóa username (bỏ @ nếu có)
        clean_username = username.lstrip('@').lower().strip()
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
        resp = requests.get(url, timeout=5)
        if resp.status_code != 200:
            return None
            
        data = resp.json()
        results = data.get('result') or []
        
        # Duyệt qua các cập nhật từ mới đến cũ
        for upd in reversed(results):
            msg = upd.get('message') or upd.get('channel_post') or {}
            chat = msg.get('chat') or {}
            from_user = msg.get('from') or {}
            
            # Kiểm tra username trong chat
            chat_username = (chat.get('username') or '').lower()
            
            # Kiểm tra username trong from_user
            from_username = (from_user.get('username') or '').lower()
            
            # Kiểm tra tên đầy đủ
            chat_fullname = f"{chat.get('first_name', '')} {chat.get('last_name', '')}".lower().strip()
            from_fullname = f"{from_user.get('first_name', '')} {from_user.get('last_name', '')}".lower().strip()
            
            # So khớp với các định dạng khác nhau
            if (chat_username == clean_username or 
                from_username == clean_username or
                chat_fullname == clean_username or
                from_fullname == clean_username):
                
                chat_id = chat.get('id')
                if isinstance(chat_id, int):
                    return chat_id
        
        # Không tìm thấy
        return None
    except Exception as e:
        print(f"Error resolving chat_id: {str(e)}")
        return None

def send_telegram_notification(telegram_id, message, schedule, offset_minutes: int = None, event_type: str = 'class'):
    """Gửi Telegram notification"""
    if not TELEGRAM_BOT_TOKEN:
        print("   ⚠️  Telegram bot not configured, skipping")
        return False
    
    try:
        # Format message cho Telegram (Markdown)
        offset_text = _offset_text(offset_minutes or 0, event_type)
        title = "Nhắc nhở lịch thi" if event_type == 'exam' else "Nhắc nhở lịch học"
        telegram_message = f"""
🔔 *{title}*

📚 Môn: *{schedule['subject']}*
🕐 Thời gian: `{schedule['start_time']}`
📍 Địa điểm: {schedule['location']}

⏰ {offset_text}! Chuẩn bị nhé.
        """.strip()
        
        chat_id = telegram_id
        if telegram_id and isinstance(telegram_id, str) and not telegram_id.isdigit():
            uname = telegram_id.lstrip('@').strip()
            print(f"   Attempting to resolve chat_id for username: {uname}")
            mapped_id = _resolve_chat_id_from_updates(uname)
            if mapped_id:
                chat_id = mapped_id
                print(f"   Successfully resolved chat_id: {chat_id}")
            else:
                # Fallback to username if not resolved
                chat_id = f'@{uname}'
                print(f"   Could not resolve chat_id, falling back to username: {chat_id}")
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': telegram_message,
            'parse_mode': 'Markdown'
        }
        
        response = requests.post(url, json=payload, timeout=5)
        
        if response.status_code == 200:
            print(f"   ✅ Telegram notification sent to {chat_id}")
            return True
        else:
            print(f"   ❌ Telegram send failed to {chat_id}: {response.status_code} - {response.text}")
            return False
    
    except Exception as e:
        print(f"   ❌ Telegram send failed: {e}")
        return False


# ==================== WEBSOCKET NOTIFICATION ====================

def send_websocket_notification(user_id, message, schedule, offset_minutes: int = None, event_type: str = 'class'):
    """Gửi in-app notification qua WebSocket"""
    if not socketio:
        print("   ⚠️  SocketIO not initialized, skipping in-app notification")
        return False
    
    try:
        notification_data = {
            'type': 'exam_reminder' if event_type == 'exam' else 'class_reminder',
            'schedule_id': schedule['id'],
            'subject': schedule['subject'],
            'start_time': schedule['start_time'],
            'location': schedule['location'],
            'message': message,
            'offset_minutes': offset_minutes,
            'timestamp': datetime.now().isoformat()
        }
        
        # Emit to specific user room
        socketio.emit('notification', notification_data, room=f"user_{user_id}")
        
        return True
    
    except Exception as e:
        print(f"   ❌ WebSocket send failed: {e}")
        return False


# ==================== DATABASE LOGGING ====================

def save_notification_log(user_id, schedule_id, message, channels, reminder_offset=None, event_type=None):
    """Lưu log notification vào database, kèm mốc nhắc nhở và loại sự kiện"""
    channel_str = ','.join(channels) if channels else 'none'

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO notifications 
            (user_id, schedule_id, message, send_time, sent, channel, reminder_offset, event_type)
            VALUES (?, ?, ?, ?, 1, ?, ?, ?)
        ''', (user_id, schedule_id, message, datetime.now().isoformat(), channel_str, reminder_offset, event_type))


# ==================== TELEGRAM BOT COMMANDS ====================

def setup_telegram_bot_webhook():
    """
    Setup Telegram Bot webhook (optional - cho production)
    Để test local dùng polling trong file riêng
    """
    if not TELEGRAM_BOT_TOKEN:
        return
    
    # Code để setup webhook - skip trong development
    pass


def handle_telegram_command(chat_id, command, user_id=None):
    """
    Xử lý Telegram bot commands
    Commands: /start, /today, /week, /tasks
    """
    if not TELEGRAM_BOT_TOKEN:
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    if command == '/start':
        message = """
👋 Chào mừng đến với SmartSchedule.AI Bot!

Các lệnh có sẵn:
/today - Xem lịch hôm nay
/week - Xem lịch tuần này
/tasks - Xem nhiệm vụ cần làm
/help - Hướng dẫn sử dụng

Để bật thông báo, vui lòng liên kết Telegram ID trong ứng dụng web.
        """
        
    elif command == '/today' and user_id:
        message = get_today_schedule_telegram(user_id)
    
    elif command == '/week' and user_id:
        message = get_week_schedule_telegram(user_id)
    
    elif command == '/tasks' and user_id:
        message = get_tasks_telegram(user_id)
    
    else:
        message = "Vui lòng liên kết tài khoản trong ứng dụng web để sử dụng lệnh này."
    
    requests.post(url, json={
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown'
    })


def get_today_schedule_telegram(user_id):
    """Lấy lịch hôm nay cho Telegram"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT subject, start_time, location
            FROM schedule
            WHERE user_id = ?
            AND date(start_time) = date('now')
            ORDER BY start_time ASC
        ''', (user_id,))
        schedules = cursor.fetchall()
    
    if not schedules:
        return "📅 Hôm nay bạn không có lịch nào."
    
    message = "📅 *Lịch hôm nay:*\n\n"
    for s in schedules:
        time = s['start_time'].split()[1][:5]
        message += f"• `{time}` - {s['subject']} tại {s['location']}\n"
    
    return message


def get_week_schedule_telegram(user_id):
    """Lấy lịch tuần này cho Telegram"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT subject, start_time
            FROM schedule
            WHERE user_id = ?
            AND start_time BETWEEN date('now') AND date('now', '+7 days')
            ORDER BY start_time ASC
            LIMIT 10
        ''', (user_id,))
        schedules = cursor.fetchall()
    
    if not schedules:
        return "📊 Tuần này bạn không có lịch nào."
    
    message = "📊 *Lịch tuần này:*\n\n"
    for s in schedules:
        date_time = s['start_time'].replace(' ', ' `') + '`'
        message += f"• {date_time} - {s['subject']}\n"
    
    return message


def get_tasks_telegram(user_id):
    """Lấy tasks cho Telegram"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT title, due_date, priority, status
            FROM tasks
            WHERE user_id = ?
            AND status != 'completed'
            ORDER BY due_date ASC
            LIMIT 10
        ''', (user_id,))
        tasks = cursor.fetchall()
    
    if not tasks:
        return "✅ Bạn không có nhiệm vụ nào đang chờ."
    
    message = "📝 *Nhiệm vụ cần làm:*\n\n"
    for t in tasks:
        emoji = "🔴" if t['priority'] == 'high' else "🟡" if t['priority'] == 'medium' else "🟢"
        message += f"{emoji} {t['title']}\n   Deadline: `{t['due_date']}`\n\n"
    
    return message


# ==================== MANUAL NOTIFICATION ====================

def send_manual_notification(user_id, message, channels=['email', 'telegram', 'in-app']):
    """
    Gửi notification thủ công (dùng cho testing hoặc custom notifications)
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.*, ns.*
            FROM users u
            JOIN notification_settings ns ON ns.user_id = u.id
            WHERE u.id = ?
        ''', (user_id,))
        user = cursor.fetchone()
    
    if not user:
        return False
    
    success = []
    
    if 'email' in channels and user['email_enabled'] and user['email']:
        dummy_schedule = {
            'subject': 'Thông báo từ SmartSchedule',
            'start_time': datetime.now().isoformat(),
            'location': 'N/A'
        }
        if send_email_notification(user['email'], user['name'], message, dummy_schedule):
            success.append('email')
    
    if 'telegram' in channels and user['telegram_enabled'] and user['telegram_id']:
        if send_telegram_notification(user['telegram_id'], message, {'id': 0, 'subject': 'Notification', 'start_time': '', 'location': ''}):
            success.append('telegram')
    
    if 'in-app' in channels:
        if send_websocket_notification(user_id, message, {'id': 0, 'subject': 'Notification', 'start_time': '', 'location': ''}):
            success.append('in-app')
    
    return success

import logging

def setup_telegram_bot_webhook():
    """
    Setup Telegram Bot webhook (optional - cho production)
    Để test local dùng polling trong file riêng
    """
    if not TELEGRAM_BOT_TOKEN:
        return
    
    # Code để setup webhook - skip trong development
    pass


def handle_telegram_command(chat_id, command, user_id=None):
    """
    Xử lý Telegram bot commands
    Commands: /start, /today, /week, /tasks
    """
    if not TELEGRAM_BOT_TOKEN:
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    if command == '/start':
        message = """
👋 Chào mừng đến với SmartSchedule.AI Bot!

Các lệnh có sẵn:
/today - Xem lịch hôm nay
/week - Xem lịch tuần này
/tasks - Xem nhiệm vụ cần làm
/help - Hướng dẫn sử dụng

Để bật thông báo, vui lòng liên kết Telegram ID trong ứng dụng web.
        """
        
    elif command == '/today' and user_id:
        message = get_today_schedule_telegram(user_id)
    
    elif command == '/week' and user_id:
        message = get_week_schedule_telegram(user_id)
    
    elif command == '/tasks' and user_id:
        message = get_tasks_telegram(user_id)
    
    else:
        message = "Vui lòng liên kết tài khoản trong ứng dụng web để sử dụng lệnh này."
    
    requests.post(url, json={
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown'
    })


def get_today_schedule_telegram(user_id):
    """Lấy lịch hôm nay cho Telegram"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT subject, start_time, location
            FROM schedule
            WHERE user_id = ?
            AND date(start_time) = date('now')
            ORDER BY start_time ASC
        ''', (user_id,))
        schedules = cursor.fetchall()
    
    if not schedules:
        return "📅 Hôm nay bạn không có lịch nào."
    
    message = "📅 *Lịch hôm nay:*\n\n"
    for s in schedules:
        time = s['start_time'].split()[1][:5]
        message += f"• `{time}` - {s['subject']} tại {s['location']}\n"
    
    return message


def get_week_schedule_telegram(user_id):
    """Lấy lịch tuần này cho Telegram"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT subject, start_time
            FROM schedule
            WHERE user_id = ?
            AND start_time BETWEEN date('now') AND date('now', '+7 days')
            ORDER BY start_time ASC
            LIMIT 10
        ''', (user_id,))
        schedules = cursor.fetchall()
    
    if not schedules:
        return "📊 Tuần này bạn không có lịch nào."
    
    message = "📊 *Lịch tuần này:*\n\n"
    for s in schedules:
        date_time = s['start_time'].replace(' ', ' `') + '`'
        message += f"• {date_time} - {s['subject']}\n"
    
    return message


def get_tasks_telegram(user_id):
    """Lấy tasks cho Telegram"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT title, due_date, priority, status
            FROM tasks
            WHERE user_id = ?
            AND status != 'completed'
            ORDER BY due_date ASC
            LIMIT 10
        ''', (user_id,))
        tasks = cursor.fetchall()
    
    if not tasks:
        return "✅ Bạn không có nhiệm vụ nào đang chờ."
    
    message = "📝 *Nhiệm vụ cần làm:*\n\n"
    for t in tasks:
        emoji = "🔴" if t['priority'] == 'high' else "🟡" if t['priority'] == 'medium' else "🟢"
        message += f"{emoji} {t['title']}\n   Deadline: `{t['due_date']}`\n\n"
    
    return message


# ==================== MANUAL NOTIFICATION ====================

def send_manual_notification(user_id, message, channels=['email', 'telegram', 'in-app']):
    """
    Gửi notification thủ công (dùng cho testing hoặc custom notifications)
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.*, ns.*
            FROM users u
            JOIN notification_settings ns ON ns.user_id = u.id
            WHERE u.id = ?
        ''', (user_id,))
        user = cursor.fetchone()
    
    if not user:
        return False
    
    success = []
    
    if 'email' in channels and user['email_enabled'] and user['email']:
        dummy_schedule = {
            'subject': 'Thông báo từ SmartSchedule',
            'start_time': datetime.now().isoformat(),
            'location': 'N/A'
        }
        if send_email_notification(user['email'], user['name'], message, dummy_schedule):
            success.append('email')
    
    if 'telegram' in channels and user['telegram_enabled'] and user['telegram_id']:
        if send_telegram_notification(user['telegram_id'], message, {'id': 0, 'subject': 'Notification', 'start_time': '', 'location': ''}):
            success.append('telegram')
    
    if 'in-app' in channels:
        if send_websocket_notification(user_id, message, {'id': 0, 'subject': 'Notification', 'start_time': '', 'location': ''}):
            success.append('in-app')
    
    return success
