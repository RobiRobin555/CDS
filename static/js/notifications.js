// ============================================
// NOTIFICATIONS.JS - WebSocket Real-time Notifications
// ============================================

class NotificationManager {
    constructor() {
        this.socket = null;
        this.notificationQueue = [];
        this.isConnected = false;
    }

    // Initialize WebSocket connection
    connect() {
        const token = localStorage.getItem('jwt_token');
        if(!token) {
            console.log('No token found, skipping WebSocket connection');
            return;
        }

        // Socket.IO client connection
        try {
            this.socket = io(window.location.origin, {
                auth: {
                    token: token
                },
                transports: ['websocket', 'polling']
            });

            this.setupEventListeners();
        } catch(error) {
            console.error('WebSocket connection error:', error);
        }
    }

    // Setup event listeners
    setupEventListeners() {
        if(!this.socket) return;

        this.socket.on('connect', () => {
            console.log('✅ WebSocket connected');
            this.isConnected = true;
            this.processQueue();
        });

        this.socket.on('notification', (data) => {
            this.handleNotification(data);
        });

        this.socket.on('schedule_update', (data) => {
            this.handleScheduleUpdate(data);
        });

        this.socket.on('task_update', (data) => {
            this.handleTaskUpdate(data);
        });

        this.socket.on('disconnect', () => {
            console.log('❌ WebSocket disconnected');
            this.isConnected = false;
        });

        this.socket.on('connect_error', (error) => {
            console.error('Connection error:', error);
            this.isConnected = false;
        });
    }

    // Handle incoming notification
    handleNotification(data) {
        console.log('Notification received:', data);

        // Show in-app notification
        this.showInAppNotification(data.message, data.type || 'info');

        // Update badge count
        this.updateNotificationBadge();

        // Play sound (optional)
        this.playNotificationSound();

        // Update chatbot badge if notification is related
        if(data.type === 'reminder' || data.type === 'deadline') {
            this.updateChatbotBadge();
        }
    }

    // Handle schedule update
    handleScheduleUpdate(data) {
        console.log('Schedule update:', data);

        // Reload calendar if on dashboard
        if(window.location.pathname.includes('dashboard')) {
            if(typeof calendar !== 'undefined' && calendar.refetchEvents) {
                calendar.refetchEvents();
            }
        }

        this.showInAppNotification('📅 Lịch học đã được cập nhật', 'info');
    }

    // Handle task update
    handleTaskUpdate(data) {
        console.log('Task update:', data);

        // Reload tasks if on tasks page
        if(window.location.pathname.includes('tasks')) {
            if(typeof loadTasks === 'function') {
                loadTasks();
            }
        }

        this.showInAppNotification('✅ Nhiệm vụ đã được cập nhật', 'info');
    }

    // Show in-app notification (toast)
    showInAppNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = 'toast-notification';
        
        const icons = {
            info: '💬',
            success: '✅',
            warning: '⚠️',
            error: '❌',
            reminder: '🔔'
        };

        notification.innerHTML = `
            <div class="toast-icon">${icons[type] || '💬'}</div>
            <div class="toast-message">${message}</div>
        `;
        
        notification.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            background: white;
            padding: 1rem 1.5rem;
            border-radius: 0.5rem;
            box-shadow: 0 10px 15px rgba(0,0,0,0.1);
            display: flex;
            gap: 0.75rem;
            align-items: center;
            z-index: 9999;
            animation: slideIn 0.3s ease;
            max-width: 350px;
            border-left: 4px solid var(--primary);
        `;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    }

    // Update notification badge
    updateNotificationBadge() {
        const badge = document.getElementById('notificationBadge');
        if(badge) {
            const currentCount = parseInt(badge.textContent) || 0;
            badge.textContent = currentCount + 1;
            badge.style.display = 'flex';
        }
    }

    // Update chatbot badge
    updateChatbotBadge() {
        const badge = document.getElementById('notificationBadge');
        if(badge) {
            const currentCount = parseInt(badge.textContent) || 0;
            badge.textContent = currentCount + 1;
            badge.style.display = 'flex';
        }
    }

    // Play notification sound (optional)
    playNotificationSound() {
        // Create audio element for notification sound
        // Uncomment to enable sound
        /*
        const audio = new Audio('/static/sounds/notification.mp3');
        audio.volume = 0.5;
        audio.play().catch(e => console.log('Audio play failed:', e));
        */
    }

    // Process queued notifications
    processQueue() {
        while(this.notificationQueue.length > 0) {
            const notification = this.notificationQueue.shift();
            this.showInAppNotification(notification.message, notification.type);
        }
    }

    // Queue notification for later
    queueNotification(message, type = 'info') {
        this.notificationQueue.push({message, type});
    }

    // Disconnect WebSocket
    disconnect() {
        if(this.socket) {
            this.socket.disconnect();
            this.isConnected = false;
        }
    }

    // Send notification (emit to server)
    sendNotification(event, data) {
        if(this.socket && this.isConnected) {
            this.socket.emit(event, data);
        }
    }
}

// Create global notification manager
const notificationManager = new NotificationManager();

// Auto-connect on page load
document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('jwt_token');
    if(token) {
        // Delay connection slightly to ensure page is ready
        setTimeout(() => {
            notificationManager.connect();
        }, 1000);
    }
});

// Disconnect on page unload
window.addEventListener('beforeunload', () => {
    notificationManager.disconnect();
});

// Export for use in other files
if(typeof module !== 'undefined' && module.exports) {
    module.exports = { NotificationManager, notificationManager };
}