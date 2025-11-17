import sqlite3

DB_PATH = 'smartschedule.db'
UID = 26

def show_notifications(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        c = conn.cursor()
        c.execute('SELECT id, user_id, schedule_id, channel, reminder_offset, send_time FROM notifications WHERE user_id = ? ORDER BY send_time DESC LIMIT 20', (user_id,))
        rows = c.fetchall()
        print(f"🔔 Notifications for user {user_id} ({len(rows)}):")
        for r in rows:
            d = dict(r)
            print(f" - id={d['id']} sched={d['schedule_id']} channel={d['channel']} offset={d['reminder_offset']} at {d['send_time']}")
    finally:
        conn.close()

if __name__ == '__main__':
    show_notifications(UID)
