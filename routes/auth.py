"""
routes/auth.py - API endpoints cho Authentication
"""

from flask import Blueprint, request, jsonify
from models import get_db
from utils.auth import (
    hash_password, 
    verify_password, 
    generate_token,
    validate_email,
    validate_password_strength,
    token_required
)
from utils.validators import validate_name, validate_telegram_id

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Đăng ký tài khoản mới
    
    Request Body:
    {
        "name": "Nguyen Van A",
        "email": "student@example.com",
        "password": "password123"
    }
    """
    data = request.get_json()
    
    # Validate input
    if not data or not all(k in data for k in ['name', 'email', 'password']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    name = data['name'].strip()
    email = data['email'].strip().lower()
    password = data['password']
    
    # Validate email
    if not validate_email(email):
        return jsonify({'error': 'Invalid email format'}), 400
    
    # Validate password strength
    is_valid, msg = validate_password_strength(password)
    if not is_valid:
        return jsonify({'error': msg}), 400
    
    # Kiểm tra email đã tồn tại chưa
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
        if cursor.fetchone():
            return jsonify({'error': 'Email already exists'}), 409
        
        # Hash password và tạo user
        password_hash = hash_password(password)
        
        cursor.execute('''
            INSERT INTO users (name, email, password_hash)
            VALUES (?, ?, ?)
        ''', (name, email, password_hash))
        
        user_id = cursor.lastrowid
        
        # Tạo notification settings mặc định
        cursor.execute('''
            INSERT INTO notification_settings (user_id)
            VALUES (?)
        ''', (user_id,))
    
    # Tạo JWT token
    token = generate_token(user_id, email)
    
    return jsonify({
        'success': True,
        'message': 'User registered successfully',
        'user': {
            'id': user_id,
            'name': name,
            'email': email
        },
        'token': token
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Đăng nhập
    
    Request Body:
    {
        "email": "student@example.com",
        "password": "password123"
    }
    """
    data = request.get_json()
    
    if not data or not all(k in data for k in ['email', 'password']):
        return jsonify({'error': 'Missing email or password'}), 400
    
    email = data['email'].strip().lower()
    password = data['password']
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, email, password_hash 
            FROM users 
            WHERE email = ?
        ''', (email,))
        
        user = cursor.fetchone()
        
        if not user:
            return jsonify({'error': 'Invalid email or password'}), 401
        
        # Kiểm tra password
        if not verify_password(user['password_hash'], password):
            return jsonify({'error': 'Invalid email or password'}), 401
    
    # Tạo JWT token
    token = generate_token(user['id'], user['email'])
    
    return jsonify({
        'message': 'Login successful',
        'user': {
            'id': user['id'],
            'name': user['name'],
            'email': user['email']
        },
        'token': token
    }), 200


@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user(current_user):
    """
    Lấy thông tin user hiện tại (từ token)
    
    Headers:
        Authorization: Bearer <token>
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, email, telegram_id, created_at
            FROM users
            WHERE id = ?
        ''', (current_user['user_id'],))
        
        user = cursor.fetchone()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'user': {
            'id': user['id'],
            'name': user['name'],
            'email': user['email'],
            'telegram_id': user['telegram_id'],
            'created_at': user['created_at']
        }
    }), 200


@auth_bp.route('/update-profile', methods=['PUT'])
@token_required
def update_profile(current_user):
    """
    Cập nhật thông tin profile
    
    Request Body:
    {
        "name": "New Name",
        "telegram_id": "123456789"
    }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    allowed_fields = ['name', 'telegram_id']
    updates = {k: v for k, v in data.items() if k in allowed_fields}
    
    if not updates:
        return jsonify({'error': 'No valid fields to update'}), 400
    
    # Validate fields
    if 'name' in updates:
        ok, msg = validate_name(updates['name'])
        if not ok:
            return jsonify({'error': msg}), 400
    if 'telegram_id' in updates:
        ok, msg = validate_telegram_id(updates['telegram_id'])
        if not ok:
            return jsonify({'error': msg}), 400

    # Build dynamic UPDATE query
    set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
    values = list(updates.values()) + [current_user['user_id']]
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute(f'''
            UPDATE users
            SET {set_clause}
            WHERE id = ?
        ''', values)
    
    return jsonify({
        'message': 'Profile updated successfully',
        'updated_fields': list(updates.keys())
    }), 200


@auth_bp.route('/change-password', methods=['PUT'])
@token_required
def change_password(current_user):
    """
    Đổi mật khẩu
    
    Request Body:
    {
        "old_password": "oldpass123",
        "new_password": "newpass123"
    }
    """
    data = request.get_json()
    
    if not data or not all(k in data for k in ['old_password', 'new_password']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    old_password = data['old_password']
    new_password = data['new_password']
    
    # Validate new password strength
    is_valid, msg = validate_password_strength(new_password)
    if not is_valid:
        return jsonify({'error': msg}), 400
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Lấy password hash hiện tại
        cursor.execute('''
            SELECT password_hash FROM users WHERE id = ?
        ''', (current_user['user_id'],))
        
        user = cursor.fetchone()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Verify old password
        if not verify_password(user['password_hash'], old_password):
            return jsonify({'error': 'Old password is incorrect'}), 401
        
        # Update password
        new_password_hash = hash_password(new_password)
        
        cursor.execute('''
            UPDATE users
            SET password_hash = ?
            WHERE id = ?
        ''', (new_password_hash, current_user['user_id']))
    
    return jsonify({'message': 'Password changed successfully'}), 200


@auth_bp.route('/delete-account', methods=['DELETE'])
@token_required
def delete_account(current_user):
    """
    Xóa tài khoản người dùng (yêu cầu xác nhận mật khẩu)

    Request Body:
    {
        "password": "current_password"
    }
    """
    data = request.get_json() or {}
    password = data.get('password')
    if not password:
        return jsonify({'error': 'Password is required'}), 400

    user_id = current_user['user_id']

    with get_db() as conn:
        cursor = conn.cursor()
        # Lấy password hash hiện tại
        cursor.execute('SELECT password_hash FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({'error': 'User not found'}), 404

        # Xác thực mật khẩu
        if not verify_password(row['password_hash'], password):
            return jsonify({'error': 'Password is incorrect'}), 401

        # Xóa dữ liệu liên quan trước (đảm bảo sạch ngay cả khi PRAGMA foreign_keys tắt)
        cursor.execute('DELETE FROM notifications WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM tasks WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM schedule WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM chat_history WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM notification_settings WHERE user_id = ?', (user_id,))

        # Cuối cùng xóa user
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))

    return jsonify({'message': 'Account deleted successfully'}), 200
