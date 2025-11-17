// ============================================
// TASKS.JS - Task Management
// ============================================

let tasks = [];
let editingTaskId = null;
let currentFilter = 'all';

document.addEventListener('DOMContentLoaded', async function() {
    await loadTasks();
    setupDragAndDrop();
    setupFilters();
    
    // Setup form submit
    document.getElementById('taskForm').addEventListener('submit', handleAddTask);
    
    // Close modal when clicking outside
    document.getElementById('taskModal').addEventListener('click', function(e) {
        if(e.target === this) {
            closeTaskModal();
        }
    });
});

// Load tasks from API
async function loadTasks() {
    try {
        const data = await api.getTasks();
        tasks = data.tasks || [];
        renderTasks();
    } catch(error) {
        console.error('Error loading tasks:', error);
        api.showNotification('❌ Lỗi khi tải nhiệm vụ', 'error');
    }
}

// Render tasks to kanban board
function renderTasks() {
    // Clear all lists
    document.getElementById('pendingTasks').innerHTML = '';
    document.getElementById('inProgressTasks').innerHTML = '';
    document.getElementById('completedTasks').innerHTML = '';

    const filtered = tasks.filter(task => {
        if(currentFilter === 'all') return true;
        return task.priority === currentFilter;
    });

    filtered.forEach(task => {
        const card = createTaskCard(task);
        const containerId = task.status === 'completed' ? 'completedTasks'
            : task.status === 'in_progress' ? 'inProgressTasks'
            : 'pendingTasks';
        document.getElementById(containerId).appendChild(card);
    });

    updateCounts();
}

function createTaskCard(task) {
    const card = document.createElement('div');
    card.className = 'task-card';
    card.draggable = true;
    card.dataset.id = task.id;

    card.innerHTML = `
        <div class="task-header">
            <div class="task-title">${escapeHtml(task.title)}</div>
            <div class="task-actions">
                <button class="btn btn-sm" onclick="editTask(${task.id})">✏️</button>
                <button class="btn btn-sm btn-danger" onclick="deleteTask(${task.id})">🗑️</button>
            </div>
        </div>
        <div class="task-meta">
            ${task.due_date ? `⏰ ${escapeHtml(formatDateTime(task.due_date))}` : ''}
            ${task.priority === 'high' ? ' 🔴' : task.priority === 'medium' ? ' 🟡' : ' 🟢'}
        </div>
        <div class="task-desc">${escapeHtml(task.description || '')}</div>
    `;

    return card;
}

function updateCounts() {
    document.getElementById('pendingCount').textContent = tasks.filter(t => t.status === 'pending').length;
    document.getElementById('inProgressCount').textContent = tasks.filter(t => t.status === 'in_progress').length;
    document.getElementById('completedCount').textContent = tasks.filter(t => t.status === 'completed').length;
}

function setupDragAndDrop() {
    const lists = document.querySelectorAll('.task-list');

    lists.forEach(list => {
        list.addEventListener('dragover', e => {
            e.preventDefault();
            list.classList.add('drag-over');
        });

        list.addEventListener('dragleave', () => {
            list.classList.remove('drag-over');
        });

        list.addEventListener('drop', async e => {
            e.preventDefault();
            list.classList.remove('drag-over');

            const taskId = e.dataTransfer.getData('text/plain');
            const newStatus = list.dataset.status;

            try {
                await api.updateTask(taskId, { status: newStatus });
                const task = tasks.find(t => t.id == taskId);
                if(task) task.status = newStatus;
                renderTasks();
                api.showNotification('✅ Đã cập nhật trạng thái', 'success');
            } catch(error) {
                api.showNotification('❌ Lỗi khi cập nhật', 'error');
            }
        });
    });

    document.addEventListener('dragstart', e => {
        if(e.target.classList.contains('task-card')) {
            e.dataTransfer.setData('text/plain', e.target.dataset.id);
            e.target.classList.add('dragging');
        }
    });

    document.addEventListener('dragend', e => {
        if(e.target.classList.contains('task-card')) {
            e.target.classList.remove('dragging');
        }
    });
}

function setupFilters() {
    const filterButtons = document.querySelectorAll('.filter-btn');
    filterButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            filterButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilter = btn.dataset.filter;
            renderTasks();
        });
    });
}

function openTaskModal() {
    editingTaskId = null;
    document.getElementById('modalTitle').textContent = '➕ Thêm nhiệm vụ';
    document.getElementById('taskTitle').value = '';
    document.getElementById('taskDescription').value = '';
    document.getElementById('taskDueDate').value = '';
    document.getElementById('taskPriority').value = 'medium';
    document.getElementById('taskStatus').value = 'pending';
    document.getElementById('taskModal').classList.add('active');
}

function closeTaskModal() {
    document.getElementById('taskModal').classList.remove('active');
}

function editTask(id) {
    const task = tasks.find(t => t.id === id);
    if(!task) return;

    editingTaskId = id;
    document.getElementById('modalTitle').textContent = '✏️ Sửa nhiệm vụ';
    document.getElementById('taskTitle').value = task.title;
    document.getElementById('taskDescription').value = task.description || '';
    // Convert SQL datetime to input value format (YYYY-MM-DDTHH:MM)
    document.getElementById('taskDueDate').value = toLocalInputValue(task.due_date);
    document.getElementById('taskPriority').value = task.priority || 'medium';
    document.getElementById('taskStatus').value = task.status || 'pending';
    
    document.getElementById('taskModal').classList.add('active');
}

async function deleteTask(id) {
    if(!confirm('Bạn có chắc muốn xóa nhiệm vụ này?')) return;
    try {
        await api.deleteTask(id);
        await loadTasks();
        api.showNotification('🗑️ Đã xóa nhiệm vụ', 'success');
    } catch(error) {
        api.showNotification('❌ Lỗi khi xóa nhiệm vụ', 'error');
    }
}

// Handle add/edit task form submit
async function handleAddTask(e) {
    e.preventDefault();

    const rawDue = document.getElementById('taskDueDate').value;
    const taskData = {
        title: document.getElementById('taskTitle').value,
        description: document.getElementById('taskDescription').value,
        due_date: toSqlDateTime(rawDue),
        priority: document.getElementById('taskPriority').value,
        status: document.getElementById('taskStatus').value
    };

    try {
        if(editingTaskId) {
            // Update existing task
            await api.updateTask(editingTaskId, taskData);
            api.showNotification('✅ Đã cập nhật nhiệm vụ', 'success');
        } else {
            // Add new task
            await api.addTask(taskData);
            api.showNotification('✅ Đã thêm nhiệm vụ mới', 'success');
        }

        await loadTasks();
        closeTaskModal();
    } catch(error) {
        api.showNotification('❌ Lỗi khi lưu nhiệm vụ', 'error');
    }
}

// Helpers to safely render text
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Convert "YYYY-MM-DD HH:MM:SS" to input datetime-local value
function toLocalInputValue(sqlDateTime) {
    if(!sqlDateTime) return '';
    const m = sqlDateTime.match(/^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?/);
    if(!m) return '';
    const [, y, mo, d, h, mi] = m;
    return `${y}-${mo}-${d}T${h}:${mi}`;
}

// Convert input datetime-local to "YYYY-MM-DD HH:MM:SS" (SQL-like)
function toSqlDateTime(localValue) {
    if(!localValue) return null;
    const m = localValue.match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/);
    if(!m) return null;
    const [, y, mo, d, h, mi] = m;
    return `${y}-${mo}-${d} ${h}:${mi}:00`;
}