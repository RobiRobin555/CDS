// ============================================
// CHATBOT.JS - AI Chatbot Integration
// ============================================

let isChatbotOpen = false;
let historyLoaded = false;
let chatContext = {
    upcomingSchedules: [],
    pendingTasks: []
};

document.addEventListener('DOMContentLoaded', function() {
    loadChatContext();
    
    // Refresh context every 5 minutes
    setInterval(loadChatContext, 5 * 60 * 1000);
    
    // Setup event listeners
    setupChatbot();

    // Load AI suggestions từ backend
    loadAISuggestions();

    // Bind nút xóa lịch sử nếu có
    const clearBtn = document.getElementById('clearChatBtn');
    if (clearBtn) {
        clearBtn.addEventListener('click', clearChatHistory);
    }
});

// Load context for AI
async function loadChatContext() {
    try {
        const today = new Date().toISOString().split('T')[0];
        const nextWeek = new Date();
        nextWeek.setDate(nextWeek.getDate() + 7);
        
        const scheduleData = await api.getSchedule({
            start: today,
            end: nextWeek.toISOString().split('T')[0]
        });
        
        const taskData = await api.getTasks();
        
        chatContext.upcomingSchedules = scheduleData.schedules || [];
        chatContext.pendingTasks = taskData.tasks?.filter(t => t.status !== 'completed') || [];

        // Render dynamic subject suggestions based on upcoming schedules
        renderDynamicSubjectSuggestions();
    } catch(error) {
        console.error('Error loading chat context:', error);
    }
}

// Setup chatbot
function setupChatbot() {
    const chatInput = document.getElementById('chatInput');
    if(!chatInput) return;

    // Auto-resize textarea
    chatInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 100) + 'px';
    });

    // Handle Enter key
    chatInput.addEventListener('keydown', function(e) {
        if(e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
}

// Toggle chatbot
function toggleChatbot() {
    const chatbotWindow = document.getElementById('chatbotWindow');
    const chatbotButton = document.getElementById('chatbotButton');
    const badge = document.getElementById('notificationBadge');
    
    isChatbotOpen = !isChatbotOpen;
    
    if(isChatbotOpen) {
        chatbotWindow.classList.add('active');
        chatbotButton.classList.add('active');
        if(badge) badge.style.display = 'none';
        scrollToBottom();
        document.getElementById('chatInput')?.focus();

        // Load lịch sử chat lần đầu khi mở
        if (!historyLoaded) {
            loadChatHistory();
            historyLoaded = true;
        }
    } else {
        chatbotWindow.classList.remove('active');
        chatbotButton.classList.remove('active');
    }
}

// Send message
async function sendMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    
    if(!message) return;

    // Add user message
    addMessage(message, 'user');
    input.value = '';
    input.style.height = 'auto';

    // Show typing indicator
    showTypingIndicator();

    try {
        // Call AI API with context
        const response = await api.chat(message, {
            schedules: chatContext.upcomingSchedules.slice(0, 5),
            tasks: chatContext.pendingTasks.slice(0, 5)
        });
        
        hideTypingIndicator();
        
        if(response && response.reply) {
            addMessage(response.reply, 'bot');
        } else {
            addMessage('Xin lỗi, tôi không thể xử lý câu hỏi này lúc này.', 'bot');
        }
        
        // Hiển thị gợi ý lịch nếu có
        if (response && Array.isArray(response.suggestions) && response.suggestions.length > 0) {
            showSuggestionCards(response.suggestions, response.cta || 'Nhấn "Thêm" để tạo lịch');
        }
        
    } catch(error) {
        console.error('Chat error:', error);
        hideTypingIndicator();
        addMessage('Xin lỗi, tôi đang gặp sự cố. Vui lòng thử lại sau.', 'bot');
    }
}

// ========== NEW: Load chat history ==========
async function loadChatHistory(limit = 20) {
    try {
        const res = await api.request(`/chat/history?limit=${limit}`);
        const history = res && Array.isArray(res.history) ? res.history : [];
        // Render oldest first
        history.reverse().forEach(item => {
            if (item.user_message) addMessage(item.user_message, 'user');
            if (item.ai_reply) addMessage(item.ai_reply, 'bot');
        });
    } catch (err) {
        console.warn('Cannot load chat history:', err);
    }
}

// ========== NEW: Load AI suggestions ==========
async function loadAISuggestions() {
    try {
        const res = await api.request('/suggestions');
        const suggestions = Array.isArray(res?.suggestions) ? res.suggestions : [];
        renderAISuggestions(suggestions);
    } catch (err) {
        console.warn('loadAISuggestions error:', err);
    }
}

function renderAISuggestions(suggestions) {
    const container = document.getElementById('aiSuggestions');
    if (container) {
        container.innerHTML = '';
        suggestions.slice(0, 5).forEach(text => {
            const btn = document.createElement('button');
            btn.className = 'quick-action-btn';
            btn.textContent = text;
            btn.onclick = () => sendQuickMessage(text);
            container.appendChild(btn);
        });
        return;
    }

    // Fallback: show as a bot message chips
    if (!suggestions.length) return;
    const messagesContainer = document.getElementById('chatMessages');
    if (!messagesContainer) return;
    const time = new Date().toLocaleTimeString('vi-VN', {hour: '2-digit', minute: '2-digit'});
    const wrap = document.createElement('div');
    wrap.className = 'message bot';
    wrap.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-content">
            <div class="message-bubble">
                <div style="margin-bottom:8px;font-weight:600;">Gợi ý câu hỏi nhanh</div>
                <div id="aiSuggestionChips" style="display:flex;flex-wrap:wrap;gap:8px;"></div>
            </div>
            <div class="message-time">${time}</div>
        </div>
    `;
    messagesContainer.appendChild(wrap);
    const chips = wrap.querySelector('#aiSuggestionChips');
    suggestions.slice(0, 5).forEach(text => {
        const chip = document.createElement('button');
        chip.className = 'btn-secondary';
        chip.style.padding = '6px 10px';
        chip.textContent = text;
        chip.onclick = () => sendQuickMessage(text);
        chips.appendChild(chip);
    });
    scrollToBottom();
}

// ========== NEW: Clear chat history ==========
async function clearChatHistory() {
    try {
        if (!confirm('Bạn có chắc chắn muốn xóa toàn bộ lịch sử chat?')) return;
        await api.request('/chat/clear', { method: 'DELETE' });
        const messagesContainer = document.getElementById('chatMessages');
        if (messagesContainer) messagesContainer.innerHTML = '';
        historyLoaded = false;
        addMessage('✅ Đã xóa lịch sử chat.', 'bot');
    } catch (err) {
        console.error('Clear chat history error:', err);
        addMessage('Không thể xóa lịch sử chat. Vui lòng thử lại.', 'bot');
    }
}

// Render dynamic suggestions for subjects
function renderDynamicSubjectSuggestions() {
    try {
        const container = document.getElementById('dynamicSuggestions');
        if (!container) return;

        // Build a unique subject list from upcoming schedules
        const subjectsSet = new Set();
        (chatContext.upcomingSchedules || []).forEach(s => {
            if (s && s.subject) subjectsSet.add(s.subject);
        });

        // Clear previous suggestions
        container.innerHTML = '';

        const subjects = Array.from(subjectsSet).slice(0, 3);
        subjects.forEach(subj => {
            const btn = document.createElement('button');
            btn.className = 'quick-action-btn';
            btn.textContent = `🔎 Thông tin môn ${subj}`;
            btn.onclick = () => sendQuickMessage(`Thông tin môn ${subj}`);
            container.appendChild(btn);
        });
    } catch (e) {
        console.warn('renderDynamicSubjectSuggestions error:', e);
    }
}

// Send quick message
function sendQuickMessage(message) {
    document.getElementById('chatInput').value = message;
    sendMessage();
}

// Add message to chat
function addMessage(text, sender) {
    const messagesContainer = document.getElementById('chatMessages');
    if(!messagesContainer) return;

    const time = new Date().toLocaleTimeString('vi-VN', {hour: '2-digit', minute: '2-digit'});
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    
    const avatar = sender === 'bot' ? '🤖' : '👤';
    
    messageDiv.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            <div class="message-bubble">${escapeHtml(text).replace(/\n/g, '<br>')}</div>
            <div class="message-time">${time}</div>
        </div>
    `;
    
    messagesContainer.appendChild(messageDiv);
    scrollToBottom();
}

// Show typing indicator
function showTypingIndicator() {
    const messagesContainer = document.getElementById('chatMessages');
    if(!messagesContainer) return;

    const indicator = document.createElement('div');
    indicator.className = 'message bot';
    indicator.id = 'typingIndicator';
    indicator.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="typing-indicator active">
            <div class="typing-dots">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
    `;
    messagesContainer.appendChild(indicator);
    scrollToBottom();
}

// Hide typing indicator
function hideTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if(indicator) indicator.remove();
}

// Scroll to bottom
function scrollToBottom() {
    const messages = document.getElementById('chatMessages');
    if(messages) {
        messages.scrollTop = messages.scrollHeight;
    }
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Hiển thị thẻ gợi ý và nút thêm lịch
function showSuggestionCards(suggestions, ctaText) {
    const messagesContainer = document.getElementById('chatMessages');
    if(!messagesContainer) return;

    const time = new Date().toLocaleTimeString('vi-VN', {hour: '2-digit', minute: '2-digit'});
    const wrap = document.createElement('div');
    wrap.className = 'message bot';
    wrap.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-content">
            <div class="message-bubble">
                <div style="margin-bottom:8px;font-weight:600;">${escapeHtml(ctaText)}</div>
                <div id="suggestionList"></div>
                <div style="margin-top:8px; display:flex; gap:8px;">
                    <button id="addAllBtn" class="btn-primary" style="padding:6px 10px;">Thêm tất cả</button>
                    <button id="dismissBtn" class="btn-secondary" style="padding:6px 10px;">Bỏ qua</button>
                </div>
            </div>
            <div class="message-time">${time}</div>
        </div>
    `;
    messagesContainer.appendChild(wrap);

    const listEl = wrap.querySelector('#suggestionList');
    suggestions.forEach((s, idx) => {
        const start = new Date(s.start_time.replace('T',' '));
        const end = new Date(s.end_time.replace('T',' '));
        const item = document.createElement('div');
        item.style.border = '1px solid #e5e7eb';
        item.style.borderRadius = '8px';
        item.style.padding = '8px';
        item.style.marginBottom = '8px';
        item.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; gap:8px;">
                <div>
                    <div style="font-weight:600;">${escapeHtml(s.subject)}</div>
                    <div style="font-size:12px;color:#6b7280;">${start.toLocaleString('vi-VN')} → ${end.toLocaleString('vi-VN')}</div>
                </div>
                <button class="btn-primary" data-idx="${idx}" style="padding:6px 10px;">Thêm</button>
            </div>
        `;
        listEl.appendChild(item);
    });

    // Sự kiện cho nút Thêm từng gợi ý
    listEl.addEventListener('click', async (e) => {
        const btn = e.target.closest('button[data-idx]');
        if (!btn) return;
        const idx = parseInt(btn.getAttribute('data-idx'), 10);
        const suggestion = suggestions[idx];
        await addSuggestionToSchedule(suggestion, btn);
    });

    // Nút Thêm tất cả
    wrap.querySelector('#addAllBtn')?.addEventListener('click', async (e) => {
        const btn = e.currentTarget;
        btn.setAttribute('disabled', 'true');
        let success = 0;
        for (const s of suggestions) {
            try {
                await api.addSchedule(s);
                success++;
            } catch (err) {
                console.error('Add schedule failed:', err);
            }
        }
        addMessage(`Đã thêm ${success}/${suggestions.length} lịch đề xuất. ✅`, 'bot');
        btn.removeAttribute('disabled');
        // Cập nhật lịch nếu có calendar
        if (window.calendar && typeof window.calendar.refetchEvents === 'function') {
            try { window.calendar.refetchEvents(); } catch {}
        }
    });

    // Nút Bỏ qua
    wrap.querySelector('#dismissBtn')?.addEventListener('click', () => {
        wrap.remove();
    });

    scrollToBottom();
}

async function addSuggestionToSchedule(suggestion, buttonEl) {
    try {
        buttonEl?.setAttribute('disabled', 'true');
        await api.addSchedule(suggestion);
        addMessage(`Đã thêm: ${suggestion.subject}`, 'bot');
        // Cập nhật lịch nếu có calendar
        if (window.calendar && typeof window.calendar.refetchEvents === 'function') {
            try { window.calendar.refetchEvents(); } catch {}
        }
    } catch (err) {
        console.error('Add suggestion error:', err);
        addMessage('Không thể thêm lịch. Vui lòng thử lại.', 'bot');
    } finally {
        buttonEl?.removeAttribute('disabled');
    }
}

// Close chatbot when clicking outside (optional)
document.addEventListener('click', function(e) {
    const chatbotWindow = document.getElementById('chatbotWindow');
    const chatbotButton = document.getElementById('chatbotButton');
    
    if(isChatbotOpen && chatbotWindow && chatbotButton) {
        if(!chatbotWindow.contains(e.target) && !chatbotButton.contains(e.target)) {
            // Uncomment to close on outside click
            // toggleChatbot();
        }
    }
});
