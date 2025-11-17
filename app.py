"""
app.py - Flask Main Application cho SmartSchedule.AI
"""

import os

# Nạp biến môi trường từ file .env (nếu có)
try:
    from dotenv import load_dotenv  # optional dependency
    load_dotenv()  # loads .env from project root
except Exception:
    # Fallback: nạp .env thủ công nếu python-dotenv chưa được cài
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        if key and key not in os.environ:
                            os.environ[key] = value
        except Exception:
            pass

from flask import Flask, jsonify, render_template, send_from_directory
from flask_cors import CORS
from routes.auth import auth_bp
from routes.schedule import schedule_bp
from routes.tasks import tasks_bp
from routes.ai_agent import ai_bp
from routes.notify import notify_bp
from routes.import_schedule import import_bp
from routes.stats import stats_bp
from services.websocket_service import init_socketio
from services.notification_service import start_notification_scheduler, set_socketio
from config import current_config, print_config_status
import models

# Khởi tạo Flask app
app = Flask(__name__)

# Load configuration
app.config.from_object(current_config)

# Enable CORS cho frontend
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Initialize SocketIO
socketio = init_socketio(app)

# Set socketio instance cho notification service
set_socketio(socketio)

# Register Blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(schedule_bp, url_prefix='/api/schedule')
app.register_blueprint(tasks_bp, url_prefix='/api/tasks')
app.register_blueprint(ai_bp, url_prefix='/api')
app.register_blueprint(notify_bp, url_prefix='/api/notify')
app.register_blueprint(import_bp, url_prefix='/api/import')
app.register_blueprint(stats_bp, url_prefix='/api/stats')

# Pages
@app.route('/')
def home_page():
    return jsonify({
        'app': 'SmartSchedule.AI',
        'version': '1.0',
        'features': ['auth', 'schedule', 'tasks', 'notifications', 'socketio']
    })

@app.route('/research.html')
def research_page():
    return render_template('research.html')

@app.route('/dashboard.html')
def dashboard_page():
    return render_template('dashboard.html')

@app.route('/tasks.html')
def tasks_page():
    return render_template('tasks.html')

@app.route('/import.html')
def import_page():
    return render_template('import.html')

@app.route('/settings.html')
def settings_page():
    return render_template('settings.html')

@app.route('/statistic.html')
def statistic_page():
    return render_template('statistic.html')

@app.route('/login.html')
def login_page():
    return render_template('auth/login.html')

@app.route('/register.html')
def register_page():
    return render_template('auth/register.html')

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'database': 'connected',
        'modules': {
            'auth': 'ready',
            'schedule': 'ready',
            'tasks': 'ready',
            'ai_agent': 'ready',
            'notifications': 'ready',
            'websocket': 'ready',
            'import': 'ready',
            'stats': 'ready'
        },
        'scheduler_running': current_config.SCHEDULER_ENABLED,
        'config_ok': True
    }), 200


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({'error': 'Internal server error'}), 500


@app.errorhandler(413)
def file_too_large(error):
    """Handle file size exceeded"""
    return jsonify({'error': 'File too large'}), 413

# PWA assets: manifest and service worker
@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory(app.root_path, 'manifest.json')

@app.route('/sw.js')
def serve_sw():
    return send_from_directory(app.root_path, 'sw.js')

@app.route('/@vite/client')
def vite_client_placeholder():
    """Gracefully handle legacy Vite dev client requests"""
    return ('', 204)

@app.route('/@vite/<path:subpath>')
def vite_any_placeholder(subpath):
    """Gracefully handle any legacy Vite dev requests"""
    return ('', 204)

if __name__ == '__main__':
    # Khởi tạo database nếu chưa có
    print("🚀 Starting SmartSchedule.AI Backend (COMPLETE VERSION)...")
    print("="*60)
    models.init_database()
    
    # Print configuration status
    print_config_status()
    
    # Uncomment để thêm dữ liệu mẫu lần đầu
    # models.seed_sample_data()
    
    print("\n✅ ALL BACKEND MODULES READY:")
    print("   ✅ Authentication (JWT)")
    print("   ✅ Schedule Management (CRUD + Conflict Detection)")
    print("   ✅ Task Management (Priority + Status)")
    print("   ✅ AI Chatbot (Groq/HuggingFace/Ollama)")
    print("   ✅ Multi-channel Notifications (Email/Telegram/WebSocket)")
    print("   ✅ APScheduler (Auto-reminders)")
    print("   ✅ WebSocket Realtime (SocketIO)")
    print("   ✅ Import Schedule (Excel/CSV)")
    print("   ✅ Statistics & Analytics")
    
    print("\n📂 File Upload:")
    print(f"   Max size: {current_config.MAX_CONTENT_LENGTH / 1024 / 1024}MB")
    print(f"   Allowed: {', '.join(current_config.ALLOWED_EXTENSIONS)}")
    
    print("\n" + "="*60)
    
    # Start notification scheduler
    if current_config.SCHEDULER_ENABLED:
        # Khởi động trực tiếp (use_reloader=False) để tránh bỏ lỡ tiến trình child
        try:
            start_notification_scheduler(app)
        except Exception as e:
            print(f"⚠️  Failed to start notification scheduler: {e}")
    else:
        print("⚠️  Scheduler disabled in config")
    
    # Allow custom host/port via environment variables
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', '5000'))

    print("\n🌐 Starting Flask + SocketIO server...")
    print(f"   API: http://localhost:{port}/api")
    print(f"   WebSocket: ws://localhost:{port}")
    print(f"   Docs: http://localhost:{port}/")
    print("\n" + "="*60 + "\n")
    
    # Chạy Flask development server với SocketIO
    socketio.run(
        app,
        host=host,
        port=port,
        debug=current_config.DEBUG,
        use_reloader=False  # Tránh scheduler chạy 2 lần khi reload
    )
