import sqlite3
from datetime import datetime
from contextlib import contextmanager

DATABASE_PATH = 'smartschedule.db'

@contextmanager
def get_db():
    """Context manager để quản lý database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Trả về dict thay vì tuple
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def init_database():
    """Khởi tạo database với tất cả các bảng"""
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. Bảng Users
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            telegram_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 2. Bảng Schedule (Lịch học)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            description TEXT,
            start_time DATETIME NOT NULL,
            end_time DATETIME NOT NULL,
            location TEXT,
            type TEXT DEFAULT 'class',
            recurring TEXT,
            color TEXT DEFAULT '#3788d8',
            reminder_time INTEGER DEFAULT 30,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        ''')
        
        # 3. Bảng Tasks (Nhiệm vụ)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            due_date DATETIME,
            priority TEXT DEFAULT 'medium',
            status TEXT DEFAULT 'pending',
            related_schedule_id INTEGER,
            completed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(related_schedule_id) REFERENCES schedule(id) ON DELETE SET NULL
        )
        ''')
        
        # 4. Bảng Notifications (Nhắc nhở)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            schedule_id INTEGER,
            message TEXT NOT NULL,
            send_time DATETIME NOT NULL,
            sent BOOLEAN DEFAULT 0,
            channel TEXT DEFAULT 'email',
            -- NEW: lưu mốc nhắc nhở (phút). Ví dụ: 60, 30, 1440, 4320, 10080
            reminder_offset INTEGER,
            -- NEW: loại sự kiện (class/exam)
            event_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(schedule_id) REFERENCES schedule(id) ON DELETE CASCADE
        )
        ''')

        # Đảm bảo các cột mới tồn tại nếu DB đã được tạo trước đó
        try:
            cursor.execute("PRAGMA table_info(notifications)")
            cols = [row[1] for row in cursor.fetchall()]
            if 'reminder_offset' not in cols:
                cursor.execute("ALTER TABLE notifications ADD COLUMN reminder_offset INTEGER")
            if 'event_type' not in cols:
                cursor.execute("ALTER TABLE notifications ADD COLUMN event_type TEXT")
        except Exception:
            # Bỏ qua nếu không thể ALTER (ví dụ cột đã tồn tại)
            pass
        
        # 5. Bảng Chat History
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            user_msg TEXT NOT NULL,
            ai_reply TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        ''')
        
        # 6. Bảng Notification Settings
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS notification_settings (
            user_id INTEGER PRIMARY KEY,
            email_enabled BOOLEAN DEFAULT 1,
            telegram_enabled BOOLEAN DEFAULT 0,
            in_app_enabled BOOLEAN DEFAULT 1,
            -- NEW: Thời gian nhắc nhở cho từng kênh (phút)
            email_reminder_offset INTEGER DEFAULT 30,
            telegram_reminder_offset INTEGER DEFAULT 30,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        ''')

        # Cập nhật bảng notification_settings nếu DB đã tồn tại
        try:
            cursor.execute("PRAGMA table_info(notification_settings)")
            cols = [row[1] for row in cursor.fetchall()]
            if 'email_reminder_offset' not in cols:
                cursor.execute("ALTER TABLE notification_settings ADD COLUMN email_reminder_offset INTEGER DEFAULT 30")
            if 'telegram_reminder_offset' not in cols:
                cursor.execute("ALTER TABLE notification_settings ADD COLUMN telegram_reminder_offset INTEGER DEFAULT 30")
            
            # Xóa cột cũ nếu tồn tại
            if 'default_reminder_time' in cols:
                 # Tạo bảng tạm
                cursor.execute('''
                    CREATE TABLE notification_settings_new (
                        user_id INTEGER PRIMARY KEY,
                        email_enabled BOOLEAN,
                        telegram_enabled BOOLEAN,
                        in_app_enabled BOOLEAN,
                        email_reminder_offset INTEGER,
                        telegram_reminder_offset INTEGER,
                        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                    )
                ''')
                # Sao chép dữ liệu, sử dụng giá trị từ cột cũ làm mặc định
                cursor.execute('''
                    INSERT INTO notification_settings_new (user_id, email_enabled, telegram_enabled, in_app_enabled, email_reminder_offset, telegram_reminder_offset)
                    SELECT user_id, email_enabled, telegram_enabled, in_app_enabled, default_reminder_time, default_reminder_time
                    FROM notification_settings
                ''')
                # Xóa bảng cũ và đổi tên bảng mới
                cursor.execute('DROP TABLE notification_settings')
                cursor.execute('ALTER TABLE notification_settings_new RENAME TO notification_settings')
                print("✅ Migrated notification_settings table successfully!")

        except Exception as e:
            print(f"⚠️  Could not migrate notification_settings table: {e}")
            pass

        
        # Tạo indexes để tăng tốc query
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_schedule_user ON schedule(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_schedule_time ON schedule(start_time, end_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_notifications_schedule_offset ON notifications(schedule_id, reminder_offset)')
        
        print("✅ Database initialized successfully!")
        print(f"📁 Database file: {DATABASE_PATH}")


def seed_sample_data():
    """Thêm dữ liệu mẫu để test"""
    from werkzeug.security import generate_password_hash
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Thêm user mẫu
        password_hash = generate_password_hash('password123')
        cursor.execute('''
            INSERT OR IGNORE INTO users (name, email, password_hash)
            VALUES (?, ?, ?)
        ''', ('Nguyen Van A', 'test@example.com', password_hash))
        
        user_id = cursor.lastrowid
        
        # Thêm notification settings mặc định
        cursor.execute('''
            INSERT OR IGNORE INTO notification_settings (user_id)
            VALUES (?)
        ''', (user_id,))
        
        # Thêm lịch mẫu
        cursor.execute('''
            INSERT INTO schedule 
            (user_id, subject, start_time, end_time, location, type, color)
            VALUES 
            (?, 'Toán Cao Cấp', '2025-10-20 08:00:00', '2025-10-20 10:00:00', 'Phòng A101', 'class', '#FF5733'),
            (?, 'Lập Trình Python', '2025-10-20 14:00:00', '2025-10-20 16:00:00', 'Phòng B205', 'class', '#3788d8')
        ''', (user_id, user_id))
        
        # Thêm task mẫu
        cursor.execute('''
            INSERT INTO tasks 
            (user_id, title, description, due_date, priority, status)
            VALUES 
            (?, 'Nộp bài tập Toán', 'Bài tập chương 3', '2025-10-25 23:59:00', 'high', 'pending'),
            (?, 'Đọc tài liệu Flask', 'Chương 1-3', '2025-10-22 23:59:00', 'medium', 'pending')
        ''', (user_id, user_id))
        
        print("✅ Sample data inserted!")
        print(f"   Email: test@example.com")
        print(f"   Password: password123")


if __name__ == '__main__':
    print("🚀 Initializing SmartSchedule.AI Database...")
    init_database()
    
