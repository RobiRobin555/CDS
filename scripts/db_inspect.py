import sqlite3
from datetime import datetime, timedelta

DB_PATH = 'smartschedule.db'

def insert_test_schedule(user_id: int = 26, minutes_from_now: int = 12):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        c = conn.cursor()
        now = datetime.now()
        start = (now + timedelta(minutes=minutes_from_now)).strftime('%Y-%m-%d %H:%M:%S')
        end = (now + timedelta(minutes=minutes_from_now + 30)).strftime('%Y-%m-%d %H:%M:%S')
        c.execute(
            '''INSERT INTO schedule (user_id, subject, description, start_time, end_time, location, type, color, reminder_time)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (user_id, 'Test Reminder', 'Auto-inserted for scheduler test', start, end, 'Test Location', 'class', '#3788d8', 30)
        )
        conn.commit()
        print(f"✅ Inserted test schedule for user {user_id} at {start}")
    finally:
        conn.close()

def show_user_settings(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        c = conn.cursor()
        c.execute('SELECT * FROM notification_settings WHERE user_id = ?', (user_id,))
        row = c.fetchone()
        print("🔧 Notification Settings:", dict(row) if row else None)
    finally:
        conn.close()

def show_upcoming_schedules(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        c = conn.cursor()
        c.execute(
            '''SELECT id, subject, start_time, location FROM schedule
               WHERE user_id = ? AND datetime(start_time) > datetime('now')
               ORDER BY datetime(start_time) ASC''',
            (user_id,)
        )
        rows = c.fetchall()
        print(f"📅 Upcoming schedules ({len(rows)}):")
        for r in rows[:5]:
            print(" - ", dict(r))
    finally:
        conn.close()

def show_notifications(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        c = conn.cursor()
        c.execute('SELECT id, schedule_id, channel, reminder_offset, send_time FROM notifications WHERE user_id = ? ORDER BY send_time DESC LIMIT 10', (user_id,))
        rows = c.fetchall()
        print(f"🔔 Notifications ({len(rows)}):")
        for r in rows:
            print(" - ", dict(r))
    finally:
        conn.close()

if __name__ == '__main__':
    uid = 26
    # Reduce offsets for quick scheduler test
    conn = sqlite3.connect(DB_PATH)
    try:
        c = conn.cursor()
        c.execute('UPDATE notification_settings SET email_enabled=1, telegram_enabled=1, in_app_enabled=1, email_reminder_offset=1, telegram_reminder_offset=1 WHERE user_id = ?', (uid,))
        conn.commit()
        print("🔧 Updated reminder offsets to 1 minute for user", uid)
    finally:
        conn.close()

    show_user_settings(uid)
    insert_test_schedule(uid, 3)
    show_upcoming_schedules(uid)
    show_notifications(uid)

    # Move the most recent test schedule closer (1 minute from now)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        c = conn.cursor()
        c.execute("SELECT id FROM schedule WHERE user_id=? ORDER BY id DESC LIMIT 1", (uid,))
        row = c.fetchone()
        if row:
            new_start = (datetime.now() + timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S')
            new_end = (datetime.now() + timedelta(minutes=31)).strftime('%Y-%m-%d %H:%M:%S')
            c.execute("UPDATE schedule SET start_time=?, end_time=? WHERE id=?", (new_start, new_end, row['id']))
            conn.commit()
            print(f"⏱️  Adjusted schedule {row['id']} start_time to {new_start}")
    finally:
        conn.close()
import json

def row_to_dict(row):
    return {k: row[k] for k in row.keys()}

def main():
    conn = sqlite3.connect('smartschedule.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    users = [row_to_dict(r) for r in c.execute('SELECT id, name, email, telegram_id FROM users').fetchall()]
    settings = [row_to_dict(r) for r in c.execute('SELECT user_id, email_enabled, telegram_enabled, in_app_enabled, email_reminder_offset, telegram_reminder_offset FROM notification_settings').fetchall()]
    upcoming = [row_to_dict(r) for r in c.execute("SELECT id, user_id, subject, start_time, type FROM schedule WHERE start_time BETWEEN datetime('now') AND datetime('now','+1 day') ORDER BY start_time ASC").fetchall()]
    logs = [row_to_dict(r) for r in c.execute('SELECT id, user_id, schedule_id, channel, reminder_offset, event_type, created_at FROM notifications ORDER BY id DESC LIMIT 20').fetchall()]

    print(json.dumps({
        'users': users,
        'settings': settings,
        'upcoming': upcoming,
        'logs': logs
    }, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
