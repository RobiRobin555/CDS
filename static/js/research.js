// research.js - Logic cho trang Nghiên cứu (chat tự do)

// Biến toàn cục
let researchHistory = [];
let useWebSearchMode = false;

// Chuyển đổi Markdown sang HTML để trình bày có cấu trúc
function renderMarkdownToHtml(mdText) {
    try {
        if (window.marked && typeof window.marked.parse === 'function') {
            return window.marked.parse(mdText || '');
        }
        const div = document.createElement('div');
        div.textContent = mdText || '';
        return div.innerHTML;
    } catch (e) {
        const div = document.createElement('div');
        div.textContent = mdText || '';
        return div.innerHTML;
    }
}

// Khởi tạo khi trang tải xong
document.addEventListener('DOMContentLoaded', async () => {
    // Kiểm tra đăng nhập
    if (!api.token) {
        window.location.href = '/auth/login.html';
        return;
    }
    
    // Tải lịch sử nghiên cứu
    await loadResearchHistory();
    
    // Xử lý sự kiện nhấn Enter trong textarea
    document.getElementById('queryInput').addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && e.ctrlKey) {
            e.preventDefault();
            startResearch();
        }
    });
    
    // Xử lý sự kiện nút xóa tất cả lịch sử
    document.getElementById('clearHistoryBtn').addEventListener('click', clearAllHistory);
    
    // Xử lý sự kiện nút bắt đầu nghiên cứu
    document.getElementById('startResearchBtn').addEventListener('click', startResearch);

    // Nút bật/tắt tìm kiếm web
    const webToggle = document.getElementById('webSearchToggle');
    if (webToggle) {
        webToggle.addEventListener('click', () => {
            useWebSearchMode = !useWebSearchMode;
            webToggle.classList.toggle('active', useWebSearchMode);
        });
    }
    
    // Xử lý sự kiện nút làm mới
    if (document.getElementById('resetFormBtn')) {
        document.getElementById('resetFormBtn').addEventListener('click', resetForm);
    }
    
    // Xử lý sự kiện nút tiếp tục nghiên cứu
    const continueResearchBtn = document.getElementById('continueResearchBtn');
    if (continueResearchBtn) {
        continueResearchBtn.addEventListener('click', () => {
            // Focus vào ô input và thêm gợi ý để tiếp tục
            const queryInput = document.getElementById('queryInput');
            queryInput.value = "Tiếp tục nghiên cứu về: ";
            queryInput.focus();
            
            // Di chuyển con trỏ đến cuối văn bản
            queryInput.selectionStart = queryInput.value.length;
            queryInput.selectionEnd = queryInput.value.length;
            
            // Cuộn đến vị trí input
            queryInput.scrollIntoView({ behavior: 'smooth' });
        });
    }
});

// Không cần chọn môn học hoặc gợi ý câu hỏi — chat tự do

// Bắt đầu nghiên cứu
async function startResearch() {
    // Lấy câu hỏi
    const query = document.getElementById('queryInput').value.trim();
    if (!query) {
        showNotification('Vui lòng nhập câu hỏi', 'error');
        return;
    }
    
    // Kiểm tra tùy chọn tìm kiếm web (nút toggle)
    const useWebSearch = useWebSearchMode === true;
    
    // Hiển thị dạng chat: ẩn khối kết quả cũ và thêm message vào chat-stream
    const stream = document.getElementById('chatStream');
    if (stream) {
        const userMsg = document.createElement('div');
        userMsg.className = 'msg user-msg';
        userMsg.innerHTML = `
            <div class="msg-content">${query}</div>
            <div class="msg-time">${new Date().toLocaleTimeString()}</div>
        `;
        stream.appendChild(userMsg);

        // Thêm placeholder loading cho assistant
        const loadingMsg = document.createElement('div');
        loadingMsg.className = 'msg assistant-msg';
        loadingMsg.innerHTML = `
            <div class="msg-content">
                <div class="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;
        stream.appendChild(loadingMsg);
        
        // Scroll to bottom
        stream.scrollTop = stream.scrollHeight;
    }
    
    // Disable nút nghiên cứu
    const researchButton = document.getElementById('startResearchBtn');
    researchButton.disabled = true;
    researchButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Đang nghiên cứu...';
    
    // Ẩn nút tiếp tục nghiên cứu trong quá trình xử lý
    document.getElementById('continueResearchContainer').style.display = 'none';
    
    // Ẩn nút tiếp tục nghiên cứu nếu đang hiển thị
    document.getElementById('continueResearchContainer').style.display = 'none';
    
    try {
        // Gọi API nghiên cứu
        const response = await api.request('/research', {
            method: 'POST',
            body: JSON.stringify({
                query: query,
                use_web_search: useWebSearch
            })
        });
        
        // Cập nhật kết quả vào chat-stream
        if (stream) {
            const lastMsg = stream.querySelector('.msg.assistant-msg:last-child');
            if (lastMsg) {
                lastMsg.innerHTML = `
                    <div class="msg-content">${renderMarkdownToHtml(response.result || '')}</div>
                    <div class="msg-time">${new Date().toLocaleTimeString()}</div>
                `;
            } else {
                const assistantMsg = document.createElement('div');
                assistantMsg.className = 'msg assistant-msg';
                assistantMsg.innerHTML = `
                    <div class="msg-content">${renderMarkdownToHtml(response.result || '')}</div>
                    <div class="msg-time">${new Date().toLocaleTimeString()}</div>
                `;
                stream.appendChild(assistantMsg);
            }
            
            // Hiển thị nút tiếp tục nghiên cứu
            document.getElementById('continueResearchContainer').style.display = 'flex';
            
            // Scroll to bottom
            stream.scrollTop = stream.scrollHeight;
        }
        
        // Lưu vào lịch sử và cập nhật UI
        const historyItem = {
            id: response.id || Date.now(),
            subject: response.subject || 'General',
            query: query,
            result: response.result,
            timestamp: new Date().toISOString()
        };
        
        researchHistory.unshift(historyItem);
        saveResearchHistory();
        renderResearchHistory();
        
        // Xóa nội dung input để chuẩn bị cho câu hỏi tiếp theo
        document.getElementById('queryInput').value = '';
        
    } catch (error) {
        console.error('Lỗi khi thực hiện nghiên cứu:', error);
        if (stream) {
            const lastMsg = stream.querySelector('.msg.assistant-msg:last-child');
            if (lastMsg) {
                lastMsg.innerHTML = `
                    <div class="msg-content">
                        <div class="error-state">
                            Đã xảy ra lỗi khi thực hiện nghiên cứu. Vui lòng thử lại sau.
                            <br><small>${error.message || 'Lỗi không xác định'}</small>
                        </div>
                    </div>
                    <div class="msg-time">${new Date().toLocaleTimeString()}</div>
                `;
            }
        }
    } finally {
        // Enable lại nút nghiên cứu
        researchButton.disabled = false;
        researchButton.innerHTML = '<i class="fas fa-search"></i> Bắt đầu nghiên cứu';
    }
}


// Reset form
function resetForm() {
    // Xóa nội dung input
    document.getElementById('queryInput').value = '';
    document.getElementById('queryInput').placeholder = 'Nhập câu hỏi nghiên cứu của bạn...';
    
    // Xóa tất cả tin nhắn trong chat stream
    const chatStream = document.getElementById('chatStream');
    if (chatStream) {
        chatStream.innerHTML = '';
    }
    
    // Ẩn nút tiếp tục nghiên cứu
    document.getElementById('continueResearchContainer').style.display = 'none';
}

// Tải lịch sử nghiên cứu
async function loadResearchHistory() {
    try {
        const historySection = document.getElementById('researchHistory');
        
        // Tạm thời hiển thị thông báo tính năng đang phát triển
        historySection.innerHTML = '<div class="info-state" style="padding: 15px; background-color: #e7f3ff; border-radius: 8px; margin-top: 10px;">' +
            '<h4 style="margin-top: 0;">Tính năng đang phát triển</h4>' +
            '<p>Lịch sử nghiên cứu sẽ được cập nhật trong phiên bản tới.</p>' +
            '</div>';
            
        // Lưu trữ lịch sử tạm thời trong localStorage
        try {
            const savedHistory = localStorage.getItem('researchHistory');
            if (savedHistory) {
                researchHistory = JSON.parse(savedHistory);
            }
        } catch (e) {
            console.log('Không thể đọc lịch sử từ localStorage');
        }
    } catch (error) {
        console.error('Lỗi khi tải lịch sử nghiên cứu:', error);
        document.getElementById('researchHistory').innerHTML = 
            '<div class="error-state">Không thể tải lịch sử nghiên cứu. Vui lòng thử lại sau.</div>';
    }
}

// Tải lịch sử nghiên cứu
async function loadResearchHistory() {
    try {
        // Gọi API lấy lịch sử nghiên cứu
        const response = await api.request('/research/history');
        
        if (response && response.history) {
            researchHistory = response.history;
        } else {
            researchHistory = [];
        }
        
        // Hiển thị lịch sử
        renderResearchHistory();
    } catch (error) {
        console.error('Lỗi khi tải lịch sử nghiên cứu:', error);
        document.getElementById('researchHistory').innerHTML = 
            '<div class="error-state">Không thể tải lịch sử nghiên cứu. Vui lòng thử lại sau.</div>';
    }
}

// Xóa một mục lịch sử nghiên cứu
async function deleteHistoryItem(id) {
    try {
        if (!confirm('Bạn có chắc chắn muốn xóa mục này khỏi lịch sử?')) {
            return;
        }
        
        await api.request(`/research/history/${id}`, {
            method: 'DELETE'
        });
        
        // Cập nhật lại danh sách lịch sử
        await loadResearchHistory();
        showNotification('Đã xóa mục khỏi lịch sử nghiên cứu', 'success');
    } catch (error) {
        console.error('Lỗi khi xóa lịch sử nghiên cứu:', error);
        showNotification('Không thể xóa mục khỏi lịch sử. Vui lòng thử lại sau.', 'error');
    }
}

// Xóa tất cả lịch sử nghiên cứu
async function clearAllHistory() {
    try {
        if (!confirm('Bạn có chắc chắn muốn xóa tất cả lịch sử nghiên cứu?')) {
            return;
        }
        
        await api.request('/research/history', {
            method: 'DELETE'
        });
        
        // Cập nhật lại danh sách lịch sử
        await loadResearchHistory();
        showNotification('Đã xóa tất cả lịch sử nghiên cứu', 'success');
    } catch (error) {
        console.error('Lỗi khi xóa lịch sử nghiên cứu:', error);
        showNotification('Không thể xóa lịch sử. Vui lòng thử lại sau.', 'error');
    }
}

// Lưu lịch sử nghiên cứu vào localStorage
function saveResearchHistory() {
    try {
        // Giới hạn lịch sử 20 mục
        const limitedHistory = researchHistory.slice(0, 20);
        localStorage.setItem('researchHistory', JSON.stringify(limitedHistory));
    } catch (error) {
        console.error('Lỗi khi lưu lịch sử nghiên cứu:', error);
    }
}

// Hiển thị lịch sử nghiên cứu
function renderResearchHistory() {
    const historyElement = document.getElementById('researchHistory');
    
    if (researchHistory.length === 0) {
        historyElement.innerHTML = '<div class="empty-state">Chưa có lịch sử nghiên cứu</div>';
        return;
    }
    
    historyElement.innerHTML = '';
    researchHistory.forEach(item => {
        const historyItem = document.createElement('div');
        historyItem.className = 'history-item';
        historyItem.innerHTML = `
            <div class="history-query">${item.query}</div>
            <div class="history-date">${formatDate(new Date(item.timestamp))}</div>
        `;
        
        // Khi click vào item lịch sử, hiển thị lại kết quả dưới dạng chat
        historyItem.addEventListener('click', () => {
            // Xóa nội dung chat hiện tại
            const chatStream = document.getElementById('chatStream');
            chatStream.innerHTML = '';
            
            // Thêm tin nhắn của người dùng vào chat
            const userMsg = document.createElement('div');
            userMsg.className = 'msg user-msg';
            userMsg.innerHTML = `
                <div class="msg-content">${item.query}</div>
                <div class="msg-time">${formatDate(new Date(item.timestamp))}</div>
            `;
            chatStream.appendChild(userMsg);
            
            // Thêm tin nhắn của AI vào chat
            const aiMsg = document.createElement('div');
            aiMsg.className = 'msg assistant-msg';
            aiMsg.innerHTML = `
                <div class="msg-content">${renderMarkdownToHtml(item.result || '')}</div>
                <div class="msg-time">${formatDate(new Date(item.timestamp))}</div>
            `;
            chatStream.appendChild(aiMsg);
            
            // Hiển thị nút tiếp tục nghiên cứu
            document.getElementById('continueResearchContainer').style.display = 'flex';
            
            // Scroll xuống dưới để xem kết quả
            chatStream.scrollTop = chatStream.scrollHeight;
            
            // Đặt giá trị cho input
            document.getElementById('queryInput').value = '';
            document.getElementById('queryInput').placeholder = 'Nhập câu hỏi tiếp theo...';
        });
        
        historyElement.appendChild(historyItem);
    });
}

// Format date
function formatDate(date) {
    return date.toLocaleDateString('vi-VN', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Hiển thị thông báo
function showNotification(message, type = 'info') {
    // Sử dụng hàm showNotification từ utils.js nếu có
    if (window.showNotification) {
        window.showNotification(message, type);
    } else {
        alert(message);
    }
}
