"""
config.py - Application Configuration Management
"""

import os
from datetime import timedelta

class Config:
    """Base configuration"""
    
    # Flask
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    JSON_AS_ASCII = False
    JSON_SORT_KEYS = False
    
    # Database
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'smartschedule.db')
    
    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ALGORITHM = 'HS256'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    
    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')
    
    # LLM Configuration
    LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'groq')  # groq/huggingface/ollama
    
    # Groq API
    GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
    GROQ_MODEL = os.getenv('GROQ_MODEL', 'openai/gpt-oss-120b')
    
    # Hugging Face API
    HF_API_KEY = os.getenv('HF_API_KEY', '')
    HF_MODEL = os.getenv('HF_MODEL', 'mistralai/Mixtral-8x7B-Instruct-v0.1')
    
    # Ollama
    OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')
    OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3')
    
    # Email Configuration
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SMTP_EMAIL = os.getenv('SMTP_EMAIL', '')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
    SMTP_USE_TLS = os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_WEBHOOK_URL = os.getenv('TELEGRAM_WEBHOOK_URL', '')
    
    # APScheduler
    SCHEDULER_ENABLED = os.getenv('SCHEDULER_ENABLED', 'true').lower() == 'true'
    SCHEDULER_INTERVAL_MINUTES = int(os.getenv('SCHEDULER_INTERVAL_MINUTES', 5))
    REMINDER_CHECK_WINDOW = int(os.getenv('REMINDER_CHECK_WINDOW', 5))  # phút
    
    # WebSocket
    SOCKETIO_MESSAGE_QUEUE = os.getenv('SOCKETIO_MESSAGE_QUEUE', None)
    SOCKETIO_ASYNC_MODE = os.getenv('SOCKETIO_ASYNC_MODE', 'threading')
    
    # File Upload
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'pdf', 'csv'}
    
    # Rate Limiting
    RATE_LIMIT_ENABLED = os.getenv('RATE_LIMIT_ENABLED', 'false').lower() == 'true'
    RATE_LIMIT_DEFAULT = os.getenv('RATE_LIMIT_DEFAULT', '100/hour')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'app.log')


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # Override với config an toàn hơn
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'https://yourdomain.com').split(',')
    RATE_LIMIT_ENABLED = True


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DATABASE_PATH = ':memory:'  # Use in-memory database
    SCHEDULER_ENABLED = False


# Config dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config():
    """Get current configuration based on FLASK_ENV"""
    env = os.getenv('FLASK_ENV', 'development')
    return config.get(env, config['default'])


# Export for easy import
current_config = get_config()


def validate_config():
    """Validate critical configuration"""
    warnings = []
    errors = []
    
    # Check LLM API keys
    if current_config.LLM_PROVIDER == 'groq' and not current_config.GROQ_API_KEY:
        warnings.append("⚠️  GROQ_API_KEY not set - AI Chatbot will not work")
    
    if current_config.LLM_PROVIDER == 'huggingface' and not current_config.HF_API_KEY:
        warnings.append("⚠️  HF_API_KEY not set - AI Chatbot will not work")
    
    # Check Email config
    if not current_config.SMTP_EMAIL or not current_config.SMTP_PASSWORD:
        warnings.append("⚠️  SMTP credentials not set - Email notifications disabled")
    
    # Check Telegram
    if not current_config.TELEGRAM_BOT_TOKEN:
        warnings.append("⚠️  TELEGRAM_BOT_TOKEN not set - Telegram notifications disabled")
    
    # Check Secret Key
    if current_config.SECRET_KEY == 'dev-secret-key-change-in-production':
        if os.getenv('FLASK_ENV') == 'production':
            errors.append("❌ SECRET_KEY must be changed in production!")
        else:
            warnings.append("⚠️  Using default SECRET_KEY - Change in production")
    
    return warnings, errors


def print_config_status():
    """Print configuration status"""
    print("\n" + "="*60)
    print("📋 CONFIGURATION STATUS")
    print("="*60)
    
    print(f"\n🔧 Environment: {os.getenv('FLASK_ENV', 'development')}")
    print(f"🗄️  Database: {current_config.DATABASE_PATH}")
    print(f"🤖 LLM Provider: {current_config.LLM_PROVIDER}")
    print(f"📧 Email: {'✅ Configured' if current_config.SMTP_EMAIL else '❌ Not configured'}")
    print(f"💬 Telegram: {'✅ Configured' if current_config.TELEGRAM_BOT_TOKEN else '❌ Not configured'}")
    print(f"⏰ Scheduler: {'✅ Enabled' if current_config.SCHEDULER_ENABLED else '❌ Disabled'}")
    
    warnings, errors = validate_config()
    
    if errors:
        print("\n❌ ERRORS:")
        for error in errors:
            print(f"   {error}")
    
    if warnings:
        print("\n⚠️  WARNINGS:")
        for warning in warnings:
            print(f"   {warning}")
    
    if not errors and not warnings:
        print("\n✅ All configurations OK!")
    
    print("="*60 + "\n")


if __name__ == '__main__':
    print_config_status()
