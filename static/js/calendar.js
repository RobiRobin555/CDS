// ============================================
// CALENDAR.JS - FullCalendar Integration
// ============================================

let calendar;
let selectedColor = '#3788d8';
let editingEventId = null;

document.addEventListener('DOMContentLoaded', async function() {
    // Initialize FullCalendar
    const calendarEl = document.getElementById('calendar');
    
    if(!calendarEl) return;

    calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay'
        },
        locale: 'vi',
        buttonText: {
            today: 'Hôm nay',
            month: 'Tháng',
            week: 'Tuần',
            day: 'Ngày'
        },
        height: 'auto',
        editable: true,
        selectable: true,
        eventOverlap: true,
        slotEventOverlap: true,
        
        // Fetch events from API
        events: async function(fetchInfo, successCallback, failureCallback) {
            try {
                const data = await api.getSchedule({
                    start: fetchInfo.startStr,
                    end: fetchInfo.endStr
                });
                
                if(!data || !data.schedules) {
                    successCallback([]);
                    return;
                }
                
                const events = data.schedules.map(s => ({
                    id: s.id,
                    title: s.subject,
                    start: s.start_time,
                    end: s.end_time,
                    backgroundColor: s.color || '#3788d8',
                    borderColor: s.color || '#3788d8',
                    extendedProps: {
                        location: s.location,
                        type: s.type,
                        description: s.description
                    }
                }));
                
                successCallback(events);
            } catch(error) {
                console.error('Error loading events:', error);
                failureCallback(error);
            }
        },
        
        // Event click - open edit modal
        eventClick: function(info) {
            openEditEventModal(info.event);
        },
        
        // Date click - add new event
        dateClick: function(info) {
            document.getElementById('date').value = info.dateStr;
            openAddEventModal();
        },

        // Event drag & drop
        eventDrop: async function(info) {
            try {
                await api.updateSchedule(info.event.id, {
                    start_time: info.event.start.toISOString(),
                    end_time: info.event.end ? info.event.end.toISOString() : null
                });
                api.showNotification('✅ Đã cập nhật lịch', 'success');
            } catch(error) {
                info.revert();
                api.showNotification('❌ Lỗi khi cập nhật', 'error');
            }
        },

        // Event resize
        eventResize: async function(info) {
            try {
                await api.updateSchedule(info.event.id, {
                    end_time: info.event.end.toISOString()
                });
                api.showNotification('✅ Đã thay đổi thời gian', 'success');
            } catch(error) {
                info.revert();
                api.showNotification('❌ Lỗi khi thay đổi', 'error');
            }
        }
    });
    
    calendar.render();
    
    // Load sidebar data
    loadTodaySchedule();
    loadWeeklyStats();
    loadUpcomingExams();

    // Setup color picker
    setupColorPicker();

    // Setup form submit
    document.getElementById('eventForm').addEventListener('submit', handleSubmitEvent);
    // Setup delete button
    const deleteBtn = document.getElementById('deleteEventBtn');
    if(deleteBtn){
        deleteBtn.addEventListener('click', async function(){
            if(!editingEventId) return;
            if(!confirm('Bạn có chắc muốn xóa lịch này?')) return;
            await deleteEvent(editingEventId);
            closeModal();
        });
    }
});

// Load today's schedule for sidebar
async function loadTodaySchedule() {
    try {
        const today = new Date().toISOString().split('T')[0];
        const data = await api.getSchedule({
            start: today,
            end: today
        });
        
        const container = document.getElementById('todaySchedule');
        if(!container) return;

        container.innerHTML = '';
        
        if(!data.schedules || data.schedules.length === 0) {
            container.innerHTML = '<p style="color: #6b7280;">Không có lịch hôm nay</p>';
            return;
        }
        
        data.schedules.forEach(schedule => {
            const item = document.createElement('div');
            item.className = 'schedule-item';
            item.style.borderLeftColor = schedule.color || '#3788d8';
            item.innerHTML = `
                <div class="schedule-time">${formatTime(schedule.start_time)} - ${formatTime(schedule.end_time)}</div>
                <div class="schedule-subject">${schedule.subject}</div>
                <div class="schedule-location">📍 ${schedule.location || 'Chưa có'}</div>
            `;
            container.appendChild(item);
        });
    } catch(error) {
        console.error('Error loading today schedule:', error);
    }
}

// Load weekly statistics
async function loadWeeklyStats() {
    try {
        const stats = await api.getWeeklyStats();
        
        if(stats) {
            document.getElementById('weeklyClasses').textContent = stats.total_classes || 0;
            document.getElementById('weeklySubjects').textContent = stats.total_subjects || 0;
            document.getElementById('weeklyHours').textContent = stats.total_hours || 0;
            document.getElementById('weeklyTasks').textContent = stats.pending_tasks || 0;
        }
    } catch(error) {
        console.error('Error loading stats:', error);
    }
}

// Load upcoming exams
async function loadUpcomingExams() {
    try {
        const today = new Date();
        const nextMonth = new Date();
        nextMonth.setMonth(nextMonth.getMonth() + 1);

        const data = await api.getSchedule({
            start: today.toISOString().split('T')[0],
            end: nextMonth.toISOString().split('T')[0]
        });

        const container = document.getElementById('upcomingExams');
        if(!container) return;

        const exams = data.schedules?.filter(s => s.type === 'exam') || [];

        if(exams.length === 0) {
            container.innerHTML = '<p style="color: #6b7280;">Không có kỳ thi sắp tới</p>';
            return;
        }

        container.innerHTML = '';
        exams.slice(0, 3).forEach(exam => {
            const daysUntil = Math.ceil((new Date(exam.start_time) - new Date()) / (1000 * 60 * 60 * 24));
            const item = document.createElement('div');
            item.className = 'schedule-item';
            item.style.borderLeftColor = '#ef4444';
            item.innerHTML = `
                <div class="schedule-time">${formatDate(exam.start_time)}</div>
                <div class="schedule-subject">${exam.subject}</div>
                <div class="schedule-location">⏰ Còn ${daysUntil} ngày</div>
            `;
            container.appendChild(item);
        });
    } catch(error) {
        console.error('Error loading exams:', error);
    }
}

// Setup color picker
function setupColorPicker() {
    document.querySelectorAll('.color-option').forEach(option => {
        option.addEventListener('click', function() {
            document.querySelectorAll('.color-option').forEach(o => o.classList.remove('selected'));
            this.classList.add('selected');
            selectedColor = this.dataset.color;
        });
    });
}

// Open add event modal
function openAddEventModal() {
    document.getElementById('eventModal').classList.add('active');
    editingEventId = null;
    const titleEl = document.getElementById('eventModalTitle');
    const saveBtn = document.getElementById('saveEventBtn');
    const delBtn = document.getElementById('deleteEventBtn');
    if(titleEl) titleEl.textContent = '➕ Thêm lịch học';
    if(saveBtn) saveBtn.textContent = '💾 Lưu lịch';
    if(delBtn) delBtn.style.display = 'none';
    const hiddenId = document.getElementById('eventId');
    if(hiddenId) hiddenId.setAttribute('value','');
    // Set default date to today if not set
    if(!document.getElementById('date').value) {
        document.getElementById('date').value = new Date().toISOString().split('T')[0];
    }
}

// Close modal
function closeModal() {
    document.getElementById('eventModal').classList.remove('active');
    document.getElementById('eventForm').reset();
    selectedColor = '#3788d8';
    document.querySelectorAll('.color-option').forEach(o => o.classList.remove('selected'));
    document.querySelector('.color-option').classList.add('selected');
    editingEventId = null;
    const delBtn = document.getElementById('deleteEventBtn');
    if(delBtn) delBtn.style.display = 'none';
}

// Handle add/edit event form submit
async function handleSubmitEvent(e) {
    e.preventDefault();
    
    const date = document.getElementById('date').value;
    const start = document.getElementById('startTime').value;
    const end = document.getElementById('endTime').value;
    const recurringValue = document.getElementById('recurring').value;

    const scheduleData = {
        subject: document.getElementById('subject').value,
        start_time: `${date} ${start}:00`,
        end_time: `${date} ${end}:00`,
        location: document.getElementById('location').value,
        type: document.getElementById('type').value,
        recurring: recurringValue && recurringValue !== 'none' ? { frequency: recurringValue } : null,
        color: selectedColor,
        reminder_time: parseInt(document.getElementById('reminder').value) || 30
    };

    // Validate time
    if(new Date(`${date}T${start}:00`) >= new Date(`${date}T${end}:00`)) {
        api.showNotification('⚠️ Giờ kết thúc phải sau giờ bắt đầu!', 'warning');
        return;
    }

    try {
        if(editingEventId){
            // Update existing schedule
            const result = await api.updateSchedule(editingEventId, scheduleData);
            if(result){
                if(typeof calendar !== 'undefined' && calendar.refetchEvents) {
                    calendar.refetchEvents();
                }
                closeModal();
                if(typeof loadTodaySchedule === 'function') {
                    loadTodaySchedule();
                }
                api.showNotification('✅ Đã cập nhật lịch học', 'success');
            }
        } else {
            // Check conflicts (only for creating new)
            const conflicts = await api.checkConflicts({ start_time: scheduleData.start_time, end_time: scheduleData.end_time });
            if(conflicts && conflicts.conflicts && conflicts.conflicts.length > 0) {
                if(!confirm(`⚠️ Phát hiện ${conflicts.conflicts.length} lịch trùng giờ! Bạn vẫn muốn thêm?`)) {
                    return;
                }
            }

            // Add schedule
            const result = await api.addSchedule(scheduleData);
            
            if(result && (result.schedule_id || result.message)) {
                if(typeof calendar !== 'undefined' && calendar.refetchEvents) {
                    calendar.refetchEvents();
                }
                closeModal();
                if(typeof loadTodaySchedule === 'function') {
                    loadTodaySchedule();
                }
                api.showNotification('✅ Đã thêm lịch học thành công!', 'success');
            }
        }
    } catch(error) {
        api.showNotification('❌ Lỗi khi lưu lịch', 'error');
    }
}

// Open edit event modal
function openEditEventModal(event) {
    // Prefill form values
    editingEventId = event.id;
    const hiddenId = document.getElementById('eventId');
    if(hiddenId) hiddenId.setAttribute('value', event.id);
    const titleEl = document.getElementById('eventModalTitle');
    const saveBtn = document.getElementById('saveEventBtn');
    const delBtn = document.getElementById('deleteEventBtn');
    if(titleEl) titleEl.textContent = '✏️ Sửa lịch học';
    if(saveBtn) saveBtn.textContent = '💾 Cập nhật lịch';
    if(delBtn) delBtn.style.display = 'inline-block';

    document.getElementById('subject').value = event.title || '';
    const start = event.start;
    const end = event.end || new Date(start.getTime() + 60*60*1000);
    const dateStr = start.toISOString().split('T')[0];
    const pad = (n) => String(n).padStart(2, '0');
    const startStr = `${pad(start.getHours())}:${pad(start.getMinutes())}`;
    const endStr = `${pad(end.getHours())}:${pad(end.getMinutes())}`;
    document.getElementById('date').value = dateStr;
    document.getElementById('startTime').value = startStr;
    document.getElementById('endTime').value = endStr;
    document.getElementById('location').value = event.extendedProps.location || '';
    document.getElementById('type').value = event.extendedProps.type || 'class';
    document.getElementById('recurring').value = 'none';
    selectedColor = event.backgroundColor || '#3788d8';
    document.querySelectorAll('.color-option').forEach(o => {
        o.classList.toggle('selected', o.dataset.color === selectedColor);
    });

    document.getElementById('eventModal').classList.add('active');
}

// Delete event
async function deleteEvent(eventId) {
    try {
        await api.deleteSchedule(eventId);
        calendar.refetchEvents();
        loadTodaySchedule();
        api.showNotification('🗑️ Đã xóa lịch học', 'success');
    } catch(error) {
        api.showNotification('❌ Lỗi khi xóa lịch', 'error');
    }
}

// Close modal when clicking outside
document.addEventListener('click', function(e) {
    const modal = document.getElementById('eventModal');
    if(e.target === modal) {
        closeModal();
    }
});
