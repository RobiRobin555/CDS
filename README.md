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

## 📝 5. License
© 2025 AIoTLab, Faculty of Information Technology, DaiNam University. All rights reserved.

---
