// statistics.js - Fetch và hiển thị thống kê, kèm phân tích AI

(function() {
  const state = {
    overview: null,
    week: null,
    month: null,
    subjects: null,
    productivity: null,
    busiestDays: null,
    timeDistribution: null
  };

  async function loadOverview() {
    const data = await api.request('/stats/overview');
    state.overview = data?.overview || {};
    document.getElementById('ovTotalSchedules').textContent = state.overview.total_schedules || 0;
    document.getElementById('ovUpcomingSchedules').textContent = state.overview.upcoming_schedules || 0;
    document.getElementById('ovTotalTasks').textContent = state.overview.total_tasks || 0;
    document.getElementById('ovPendingTasks').textContent = state.overview.pending_tasks || 0;
    document.getElementById('ovOverdueTasks').textContent = state.overview.overdue_tasks || 0;
    const rate = Math.round(state.overview.completion_rate || 0);
    document.getElementById('ovCompletionRate').textContent = `${rate}%`;
    // vẽ vòng tròn tiến độ
    const circle = document.getElementById('progressCircle');
    if (circle) {
      const circumference = 2 * Math.PI * 42;
      const offset = circumference - (rate / 100) * circumference;
      circle.style.strokeDashoffset = offset;
    }
  }

  async function loadWeekly() {
    const data = await api.request('/stats/weekly');
    state.week = data?.week_stats || {};
    const container = document.getElementById('weeklyChart');
    container.innerHTML = '';
    const byDay = state.week.by_day || {};
    const order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];
    const dayLabels = {
      Monday: 'T2', Tuesday: 'T3', Wednesday: 'T4', Thursday: 'T5', Friday: 'T6', Saturday: 'T7', Sunday: 'CN'
    };
    const maxHours = Math.max(...order.map(d => (byDay[d]?.hours || 0)), 1);
    order.forEach((d, idx) => {
      const hours = byDay[d]?.hours || 0;
      const wrap = document.createElement('div');
      wrap.className = 'bar-wrap';
      const bar = document.createElement('div');
      bar.className = 'bar';
      bar.style.height = `${Math.round((hours / maxHours) * 120)}px`;
      bar.title = `${dayLabels[d]}: ${hours}h (${byDay[d]?.count || 0} tiết)`;
      const label = document.createElement('div');
      label.className = 'label';
      label.textContent = dayLabels[d];
      wrap.appendChild(bar);
      wrap.appendChild(label);
      container.appendChild(wrap);
    });
    const legend = document.getElementById('weeklyLegend');
    legend.textContent = `Tổng tiết: ${state.week.total_events || 0}, Tổng giờ: ${state.week.total_hours || 0}h, TB/ngày: ${state.week.average_hours_per_day || 0}h`;
  }

  async function loadMonthly() {
    const data = await api.request('/stats/monthly');
    state.month = data?.month_stats || {};
    const tbody = document.querySelector('#monthlyTable tbody');
    tbody.innerHTML = '';
    (state.month.by_week || []).forEach(w => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>Tuần ${w.week}</td><td>${w.count}</td><td>${w.hours}h</td>`;
      tbody.appendChild(tr);
    });
  }

  async function loadSubjects() {
    const data = await api.request('/stats/subjects');
    state.subjects = data?.subject_stats || [];
    const tbody = document.querySelector('#subjectsTable tbody');
    tbody.innerHTML = '';
    state.subjects.forEach(s => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${s.subject}</td>
        <td>${s.class_count}</td>
        <td>${s.total_hours.toFixed(1)}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  async function loadProductivity(period = 'week') {
    const data = await api.request(`/stats/productivity?period=${encodeURIComponent(period)}`);
    state.productivity = data?.productivity || {};
  }

  async function loadBusiestDays() {
    const data = await api.request('/stats/busiest-days');
    state.busiestDays = data?.busiest_days || [];
    const container = document.getElementById('busiestDays');
    container.innerHTML = '';
    state.busiestDays.forEach(d => {
      const row = document.createElement('div');
      row.className = 'card';
      row.innerHTML = `<div style="display:flex; justify-content:space-between;">
        <span>${d.date}</span>
        <span>${d.total_hours}h • ${d.event_count} tiết</span>
      </div>`;
      container.appendChild(row);
    });
  }

  async function loadTimeDistribution() {
    const data = await api.request('/stats/time-distribution');
    state.timeDistribution = data?.time_distribution || {};
    const container = document.getElementById('timeDistributionChart');
    container.innerHTML = '';
    const counts = Array.from({ length: 24 }, (_, h) => state.timeDistribution[h] || 0);
    const max = Math.max(...counts, 1);
    // 24 bars
    counts.forEach((c, h) => {
      const bar = document.createElement('div');
      bar.className = 'bar';
      bar.style.height = `${Math.round((c / max) * 120)}px`;
      bar.title = `${h}:00 - ${c} tiết`;
      bar.style.background = '#38bdf8';
      container.appendChild(bar);
    });
  }

  async function loadAISuggestions() {
    try {
      const data = await api.request('/suggestions');
      const quick = document.getElementById('aiQuickSuggestions');
      quick.innerHTML = '';
      (data?.suggestions || []).forEach(t => {
        const chip = document.createElement('span');
        chip.className = 'chip';
        chip.textContent = t;
        chip.onclick = () => askAI(t);
        quick.appendChild(chip);
      });
    } catch(_) {}
  }

  function buildAnalysisPrompt() {
    const ov = state.overview || {};
    const wk = state.week || {};
    const prod = state.productivity || {};
    const topSubject = (state.subjects || [])[0];
    const peakHours = [];
    if (state.timeDistribution) {
      const pairs = Object.keys(state.timeDistribution).map(h => ({ h: Number(h), c: state.timeDistribution[h] }));
      pairs.sort((a,b) => b.c - a.c);
      pairs.slice(0,3).forEach(p => peakHours.push(`${p.h}:00 (${p.c})`));
    }
    return `Hãy phân tích và đưa ra nhận xét ngắn gọn (5-8 câu) kèm gợi ý cụ thể bằng tiếng Việt để cải thiện năng suất học tập dựa trên số liệu sau:\n\n` +
      `- Tổng lịch: ${ov.total_schedules || 0}, sắp diễn ra: ${ov.upcoming_schedules || 0}\n` +
      `- Nhiệm vụ: tổng ${ov.total_tasks || 0}, đang chờ ${ov.pending_tasks || 0}, quá hạn ${ov.overdue_tasks || 0}, tỷ lệ hoàn thành ${ov.completion_rate || 0}%\n` +
      `- Tuần này: tổng tiết ${wk.total_events || 0}, tổng giờ ${wk.total_hours || 0}h, TB/ngày ${wk.average_hours_per_day || 0}h\n` +
      `- Năng suất: hoàn thành ${prod.completed || 0}/${prod.total_tasks || 0}, quá hạn ${prod.overdue || 0}, thời gian hoàn thành TB ${prod.average_completion_days || 0} ngày\n` +
      `- Môn học nổi bật: ${(topSubject && topSubject.subject) || 'Không có'}, tổng giờ ${(topSubject && topSubject.total_hours) || 0}h\n` +
      `- Khung giờ học nhiều: ${peakHours.join(', ') || 'Không có'}\n\n` +
      `Đưa ra 3-5 gợi ý hành động cụ thể cho tuần tới.`;
  }

  async function analyzeWithAI() {
    const btn = document.getElementById('aiAnalyzeBtn');
    const box = document.getElementById('aiAnalysis');
    btn.disabled = true;
    box.textContent = 'Đang phân tích bằng AI...';
    try {
      const prompt = buildAnalysisPrompt();
      // Bỏ quick_response để đảm bảo gọi LLM
      const res = await api.chat(prompt, null, false);
      const reply = res?.reply || 'Không có phản hồi từ AI';
      box.textContent = reply;
    } catch (e) {
      box.textContent = `Lỗi phân tích: ${e.message || e}`;
    } finally {
      btn.disabled = false;
    }
  }

  async function askAI(message) {
    const box = document.getElementById('aiAnalysis');
    box.textContent = 'Đang hỏi AI...';
    try {
      const res = await api.chat(message, null, true);
      box.textContent = res?.reply || 'Không có phản hồi từ AI';
    } catch (e) {
      box.textContent = `Lỗi: ${e.message || e}`;
    }
  }

  async function refreshAll() {
    try {
      showLoading();
      await Promise.all([
        loadOverview(),
        loadWeekly(),
        loadMonthly(),
        loadSubjects(),
        loadProductivity('week'),
        loadBusiestDays(),
        loadTimeDistribution(),
        loadAISuggestions(),
        drawSubjectPieChart(),
        drawProgressLineChart()
      ]);
    } finally {
      hideLoading();
    }
  }

  function init() {
    document.getElementById('refreshStatsBtn')?.addEventListener('click', refreshAll);
    document.getElementById('aiAnalyzeBtn')?.addEventListener('click', analyzeWithAI);
    refreshAll();
  }

  // Hàm vẽ biểu đồ tròn (Pie Chart)
  function drawSubjectPieChart() {
    const canvas = document.getElementById('subjectPieCanvas');
    const ctx = canvas.getContext('2d');
    const legend = document.getElementById('subjectPieLegend');
    
    if (!state.subjects || state.subjects.length === 0) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#6b7280';
        ctx.font = '14px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('Không có dữ liệu', canvas.width/2, canvas.height/2);
        return;
    }
    
    // Chuẩn bị dữ liệu
    const data = state.subjects.map(s => ({
        label: s.subject,
        value: s.total_hours,
        color: `hsl(${Math.random() * 360}, 70%, 60%)`
    }));
    
    const total = data.reduce((sum, item) => sum + item.value, 0);
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const radius = Math.min(centerX, centerY) - 20;
    
    // Xóa canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Vẽ từng phần của biểu đồ tròn
    let currentAngle = -Math.PI / 2;
    data.forEach(item => {
        const sliceAngle = (item.value / total) * 2 * Math.PI;
        
        // Vẽ miếng
        ctx.beginPath();
        ctx.moveTo(centerX, centerY);
        ctx.arc(centerX, centerY, radius, currentAngle, currentAngle + sliceAngle);
        ctx.closePath();
        ctx.fillStyle = item.color;
        ctx.fill();
        
        // Viền
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.stroke();
        
        // Vẽ phần trăm
        const textAngle = currentAngle + sliceAngle / 2;
        const textX = centerX + Math.cos(textAngle) * (radius * 0.7);
        const textY = centerY + Math.sin(textAngle) * (radius * 0.7);
        
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 12px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        const percent = Math.round((item.value / total) * 100);
        if (percent > 5) { // Chỉ hiện % nếu > 5%
            ctx.fillText(`${percent}%`, textX, textY);
        }
        
        currentAngle += sliceAngle;
    });
    
    // Tạo legend
    legend.innerHTML = '';
    data.forEach(item => {
        const legendItem = document.createElement('div');
        legendItem.className = 'pie-legend-item';
        legendItem.innerHTML = `
            <div class="pie-legend-color" style="background-color: ${item.color}"></div>
            <span>${item.label} (${item.value.toFixed(1)}h)</span>
        `;
        legend.appendChild(legendItem);
    });
  }

  // Hàm vẽ đường xu hướng (Line Chart)
  function drawProgressLineChart() {
    const canvas = document.getElementById('progressLineChart');
    const ctx = canvas.getContext('2d');
    
    // Dữ liệu mẫu - trong thực tế lấy từ API
    const weeks = ['Tuần 1', 'Tuần 2', 'Tuần 3', 'Tuần 4'];
    const completed = [12, 19, 25, 32]; // Số nhiệm vụ hoàn thành
    const total = [20, 25, 30, 35]; // Tổng nhiệm vụ
    
    const padding = 40;
    const chartWidth = canvas.width - 2 * padding;
    const chartHeight = canvas.height - 2 * padding;
    
    // Xóa canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Tìm giá trị max
    const maxValue = Math.max(...total) * 1.2;
    
    // Vẽ trục
    ctx.strokeStyle = '#e5e7eb';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padding, padding);
    ctx.lineTo(padding, canvas.height - padding);
    ctx.lineTo(canvas.width - padding, canvas.height - padding);
    ctx.stroke();
    
    // Vẽ đường hoàn thành
    ctx.strokeStyle = '#10b981';
    ctx.lineWidth = 3;
    ctx.beginPath();
    weeks.forEach((week, i) => {
        const x = padding + (i / (weeks.length - 1)) * chartWidth;
        const y = canvas.height - padding - (completed[i] / maxValue) * chartHeight;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.stroke();
    
    // Vẽ điểm dữ liệu
    weeks.forEach((week, i) => {
        const x = padding + (i / (weeks.length - 1)) * chartWidth;
        const y = canvas.height - padding - (completed[i] / maxValue) * chartHeight;
        
        ctx.fillStyle = '#10b981';
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, 2 * Math.PI);
        ctx.fill();
        
        // Hiện giá trị
        ctx.fillStyle = '#374151';
        ctx.font = '12px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(completed[i], x, y - 10);
    });
    
    // Nhãn trục X
    ctx.fillStyle = '#6b7280';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'center';
    weeks.forEach((week, i) => {
        const x = padding + (i / (weeks.length - 1)) * chartWidth;
        ctx.fillText(week, x, canvas.height - padding + 20);
    });
    
    // Tiêu đề
    ctx.fillStyle = '#374151';
    ctx.font = 'bold 14px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('Tiến độ hoàn thành nhiệm vụ', canvas.width/2, 20);
  }

  // init on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
