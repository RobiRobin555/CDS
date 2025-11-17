"""
services/websocket_service.py - WebSocket với Flask-SocketIO
"""

from flask_socketio import SocketIO, emit, join_room, leave_room
from utils.auth import decode_token

socketio = None

def init_socketio(app):
    """Khởi tạo SocketIO"""
    global socketio
    socketio = SocketIO(app, cors_allowed_origins="*")
    
    # Register event handlers
    register_socketio_events()
    
    print("✅ WebSocket (SocketIO) initialized")
    return socketio


def register_socketio_events():
    """Đăng ký các event handlers"""
    
    @socketio.on('connect')
    def handle_connect():
        """Khi client kết nối"""
        print(f"Client connected: {request.sid}")
        emit('connection_response', {'status': 'connected'})
    
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Khi client ngắt kết nối"""
        print(f"Client disconnected: {request.sid}")
    
    
    @socketio.on('authenticate')
    def handle_authenticate(data):
        """
        Authenticate user với JWT token
        Client gửi: {'token': 'jwt_token_here'}
        """
        token = data.get('token')
        
        if not token:
            emit('auth_error', {'error': 'Token is required'})
            return
        
        payload = decode_token(token)
        
        if 'error' in payload:
            emit('auth_error', {'error': payload['error']})
            return
        
        # Join user vào room riêng (để gửi notification targeted)
        user_id = payload['user_id']
        room = f"user_{user_id}"
        join_room(room)
        
        emit('auth_success', {
            'user_id': user_id,
            'message': 'Authenticated successfully'
        })
        
        print(f"User {user_id} authenticated and joined room {room}")
    
    
    @socketio.on('ping')
    def handle_ping():
        """Heartbeat để giữ connection"""
        emit('pong', {'timestamp': datetime.now().isoformat()})
    
    
    @socketio.on('request_notifications')
    def handle_request_notifications(data):
        """
        Client request danh sách notifications chưa đọc
        """
        from models import get_db
        
        token = data.get('token')
        if not token:
            emit('error', {'error': 'Token required'})
            return
        
        payload = decode_token(token)
        if 'error' in payload:
            emit('error', {'error': 'Invalid token'})
            return
        
        user_id = payload['user_id']
        
        # Lấy notifications từ database
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT n.*, s.subject
                FROM notifications n
                LEFT JOIN schedule s ON n.schedule_id = s.id
                WHERE n.user_id = ?
                AND n.created_at >= datetime('now', '-24 hours')
                ORDER BY n.created_at DESC
                LIMIT 10
            ''', (user_id,))
            
            notifications = cursor.fetchall()
        
        notif_list = []
        for n in notifications:
            notif_list.append({
                'id': n['id'],
                'message': n['message'],
                'subject': n['subject'],
                'created_at': n['created_at']
            })
        
        emit('notifications_list', {
            'count': len(notif_list),
            'notifications': notif_list
        })


# Import cần thiết cho events
from flask import request
from datetime import datetime


def broadcast_notification(user_id, notification_data):
    """
    Broadcast notification đến một user cụ thể
    Được gọi từ notification_service.py
    """
    if socketio:
        room = f"user_{user_id}"
        socketio.emit('notification', notification_data, room=room)
    else:
        print("⚠️  SocketIO not initialized, cannot broadcast")


def broadcast_schedule_update(user_id, schedule_data, action='updated'):
    """
    Thông báo khi có thay đổi lịch học
    action: 'created', 'updated', 'deleted'
    """
    if socketio:
        room = f"user_{user_id}"
        socketio.emit('schedule_update', {
            'action': action,
            'schedule': schedule_data,
            'timestamp': datetime.now().isoformat()
        }, room=room)


def broadcast_task_update(user_id, task_data, action='updated'):
    """
    Thông báo khi có thay đổi task
    """
    if socketio:
        room = f"user_{user_id}"
        socketio.emit('task_update', {
            'action': action,
            'task': task_data,
            'timestamp': datetime.now().isoformat()
        }, room=room)