// ============================================
// UTILITIES - API Client & Helper Functions
// ============================================

const API_BASE_URL = `${window.location.origin}/api`;

class APIClient {
    constructor() {
        this.token = localStorage.getItem('jwt_token');
    }

    // Get auth headers
    getHeaders() {
        const headers = {
            'Content-Type': 'application/json'
        };
        
        if(this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }
        
        return headers;
    }

    // Generic API call
    async request(endpoint, options = {}) {
        try {
            const url = `${API_BASE_URL}${endpoint}`;
            const response = await fetch(url, {
                ...options,
                headers: this.getHeaders()
            });

            let data = null;
            try {
                data = await response.json();
            } catch (_) {
                data = null;
            }

            if (response.status === 401) {
                // Avoid auto-logout for public auth endpoints
                const isAuthEndpoint = endpoint.startsWith('/auth/');
                if (!isAuthEndpoint) {
                    this.logout();
                }
                const msg = (data && (data.error || data.message)) || 'Unauthorized';
                throw new Error(msg);
            }

            if (!response.ok) {
                const msg = (data && (data.error || data.message)) || 'API Error';
                throw new Error(msg);
            }

            return data;
        } catch(error) {
            console.error('API Request Error:', error);
            this.showNotification(error.message || 'Lỗi kết nối server', 'error');
            throw error;
        }
    }

    // ========== AUTH METHODS ==========
    
    async login(email, password) {
        const data = await this.request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password })
        });

        if(data && data.token) {
            this.token = data.token;
            localStorage.setItem('jwt_token', data.token);
            localStorage.setItem('user_name', data.user.name);
            localStorage.setItem('user_email', data.user.email);
        }

        return data;
    }

    async register(name, email, password) {
        return await this.request('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ name, email, password })
        });
    }

    logout() {
        localStorage.removeItem('jwt_token');
        localStorage.removeItem('user_name');
        localStorage.removeItem('user_email');
        window.location.href = '/login.html';
    }

    // ========== SCHEDULE METHODS ==========
    
    async getSchedule(dateRange = null) {
        let endpoint = '/schedule';
        if(dateRange) {
            const startRaw = dateRange.start_date || dateRange.start;
            const endRaw = dateRange.end_date || dateRange.end;
            const normalizeDate = (v) => {
                if(!v) return v;
                const str = String(v);
                // Lấy phần ngày YYYY-MM-DD nếu có thời gian kèm theo
                return str.includes('T') ? str.split('T')[0] : str;
            };
            const start = normalizeDate(startRaw);
            const end = normalizeDate(endRaw);
            const params = new URLSearchParams();
            if(start) params.set('start_date', start);
            if(end) params.set('end_date', end);
            if(dateRange.type) params.set('type', dateRange.type);
            const qs = params.toString();
            if(qs) endpoint += `?${qs}`;
        }
        return await this.request(endpoint);
    }

    async addSchedule(scheduleData) {
        // Normalize payload: datetime format and recurring JSON
        const payload = { ...scheduleData };
        if (payload.start_time && payload.start_time.includes('T')) {
            payload.start_time = payload.start_time.replace('T', ' ');
        }
        if (payload.end_time && payload.end_time.includes('T')) {
            payload.end_time = payload.end_time.replace('T', ' ');
        }
        if (typeof payload.recurring === 'string') {
            const val = payload.recurring.trim().toLowerCase();
            if (!val || val === 'none') {
                payload.recurring = null;
            } else {
                payload.recurring = { frequency: val };
            }
        }
        return await this.request('/schedule', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    }

    async updateSchedule(id, scheduleData) {
        // Normalize payload: datetime format and recurring JSON
        const payload = { ...scheduleData };
        if (payload.start_time && payload.start_time.includes('T')) {
            payload.start_time = payload.start_time.replace('T', ' ');
        }
        if (payload.end_time && payload.end_time.includes('T')) {
            payload.end_time = payload.end_time.replace('T', ' ');
        }
        if (typeof payload.recurring === 'string') {
            const val = payload.recurring.trim().toLowerCase();
            if (!val || val === 'none') {
                payload.recurring = null;
            } else {
                payload.recurring = { frequency: val };
            }
        }
        return await this.request(`/schedule/${id}`, {
            method: 'PUT',
            body: JSON.stringify(payload)
        });
    }

    async deleteSchedule(id) {
        return await this.request(`/schedule/${id}`, {
            method: 'DELETE'
        });
    }

    async checkConflicts(scheduleData) {
        const { start_time, end_time, exclude_id } = scheduleData || {};
        const params = new URLSearchParams();
        if(start_time) params.set('start_time', start_time.includes('T') ? start_time.replace('T', ' ') : start_time);
        if(end_time) params.set('end_time', end_time.includes('T') ? end_time.replace('T', ' ') : end_time);
        if(exclude_id) params.set('exclude_id', exclude_id);
        return await this.request(`/schedule/conflicts?${params.toString()}`, {
            method: 'GET'
        });
    }

    // ========== STATS METHODS ==========
    async getWeeklyStats() {
        try {
            const week = await this.request('/stats/weekly');
            const overview = await this.request('/stats/overview');
            const subjects = await this.request('/stats/subjects');
            return {
                total_classes: week?.week_stats?.total_events || 0,
                total_subjects: subjects?.total_subjects || 0,
                total_hours: week?.week_stats?.total_hours || 0,
                pending_tasks: overview?.overview?.pending_tasks || 0
            };
        } catch (error) {
            throw error;
        }
    }

    // ========== CHATBOT METHODS ==========
    async chat(message, context = null, use_quick_response = true) {
        const payload = { message, use_quick_response };
        if (context) {
            payload.context = context;
        }
        return await this.request('/chat', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    }

    // ========== TASK METHODS ==========
    
    async getTasks() {
        return await this.request('/tasks');
    }

    async addTask(taskData) {
        return await this.request('/tasks', {
            method: 'POST',
            body: JSON.stringify(taskData)
        });
    }

    async updateTask(id, taskData) {
        return await this.request(`/tasks/${id}`, {
            method: 'PUT',
            body: JSON.stringify(taskData)
        });
    }

    async deleteTask(id) {
        return await this.request(`/tasks/${id}`, {
            method: 'DELETE'
        });
    }

    async markComplete(id) {
        return await this.request(`/tasks/${id}/complete`, {
            method: 'POST'
        });
    }

    // ========== HELPERS ==========

    showNotification(message, type = 'info') {
        const container = document.getElementById('notification-container');
        if(!container) return;
        const note = document.createElement('div');
        note.className = `notification ${type}`;
        note.textContent = message;
        container.appendChild(note);
        setTimeout(() => note.remove(), 4000);
    }
}

// Export API client
const api = new APIClient();
window.api = api;

// Date formatting helpers (used by multiple pages)
function pad(n) { return n < 10 ? `0${n}` : `${n}`; }
function formatDate(d) {
    try {
        const dt = new Date(d);
        return `${dt.getFullYear()}-${pad(dt.getMonth()+1)}-${pad(dt.getDate())}`;
    } catch { return d; }
}
function formatTime(d) {
    try {
        const dt = new Date(d);
        return `${pad(dt.getHours())}:${pad(dt.getMinutes())}`;
    } catch { return d; }
}
function formatDateTime(d) {
    try {
        const dt = new Date(d);
        return `${dt.getFullYear()}-${pad(dt.getMonth()+1)}-${pad(dt.getDate())} ${pad(dt.getHours())}:${pad(dt.getMinutes())}`;
    } catch { return d; }
}

// Restore global helpers expected by pages
function checkAuth() {
    const token = localStorage.getItem('jwt_token');
    const publicPages = ['/login.html', '/register.html', '/'];
    const currentPage = window.location.pathname;
    if(!token && !publicPages.some(page => currentPage.includes(page) || currentPage === '/')) {
        window.location.href = '/login.html';
    }
}

// expose helpers to window for non-module scripts
window.formatDate = formatDate;
window.formatTime = formatTime;
window.formatDateTime = formatDateTime;
window.checkAuth = checkAuth;

// exports removed for non-module usage
