"""
utils/auth.py - JWT Authentication và Password Hashing
"""

# Use PyJWT package
import jwt as pyjwt
import datetime
from functools import wraps
from flask import request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

# Secret key cho JWT - NÊN LƯU Ở BIẾN MÔI TRƯỜNG
SECRET_KEY = 'your-secret-key-change-this-in-production'
JWT_ALGORITHM = 'HS256'
TOKEN_EXPIRE_HOURS = 24


def hash_password(password):
    """Mã hóa mật khẩu"""
    return generate_password_hash(password, method='pbkdf2:sha256')


def verify_password(password_hash, password):
    """Kiểm tra mật khẩu có khớp không"""
    return check_password_hash(password_hash, password)


def generate_token(user_id, email):
    """Tạo JWT token"""
    payload = {
        'user_id': user_id,
        'email': email,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=TOKEN_EXPIRE_HOURS),
        'iat': datetime.datetime.utcnow()
    }
    token = pyjwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)
    # Ensure token is returned as string
    if isinstance(token, bytes):
        return token.decode('utf-8')
    return token


def decode_token(token):
    """Giải mã JWT token"""
    try:
        payload = pyjwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except pyjwt.ExpiredSignatureError:
        return {'error': 'Token expired'}
    except pyjwt.InvalidTokenError:
        return {'error': 'Invalid token'}


def token_required(f):
    """
    Decorator để bảo vệ route - yêu cầu JWT token
    
    Usage:
        @app.route('/api/protected')
        @token_required
        def protected_route(current_user):
            return jsonify({'user': current_user})
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Lấy token từ header Authorization
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                # Format: "Bearer <token>"
                token = auth_header.split(' ')[1]
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        # Giải mã token
        payload = decode_token(token)
        
        if 'error' in payload:
            return jsonify({'error': payload['error']}), 401
        
        # Truyền thông tin user vào function
        current_user = {
            'user_id': payload['user_id'],
            'email': payload['email']
        }
        
        return f(current_user, *args, **kwargs)
    
    return decorated


def validate_email(email):
    """Kiểm tra email hợp lệ"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password_strength(password):
    """
    Kiểm tra độ mạnh mật khẩu
    Yêu cầu: ít nhất 8 ký tự
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    
    # Có thể thêm các rule khác:
    # - Ít nhất 1 chữ hoa
    # - Ít nhất 1 số
    # - Ít nhất 1 ký tự đặc biệt
    
    return True, "Password is valid"