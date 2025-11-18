<h2 align="center">
    <a href="https://dainam.edu.vn/vi/khoa-cong-nghe-thong-tin">
    🎓 Faculty of Information Technology (DaiNam University)
    </a>
</h2>
<h2 align="center">
   SmartSchedule.AI
</h2>
<div align="center">
    <p align="center">
        <img src="docs/aiotlab_logo.png" alt="AIoTLab Logo" width="170"/>
        <img src="docs/fitdnu_logo.png" alt="FIT DNU Logo" width="180"/>
        <img src="docs/dnu_logo.png" alt="DaiNam University Logo" width="200"/>
    </p>

[![AIoTLab](https://img.shields.io/badge/AIoTLab-green?style=for-the-badge)](https://www.facebook.com/DNUAIoTLab)
[![Faculty of Information Technology](https://img.shields.io/badge/Faculty%20of%20Information%20Technology-blue?style=for-the-badge)](https://dainam.edu.vn/vi/khoa-cong-nghe-thong-tin)
[![DaiNam University](https://img.shields.io/badge/DaiNam%20University-orange?style=for-the-badge)](https://dainam.edu.vn)

</div>

## 📖 1. Giới thiệu
SmartSchedule.AI là hệ thống quản lý lịch thông minh tích hợp các chức năng xác thực người dùng, quản lý lịch và công việc, nhắc việc đa kênh, realtime qua WebSocket và chatbot AI. Hệ thống cung cấp API backend (Flask + Socket.IO) cùng giao diện tối giản để nghiên cứu và triển khai nhanh trong môi trường học thuật.

## 🔧 2. Công nghệ sử dụng
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.x-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Socket.IO](https://img.shields.io/badge/Socket.IO-4.x-010101?style=for-the-badge&logo=socket.io&logoColor=white)](https://socket.io/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org/)
[![APScheduler](https://img.shields.io/badge/APScheduler-active-4f46e5?style=for-the-badge)](https://apscheduler.readthedocs.io/)
[![JWT](https://img.shields.io/badge/JWT-Auth-990000?style=for-the-badge&logo=jsonwebtokens&logoColor=white)](https://jwt.io/)

## 🚀 3. Tính năng chính
- Xác thực người dùng JWT, đăng nhập/đăng ký (`routes/auth.py`)
- Quản lý lịch biểu với phát hiện xung đột (`routes/schedule.py`, `utils/conflict_detector.py`)
- Quản lý công việc: ưu tiên, trạng thái (`routes/tasks.py`)
- Chatbot AI tích hợp Groq/HF/Ollama (`routes/ai_agent.py`)
- Nhắc việc đa kênh: Email/Telegram/WebSocket (`services/notification_service.py`)
- Realtime qua Socket.IO (`services/websocket_service.py`)
- Import lịch từ Excel/CSV (`routes/import_schedule.py`)
- Thống kê & phân tích (`routes/stats.py`)
- API Healthcheck (`/api/health`) và xử lý lỗi chuẩn (`app.py`)

## 📂 4. Cấu trúc thư mục
- `app.py`: Khởi tạo Flask, Socket.IO, đăng ký blueprint và server
- `routes/`: API cho auth, schedule, tasks, ai, notify, import, stats
- `services/`: Dịch vụ WebSocket và Notification Scheduler
- `templates/` + `static/`: Giao diện HTML/CSS/JS tối giản
- `utils/`: Tiện ích xác thực, AI helper, parse file, validator
- `models.py`: Khởi tạo DB và seed dữ liệu mẫu
- `config.py`: Cấu hình hệ thống, CORS, upload, scheduler


## 🛠️ 55. Cài đặt & Chạy
- Yêu cầu: `Python >= 3.11`, SQLite tích hợp sẵn
- Tạo môi trường ảo và cài thư viện:
  - `python -m venv .venv`
  - `.venv\Scripts\Activate`
  - `pip install flask flask-cors flask-socketio apscheduler python-dotenv requests werkzeug`
- Khởi tạo CSDL và chạy server:
  - `python app.py`
- Biến môi trường quan trọng (đặt trong môi trường hệ thống hoặc file `.env` cục bộ):
  - `FLASK_ENV=development`
  - `DATABASE_PATH=smartschedule.db`
  - `JWT_SECRET_KEY=<random-hex>`
  - `SMTP_EMAIL=<your-email>`
  - `SMTP_PASSWORD=<your-app-password>`
  - `TELEGRAM_BOT_TOKEN=<bot-token>`
  - `LLM_PROVIDER=groq|huggingface|ollama`
  - `GROQ_API_KEY` hoặc `HF_API_KEY` tùy provider
  - Lưu ý: Không commit các khóa bí mật lên GitHub.

## 🗄️ 6. Schema CSDL (SQLite)
```sql
-- users
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  telegram_id TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- schedule
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
);

-- tasks
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
);

-- notifications
CREATE TABLE IF NOT EXISTS notifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  schedule_id INTEGER,
  message TEXT NOT NULL,
  send_time DATETIME NOT NULL,
  sent BOOLEAN DEFAULT 0,
  channel TEXT DEFAULT 'email',
  reminder_offset INTEGER,
  event_type TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY(schedule_id) REFERENCES schedule(id) ON DELETE CASCADE
);

-- chat_history
CREATE TABLE IF NOT EXISTS chat_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  user_msg TEXT NOT NULL,
  ai_reply TEXT NOT NULL,
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- notification_settings
CREATE TABLE IF NOT EXISTS notification_settings (
  user_id INTEGER PRIMARY KEY,
  email_enabled BOOLEAN DEFAULT 1,
  telegram_enabled BOOLEAN DEFAULT 0,
  in_app_enabled BOOLEAN DEFAULT 1,
  email_reminder_offset INTEGER DEFAULT 30,
  telegram_reminder_offset INTEGER DEFAULT 30,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- indexes
CREATE INDEX IF NOT EXISTS idx_schedule_user ON schedule(user_id);
CREATE INDEX IF NOT EXISTS idx_schedule_time ON schedule(start_time, end_time);
CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_schedule_offset ON notifications(schedule_id, reminder_offset);
```

## 🏗️ 7. Kiến trúc hệ thống
- API Backend: Flask Blueprints `routes/*` cho auth, schedule, tasks, ai, notify, import, stats
- Dịch vụ nền: APScheduler gửi nhắc việc đa kênh `services/notification_service.py`
- Realtime: Flask-SocketIO `services/websocket_service.py` phát sự kiện tới từng người dùng
- Tầng tiện ích: `utils/*` xử lý xác thực JWT, AI helper, parse file, validator, phát hiện xung đột
- Dữ liệu: SQLite `smartschedule.db` khởi tạo bởi `models.init_database()`
- Giao diện: `templates/*` và `static/*` (HTML/CSS/JS) tối giản phục vụ nghiên cứu
## 📝 8. License
© 2025 AIoTLab, Faculty of Information Technology, DaiNam University. All rights reserved.

---
