"""
utils/ai_helper.py - AI Prompt Engineering & Context Building
"""

from models import get_db
from datetime import datetime, timedelta
from utils.conflict_detector import find_free_slots
import os
import requests
import json

# Tavily API Key
TAVILY_API_KEY = os.getenv('TAVILY_API_KEY', '')

def search_web(query, max_results=3):
    """
    Tìm kiếm thông tin trên web sử dụng Tavily Search API
    
    Args:
        query (str): Câu truy vấn tìm kiếm
        max_results (int): Số lượng kết quả tối đa
        
    Returns:
        dict: Kết quả tìm kiếm hoặc thông báo lỗi
    """
    if not TAVILY_API_KEY:
        return {"error": "TAVILY_API_KEY không được cấu hình"}
    
    try:
        response = requests.post(
            "https://api.tavily.com/search",
            headers={
                "Content-Type": "application/json",
                "X-API-Key": TAVILY_API_KEY
            },
            json={
                "query": query,
                "search_depth": "basic",
                "max_results": max_results,
                "include_domains": [],
                "exclude_domains": [],
                "include_answer": True,
                "include_raw_content": False,
                "include_images": False
            },
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Tavily API Error: {response.status_code}"}
            
    except requests.exceptions.Timeout:
        return {"error": "Tìm kiếm web timeout. Vui lòng thử lại."}
    except Exception as e:
        return {"error": f"Lỗi tìm kiếm web: {str(e)}"}


def get_user_context(user_id):
    """
    Lấy context của user để truyền vào AI
    Bao gồm: lịch sắp tới, tasks pending, thống kê
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Lấy lịch sắp tới (7 ngày)
        cursor.execute('''
            SELECT subject, start_time, end_time, location, type
            FROM schedule
            WHERE user_id = ?
            AND start_time >= datetime('now')
            AND start_time <= datetime('now', '+7 days')
            ORDER BY start_time ASC
            LIMIT 10
        ''', (user_id,))
        upcoming_schedules = cursor.fetchall()
        
        # Lấy tasks pending
        cursor.execute('''
            SELECT title, due_date, priority, status
            FROM tasks
            WHERE user_id = ?
            AND status != 'completed'
            ORDER BY due_date ASC
            LIMIT 10
        ''', (user_id,))
        pending_tasks = cursor.fetchall()
        
        # Lấy tasks quá hạn
        cursor.execute('''
            SELECT COUNT(*) as count
            FROM tasks
            WHERE user_id = ?
            AND status != 'completed'
            AND due_date < datetime('now')
        ''', (user_id,))
        overdue_count = cursor.fetchone()['count']
        
        # Lấy thống kê tuần này
        cursor.execute('''
            SELECT COUNT(*) as count,
                   SUM((julianday(end_time) - julianday(start_time)) * 24) as total_hours
            FROM schedule
            WHERE user_id = ?
            AND date(start_time) >= date('now', 'weekday 0', '-7 days')
            AND date(start_time) < date('now', 'weekday 0')
        ''', (user_id,))
        week_stats = cursor.fetchone()
    
    # Format context
    context = {
        'upcoming_schedules': [dict(row) for row in upcoming_schedules],
        'pending_tasks': [dict(row) for row in pending_tasks],
        'overdue_count': overdue_count,
        'week_stats': {
            'event_count': week_stats['count'] or 0,
            'total_hours': round(week_stats['total_hours'] or 0, 1)
        }
    }
    
    return context


def build_ai_prompt(user_query, user_context, web_search_results=None):
    """
    Tạo prompt thông minh cho AI với context và kết quả tìm kiếm web (nếu có)
    """
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Format lịch sắp tới
    schedule_text = ""
    if user_context['upcoming_schedules']:
        schedule_text = "Lịch sắp tới:\n"
        for s in user_context['upcoming_schedules']:
            schedule_text += f"- {s['subject']}: {s['start_time']} tại {s['location']}\n"
    else:
        schedule_text = "Không có lịch nào trong 7 ngày tới.\n"
    
    # Format tasks
    tasks_text = ""
    if user_context['pending_tasks']:
        tasks_text = "Nhiệm vụ cần làm:\n"
        for t in user_context['pending_tasks']:
            priority_emoji = "🔴" if t['priority'] == 'high' else "🟡" if t['priority'] == 'medium' else "🟢"
            tasks_text += f"{priority_emoji} {t['title']} - Deadline: {t['due_date']}\n"
    else:
        tasks_text = "Không có nhiệm vụ nào đang chờ.\n"
        
    # Format kết quả tìm kiếm web (nếu có)
    web_search_text = ""
    if web_search_results:
        if 'error' in web_search_results:
            web_search_text = f"Kết quả tìm kiếm web: {web_search_results['error']}\n"
        else:
            web_search_text = "Kết quả tìm kiếm web:\n"
            
            # Thêm câu trả lời tổng hợp nếu có
            if 'answer' in web_search_results and web_search_results['answer']:
                web_search_text += f"Tóm tắt: {web_search_results['answer']}\n\n"
            
            # Thêm các kết quả tìm kiếm
            if 'results' in web_search_results and web_search_results['results']:
                web_search_text += "Các nguồn thông tin:\n"
                for i, result in enumerate(web_search_results['results'], 1):
                    web_search_text += f"{i}. {result.get('title', 'Không có tiêu đề')}\n"
                    web_search_text += f"   URL: {result.get('url', 'Không có URL')}\n"
                    web_search_text += f"   Nội dung: {result.get('content', 'Không có nội dung')[:200]}...\n\n"
    
    # Cảnh báo quá hạn
    overdue_warning = ""
    if user_context['overdue_count'] > 0:
        overdue_warning = f"⚠️ CHÚ Ý: Bạn có {user_context['overdue_count']} nhiệm vụ quá hạn!\n"
    
    # Thống kê tuần
    week_info = f"Tuần này: {user_context['week_stats']['event_count']} sự kiện, tổng {user_context['week_stats']['total_hours']} giờ.\n"
    
    # Tạo prompt
    prompt = f"""Bạn là SmartSchedule AI Assistant - trợ lý thông minh cho sinh viên Việt Nam.

THỜI GIAN HIỆN TẠI: {current_time}

THÔNG TIN SINH VIÊN:
{schedule_text}
{tasks_text}
{overdue_warning}
{week_info}

CÂU HỎI CỦA SINH VIÊN: {user_query}

HƯỚNG DẪN TRẢ LỜI:
- Trả lời bằng tiếng Việt, thật ngắn gọn (tối đa 300 ký tự), thân thiện
- Dựa vào thông tin lịch và tasks ở trên để trả lời chính xác
- Nếu hỏi về lịch hôm nay/ngày mai/tuần này → liệt kê cụ thể từ dữ liệu
- Nếu hỏi về tasks → ưu tiên tasks có priority cao và gần deadline
- Nếu có tasks quá hạn → nhắc nhở ưu tiên làm trước
- Nếu hỏi gợi ý thời gian học → tìm khoảng trống giữa các lịch
- Nếu không có thông tin trong dữ liệu → nói "Tôi không thấy thông tin này trong lịch của bạn"
- Luôn kết thúc bằng emoji phù hợp (📚 📅 ✅ 🎯)

TRẢ LỜI:"""
    
    return prompt


def extract_intent(user_query):
    """
    Phân tích ý định của user từ câu hỏi
    Giúp xử lý nhanh các câu hỏi đơn giản không cần LLM
    """
    query_lower = user_query.lower()
    
    intents = {
        'schedule_today': ['hôm nay', 'today', 'bữa nay', 'hôm ni'],
        'schedule_tomorrow': ['ngày mai', 'tomorrow', 'mai'],
        'schedule_week': ['tuần này', 'this week', 'week'],
        'tasks_list': ['nhiệm vụ', 'task', 'bài tập', 'deadline'],
        'overdue': ['quá hạn', 'overdue', 'trễ'],
        'free_time': ['rảnh', 'free', 'trống', 'thời gian', 'gợi ý', 'ôn tập', 'học'],
        'stats': ['thống kê', 'stats', 'tổng'],
        # Tra cứu thông tin môn học
        'subject_search': ['môn', 'môn học', 'subject', 'thông tin môn', 'tiết học', 'giảng viên']
    }
    
    for intent, keywords in intents.items():
        if any(keyword in query_lower for keyword in keywords):
            return intent
    
    return 'general'


def quick_response(intent, user_context, user_id=None):
    """
    Trả lời nhanh cho các câu hỏi đơn giản không cần gọi LLM
    Giúp tiết kiệm API calls
    """
    def subject_info_or_none():
        """Tra cứu môn học; nếu không xác định được môn thì trả về None để fallback LLM."""
        resp = format_subject_info(user_id, user_context, last_query_text=user_context.get('_last_query'))
        try:
            text = str(resp or '')
        except Exception:
            text = ''
        # Nếu không đoán được môn, format_subject_info sẽ gợi ý chọn môn -> cho LLM xử lý thay
        if 'Bạn muốn tra cứu môn nào?' in text:
            return None
        return resp

    responses = {
        'schedule_today': lambda: format_today_schedule(user_context),
        'schedule_tomorrow': lambda: format_tomorrow_schedule(user_context),
        'schedule_week': lambda: format_week_schedule(user_context),
        'tasks_list': lambda: format_tasks(user_context),
        'overdue': lambda: format_overdue(user_context),
        'free_time': lambda: build_study_task_suggestions(user_id, user_context),
        'subject_search': subject_info_or_none
    }
    
    if intent in responses:
        return responses[intent]()
    
    return None


def _normalize_text(s: str):
    try:
        return str(s).lower().strip()
    except Exception:
        return ''


def format_subject_info(user_id, context, last_query_text=None):
    """Tra cứu thông tin môn học từ lịch của người dùng.
    - Cố gắng suy ra tên môn từ câu hỏi (last_query_text)
    - Tóm tắt số buổi sắp tới, buổi gần nhất, có kỳ thi hay không
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute('''
            SELECT subject, start_time, end_time, location, type
            FROM schedule
            WHERE user_id = ?
            ORDER BY start_time ASC
        ''', (user_id,))
        rows = [dict(r) for r in cur.fetchall()]

    if not rows:
        return "Bạn chưa có dữ liệu lịch để tra cứu môn học. Hãy thêm lịch trước nhé! 📚"

    # Danh sách môn duy nhất
    subjects = {}
    for r in rows:
        subj = r.get('subject')
        if not subj:
            continue
        key = _normalize_text(subj)
        subjects.setdefault(key, subj)

    query = _normalize_text(last_query_text or '')
    target_key = None
    if query:
        # Ưu tiên khớp theo chuỗi con
        for key in subjects.keys():
            if key and key in query:
                target_key = key
                break
        # Fallback: khớp theo token (tối thiểu 2 token trùng)
        if not target_key:
            q_tokens = [t for t in query.split() if len(t) >= 2]
            best_key = None
            best_score = 0
            for key in subjects.keys():
                k_tokens = [t for t in key.split() if len(t) >= 2]
                score = len(set(q_tokens) & set(k_tokens))
                if score > best_score:
                    best_score = score
                    best_key = key
            if best_score >= 2:
                target_key = best_key

    # Nếu không đoán được, gợi ý danh sách môn
    if not target_key:
        top_subjects = sorted(set(subjects.values()))
        preview = ', '.join(top_subjects[:5])
        return f"Bạn muốn tra cứu môn nào? Ví dụ: 'Thông tin môn {top_subjects[0]}'\nCác môn gần đây: {preview}"

    target_name = subjects[target_key]
    # Lọc lịch theo môn
    subj_rows = [r for r in rows if _normalize_text(r.get('subject')) == target_key]

    # Thống kê
    now = datetime.now()
    upcoming = []
    exams = []
    for r in subj_rows:
        try:
            st = datetime.fromisoformat(str(r['start_time']).replace('T', ' '))
        except Exception:
            continue
        if st >= now:
            upcoming.append(r)
        if 'exam' in _normalize_text(r.get('type')):
            exams.append(r)

    next_text = ""
    if upcoming:
        upcoming.sort(key=lambda r: r['start_time'])
        nxt = upcoming[0]
        next_text = f"Buổi gần nhất: {nxt['start_time']} tại {nxt.get('location','')}"
    else:
        next_text = "Không có buổi học sắp tới."

    exam_text = "Có kỳ thi sắp tới." if exams else "Chưa thấy lịch thi."
    total_count = len(subj_rows)
    reply = (
        f"🔎 Thông tin môn: {target_name}\n"
        f"Tổng số buổi trong lịch: {total_count}\n"
        f"{next_text}\n"
        f"{exam_text}"
    )

    return reply


# --- Gợi ý thời gian học và làm bài tập ---

def derive_preferred_windows(user_id, lookback_days=30):
    """Suy ra khung giờ ưa thích từ lịch sử hoàn thành nhiệm vụ và các buổi học.
    Trả về dict gồm study_windows, task_windows (list các tuple (start_hour, end_hour)),
    và study_duration, task_duration (phút) từ thói quen gần đây.
    """
    def _safe_parse(dt_str):
        try:
            return datetime.fromisoformat(str(dt_str).replace('T', ' '))
        except Exception:
            for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
                try:
                    return datetime.strptime(str(dt_str), fmt)
                except Exception:
                    continue
        try:
            return datetime.strptime(str(dt_str), '%Y-%m-%d')
        except Exception:
            return None

    def _top_hours_to_windows(hours, default_windows):
        if not hours:
            return default_windows
        counts = {}
        for h in hours:
            if h is None:
                continue
            counts[h] = counts.get(h, 0) + 1
        top_hours = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
        selected = [h for h, _ in top_hours[:2]]
        windows = []
        for h in selected:
            start_h = max(7, min(21, h))
            end_h = min(22, start_h + 2)
            windows.append((start_h, end_h))
        if len(windows) < 2:
            for w in default_windows:
                if w not in windows:
                    windows.append(w)
                if len(windows) >= 2:
                    break
        return windows[:2]

    def _median_minutes(values, default_value, lo, hi):
        vals = [v for v in values if v and v > 0]
        if not vals:
            return default_value
        vals.sort()
        mid = len(vals) // 2
        median = (vals[mid] if len(vals) % 2 == 1 else (vals[mid - 1] + vals[mid]) / 2)
        median = max(lo, min(hi, int(median)))
        return median

    default_study_windows = [(19, 22), (8, 10)]
    default_task_windows = [(15, 18), (10, 12)]
    default_study_duration = 90
    default_task_duration = 60

    study_start_hours = []
    task_complete_hours = []
    study_durations = []
    task_durations = []

    lookback = f'-{lookback_days} days'

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute('''
            SELECT completed_at FROM tasks
            WHERE user_id = ?
              AND status = 'completed'
              AND completed_at IS NOT NULL
              AND completed_at >= datetime('now', ?)
        ''', (user_id, lookback))
        for r in cur.fetchall():
            dt = _safe_parse(r['completed_at'])
            if dt:
                task_complete_hours.append(dt.hour)

        cur.execute('''
            SELECT start_time, end_time FROM schedule
            WHERE user_id = ?
              AND type = 'study'
              AND start_time >= datetime('now', ?)
        ''', (user_id, lookback))
        for r in cur.fetchall():
            st = _safe_parse(r['start_time'])
            et = _safe_parse(r['end_time'])
            if st:
                study_start_hours.append(st.hour)
            if st and et:
                mins = int((et - st).total_seconds() // 60)
                if mins > 0:
                    study_durations.append(mins)

        cur.execute('''
            SELECT start_time, end_time FROM schedule
            WHERE user_id = ?
              AND type = 'task'
              AND start_time >= datetime('now', ?)
        ''', (user_id, lookback))
        for r in cur.fetchall():
            st = _safe_parse(r['start_time'])
            et = _safe_parse(r['end_time'])
            if st and et:
                mins = int((et - st).total_seconds() // 60)
                if mins > 0:
                    task_durations.append(mins)

    study_windows = _top_hours_to_windows(study_start_hours or task_complete_hours, default_study_windows)
    task_windows = _top_hours_to_windows(task_complete_hours, default_task_windows)
    study_duration = _median_minutes(study_durations, default_study_duration, 60, 120)
    task_duration = _median_minutes(task_durations, default_task_duration, 30, 120)

    return {
        'study_windows': study_windows,
        'task_windows': task_windows,
        'study_duration': study_duration,
        'task_duration': task_duration,
    }


def build_study_task_suggestions(user_id, context, days=3):
    """
    Xây dựng gợi ý các khung giờ ôn tập và làm bài tập dựa trên khoảng trống,
    ưu tiên theo deadline (task) và môn có kỳ thi gần nhất (study),
    đồng thời áp dụng khung giờ ưa thích nếu phù hợp.
    """
    if not user_id:
        return {
            'reply': 'Tôi có thể gợi ý thời gian học nếu bạn đăng nhập. 📚',
            'suggestions': []
        }

    suggestions = []
    today = datetime.now().date()

    # Lấy khung giờ ưa thích động từ thói quen
    habit = derive_preferred_windows(user_id, lookback_days=45)
    PREF_WINDOWS_STUDY = habit['study_windows']
    PREF_WINDOWS_TASK = habit['task_windows']
    STUDY_MIN = habit['study_duration']
    TASK_MIN = habit['task_duration']

    # Helper: chọn slot theo khung giờ ưa thích
    def pick_slot_with_preferences(slots, windows, min_minutes):
        for idx, slot in enumerate(slots):
            slot_start = datetime.fromisoformat(slot['start'])
            slot_end = datetime.fromisoformat(slot['end'])
            for w_start, w_end in windows:
                ws = slot_start.replace(hour=w_start, minute=0, second=0, microsecond=0)
                we = slot_start.replace(hour=w_end, minute=0, second=0, microsecond=0)
                overlap_start = max(slot_start, ws)
                overlap_end = min(slot_end, we)
                overlap = (overlap_end - overlap_start).total_seconds() / 60
                if overlap >= min_minutes:
                    start_dt = overlap_start
                    end_dt = overlap_start + timedelta(minutes=min_minutes)
                    return start_dt, end_dt, idx
        # fallback: lấy slot đầu tiên đủ dài
        if slots:
            slot = slots[0]
            slot_start = datetime.fromisoformat(slot['start'])
            start_dt = slot_start
            end_dt = start_dt + timedelta(minutes=min_minutes)
            return start_dt, end_dt, 0
        return None

    # Helper: parse datetime an toàn
    def safe_parse(dt_str):
        try:
            return datetime.fromisoformat(dt_str.replace('T', ' '))
        except Exception:
            try:
                return datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
            except Exception:
                try:
                    return datetime.strptime(dt_str, '%Y-%m-%d')
                except Exception:
                    return datetime.now() + timedelta(days=365)

    # Chọn môn có kỳ thi gần nhất, nếu không có thì chọn môn sắp học
    exam_tokens = ['exam', 'thi', 'kiểm tra', 'test', 'midterm', 'final']
    upcoming = list(context.get('upcoming_schedules', []))
    exams = [s for s in upcoming if any(tok in str(s.get('type', '')).lower() for tok in exam_tokens)]
    preferred_subject = None
    if exams:
        exams.sort(key=lambda s: safe_parse(s.get('start_time', '9999-12-31')))
        preferred_subject = exams[0].get('subject')
    if not preferred_subject and upcoming:
        upcoming.sort(key=lambda s: safe_parse(s.get('start_time', '9999-12-31')))
        preferred_subject = upcoming[0].get('subject')
    if not preferred_subject:
        preferred_subject = 'Ôn tập tổng hợp'

    # 1) Gợi ý ôn tập 90 phút, áp dụng khung giờ ưa thích
    study_start_dt = study_end_dt = None
    study_date = None
    for i in range(days):
        d = (today + timedelta(days=i)).isoformat()
        slots = find_free_slots(user_id, d, duration_minutes=STUDY_MIN)
        sel = pick_slot_with_preferences(slots, PREF_WINDOWS_STUDY, STUDY_MIN)
        if sel:
            study_start_dt, study_end_dt, _ = sel
            study_date = d
            break
    if study_start_dt and study_end_dt:
        suggestions.append({
            'subject': f"Ôn tập: {preferred_subject}",
            'start_time': study_start_dt.isoformat(sep=' '),
            'end_time': study_end_dt.isoformat(sep=' '),
            'location': 'Tự học',
            'type': 'study',
            'color': '#2563eb',
            'reminder_time': 30,
            'description': f'Gợi ý ôn tập (ưu tiên môn có thi gần nhất) cho ngày {study_date}'
        })

    # 2) Gợi ý làm bài tập 60 phút, ưu tiên theo priority + deadline
    pending_tasks = list(context.get('pending_tasks', []))
    chosen_task = None
    if pending_tasks:
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        pending_tasks.sort(key=lambda t: (
            priority_order.get(t.get('priority', 'medium'), 1),
            safe_parse(t.get('due_date', '9999-12-31'))
        ))
        chosen_task = pending_tasks[0]

    task_start_dt = task_end_dt = None
    task_date = None
    if chosen_task:
        for i in range(days + 1):
            d = (today + timedelta(days=i)).isoformat()
            slots = find_free_slots(user_id, d, duration_minutes=TASK_MIN)
            sel = pick_slot_with_preferences(slots, PREF_WINDOWS_TASK, TASK_MIN)
            if not sel:
                continue
            ts, te, idx = sel
            # Tránh trùng với khối ôn tập cùng ngày
            if study_date and d == study_date and study_start_dt and study_end_dt:
                overlaps = not (te <= study_start_dt or ts >= study_end_dt)
                if overlaps:
                    # thử slot tiếp theo trong ngày
                    if len(slots) > idx + 1:
                        alt_sel = pick_slot_with_preferences(slots[idx+1:], PREF_WINDOWS_TASK, 60)
                        if alt_sel:
                            ts, te, _ = alt_sel
                        else:
                            continue
                    else:
                        continue
            task_start_dt, task_end_dt = ts, te
            task_date = d
            break

    if task_start_dt and task_end_dt and chosen_task:
        suggestions.append({
            'subject': f"Làm bài tập: {chosen_task.get('title', 'Bài tập')}",
            'start_time': task_start_dt.isoformat(sep=' '),
            'end_time': task_end_dt.isoformat(sep=' '),
            'location': 'Tự học',
            'type': 'task',
            'color': '#10b981',
            'reminder_time': 30,
            'description': f'Gợi ý làm bài tập (ưu tiên deadline) cho ngày {task_date}'
        })

    reply_text = (
        "Mình đã đề xuất thời gian học và làm task dựa theo lịch rảnh, "
        "tối ưu theo thói quen hoàn thành trước đây (khung giờ & thời lượng), "
        "đồng thời vẫn ưu tiên môn có thi gần và task sắp đến hạn. "
        "Bạn có thể thêm từng mục hoặc 'Add All' để đưa vào lịch."
    )

    return {
        'reply': reply_text,
        'suggestions': suggestions,
        'cta': 'Nhấn \"Thêm\" để tạo lịch'
    }


def format_today_schedule(context):
    """Format lịch hôm nay"""
    today = datetime.now().date().isoformat()
    today_schedules = [s for s in context['upcoming_schedules'] 
                       if s['start_time'].startswith(today)]
    
    if not today_schedules:
        return "Hôm nay bạn không có lịch nào. Tranh thủ thời gian để hoàn thành tasks nhé! 📚"
    
    response = "📅 Lịch hôm nay của bạn:\n\n"
    for s in today_schedules:
        time = s['start_time'].split()[1][:5]
        response += f"• {time} - {s['subject']} tại {s['location']}\n"
    
    return response.strip()


def format_tomorrow_schedule(context):
    """Format lịch ngày mai"""
    tomorrow = (datetime.now() + timedelta(days=1)).date().isoformat()
    tomorrow_schedules = [s for s in context['upcoming_schedules'] 
                          if s['start_time'].startswith(tomorrow)]
    
    if not tomorrow_schedules:
        return "Ngày mai bạn không có lịch nào. Có thể thư giãn hoặc làm bài tập! 😊"
    
    response = "📅 Lịch ngày mai:\n\n"
    for s in tomorrow_schedules:
        time = s['start_time'].split()[1][:5]
        response += f"• {time} - {s['subject']} tại {s['location']}\n"
    
    return response.strip()


def format_week_schedule(context):
    """Format lịch tuần này"""
    if not context['upcoming_schedules']:
        return "Tuần này bạn không có lịch nào. 🎉"
    
    response = f"📊 Tuần này bạn có {len(context['upcoming_schedules'])} lịch:\n\n"
    for s in context['upcoming_schedules'][:5]:
        date = s['start_time'].split()[0]
        time = s['start_time'].split()[1][:5]
        response += f"• {date} {time} - {s['subject']}\n"
    
    if len(context['upcoming_schedules']) > 5:
        response += f"\n... và {len(context['upcoming_schedules']) - 5} lịch khác."
    
    return response.strip()


def format_tasks(context):
    """Format danh sách tasks"""
    if not context['pending_tasks']:
        return "Bạn không có nhiệm vụ nào đang chờ. Tuyệt vời! ✅"
    
    response = "📝 Nhiệm vụ cần làm:\n\n"
    for t in context['pending_tasks'][:5]:
        priority_emoji = "🔴" if t['priority'] == 'high' else "🟡" if t['priority'] == 'medium' else "🟢"
        response += f"{priority_emoji} {t['title']}\n   Deadline: {t['due_date']}\n\n"
    
    if context['overdue_count'] > 0:
        response += f"⚠️ {context['overdue_count']} nhiệm vụ đã quá hạn!\n"
    
    return response.strip()


def format_overdue(context):
    """Format tasks quá hạn"""
    if context['overdue_count'] == 0:
        return "Bạn không có nhiệm vụ nào quá hạn. Giữ vững phong độ! 🎯"
    
    return f"⚠️ Bạn có {context['overdue_count']} nhiệm vụ quá hạn. Hãy ưu tiên hoàn thành chúng trước nhé!"
