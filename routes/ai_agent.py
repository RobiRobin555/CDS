"""
routes/ai_agent.py - AI Chatbot API với nhiều LLM options
"""

from flask import Blueprint, request, jsonify
from models import get_db
from utils.auth import token_required
from utils.ai_helper import (
    get_user_context, 
    build_ai_prompt, 
    extract_intent,
    quick_response,
    search_web
)
import os
import requests
from datetime import datetime

ai_bp = Blueprint('ai', __name__)

# Configuration - Chọn LLM provider
LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'groq')  # groq/huggingface/ollama

# API Keys (set trong environment variables)
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
HF_API_KEY = os.getenv('HF_API_KEY')
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')
GROQ_MODEL = os.getenv('GROQ_MODEL', 'mixtral-8x7b-32768')


def query_groq(prompt):
    """
    Gọi Groq API (FASTEST - Recommended)
    Free tier: 30 requests/minute
    Đăng ký tại: https://console.groq.com
    """
    if not GROQ_API_KEY:
        return "Error: GROQ_API_KEY not configured"
    
    try:
        response = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {GROQ_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                'model': GROQ_MODEL,
                'messages': [
                    {'role': 'system', 'content': 'Bạn là trợ lý học tập, trả lời ngắn gọn, rõ ràng bằng tiếng Việt dưới 500 ký tự.'},
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.7,
                'max_tokens': 500
            },
            timeout=20
        )
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            # Trả về chi tiết lỗi để dễ debug
            try:
                err = response.json()
            except Exception:
                err = response.text
            return f"Groq API Error: {response.status_code} - {err}"
    
    except requests.exceptions.Timeout:
        return "AI timeout. Vui lòng thử lại."
    except Exception as e:
        return f"Error: {str(e)}"


def query_huggingface(prompt):
    """
    Gọi Hugging Face Inference API
    Free tier có limit, có thể bị queue
    """
    if not HF_API_KEY:
        return "Error: HF_API_KEY not configured"
    
    try:
        response = requests.post(
            'https://api-inference.huggingface.co/models/mistralai/Mixtral-8x7B-Instruct-v0.1',
            headers={'Authorization': f'Bearer {HF_API_KEY}'},
            json={
                'inputs': prompt,
                'parameters': {
                    'max_new_tokens': 250,
                    'temperature': 0.7,
                    'return_full_text': False
                }
            },
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                return result[0].get('generated_text', 'No response')
            return str(result)
        else:
            return f"HuggingFace API Error: {response.status_code}"
    
    except requests.exceptions.Timeout:
        return "AI timeout. Vui lòng thử lại."
    except Exception as e:
        return f"Error: {str(e)}"


def query_ollama(prompt):
    """
    Gọi Ollama local model
    Cần cài Ollama và pull model trước: ollama pull llama3
    """
    try:
        response = requests.post(
            f'{OLLAMA_URL}/api/generate',
            json={
                'model': 'llama3',  # hoặc phi3, mistral
                'prompt': prompt,
                'stream': False
            },
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json().get('response', 'No response')
        else:
            return f"Ollama Error: {response.status_code}"
    
    except requests.exceptions.ConnectionError:
        return "Không thể kết nối Ollama. Đảm bảo Ollama đang chạy."
    except requests.exceptions.Timeout:
        return "AI timeout. Vui lòng thử lại."
    except Exception as e:
        return f"Error: {str(e)}"


def get_ai_response_long(prompt, max_tokens=8000):
    """
    Gọi LLM với cấu hình trả lời dài (dùng cho phần nghiên cứu tự do)
    Tối ưu để sinh ra nội dung dài hơn, tự nhiên và có cấu trúc.
    """
    if LLM_PROVIDER == 'groq':
        if not GROQ_API_KEY:
            return "Error: GROQ_API_KEY not configured"
        try:
            response = requests.post(
                'https://api.groq.com/openai/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {GROQ_API_KEY}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': GROQ_MODEL,
                    'messages': [
                        {
                            'role': 'system',
                            'content': 'Bạn là AI tạo sinh bằng tiếng Việt. Trả lời mạch lạc, tự nhiên, ngắn gọn nhưng giàu chi tiết.Trả lời trong phạm vi giới hạn 3000 ký tự.'
                        },
                        {'role': 'user', 'content': prompt}
                    ],
                    'temperature': 0.7,
                    'max_tokens': max_tokens
                },
                timeout=120
            )
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            else:
                try:
                    err = response.json()
                except Exception:
                    err = response.text
                return f"Groq API Error: {response.status_code} - {err}"
        except requests.exceptions.Timeout:
            return "AI timeout. Vui lòng thử lại."
        except Exception as e:
            return f"Error: {str(e)}"
    elif LLM_PROVIDER == 'huggingface':
        if not HF_API_KEY:
            return "Error: HF_API_KEY not configured"
        try:
            response = requests.post(
                'https://api-inference.huggingface.co/models/mistralai/Mixtral-8x7B-Instruct-v0.1',
                headers={'Authorization': f'Bearer {HF_API_KEY}'},
                json={
                    'inputs': prompt,
                    'parameters': {
                        'max_new_tokens': max_tokens,
                        'temperature': 0.7,
                        'return_full_text': False
                    }
                },
                timeout=60
            )
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get('generated_text', 'No response')
                return str(result)
            else:
                return f"HuggingFace API Error: {response.status_code}"
        except requests.exceptions.Timeout:
            return "AI timeout. Vui lòng thử lại."
        except Exception as e:
            return f"Error: {str(e)}"
    else:  # ollama
        try:
            response = requests.post(
                f'{OLLAMA_URL}/api/generate',
                json={
                    'model': 'llama3',
                    'prompt': prompt,
                    'stream': False,
                    'options': {
                        'num_predict': max_tokens
                    }
                },
                timeout=60
            )
            if response.status_code == 200:
                return response.json().get('response', 'No response')
            else:
                return f"Ollama Error: {response.status_code}"
        except requests.exceptions.ConnectionError:
            return "Không thể kết nối Ollama. Đảm bảo Ollama đang chạy."
        except requests.exceptions.Timeout:
            return "AI timeout. Vui lòng thử lại."
        except Exception as e:
            return f"Error: {str(e)}"


def get_ai_response(prompt):
    """
    Wrapper để gọi LLM theo provider đã config
    """
    providers = {
        'groq': query_groq,
        'huggingface': query_huggingface,
        'ollama': query_ollama
    }
    
    query_func = providers.get(LLM_PROVIDER, query_groq)
    return query_func(prompt)


@ai_bp.route('/chat', methods=['POST'])
@token_required
def chat(current_user):
    """
    Chat với AI Assistant
    
    Request Body:
    {
        "message": "Hôm nay tôi có lịch gì?",
        "use_quick_response": true  (optional, default: true)
    }
    """
    data = request.get_json()
    user_id = current_user['user_id']
    
    if not data or 'message' not in data:
        return jsonify({'error': 'Missing message field'}), 400
    
    user_message = data['message'].strip()
    use_quick = data.get('use_quick_response', True)
    
    if not user_message:
        return jsonify({'error': 'Message cannot be empty'}), 400
    
    # Lấy context của user
    user_context = get_user_context(user_id)
    # Lưu câu hỏi cuối vào context để phục vụ subject_search nhanh
    user_context['_last_query'] = user_message
    
    # Thử trả lời nhanh trước (không cần gọi LLM)
    if use_quick:
        intent = extract_intent(user_message)
        quick_reply = quick_response(intent, user_context, user_id)
        
        if quick_reply:
            # Nếu quick_reply là dict (có suggestions), xử lý đặc biệt
            if isinstance(quick_reply, dict):
                reply_text = quick_reply.get('reply', '')
                save_chat_history(user_id, user_message, reply_text)
                resp = {
                    'message': user_message,
                    'reply': reply_text,
                    'response_type': 'quick',
                    'intent': intent
                }
                if quick_reply.get('suggestions'):
                    resp['suggestions'] = quick_reply['suggestions']
                if quick_reply.get('cta'):
                    resp['cta'] = quick_reply['cta']
                return jsonify(resp), 200
            else:
                # Trả lời dạng text đơn giản
                save_chat_history(user_id, user_message, quick_reply)
                return jsonify({
                    'message': user_message,
                    'reply': quick_reply,
                    'response_type': 'quick',
                    'intent': intent
                }), 200
    
    # Thực hiện tìm kiếm web với Tavily API cho các câu hỏi phức tạp
    web_search_results = search_web(user_message)
    
    # Nếu không có quick response, gọi LLM với kết quả tìm kiếm web
    prompt = build_ai_prompt(user_message, user_context, web_search_results)
    ai_reply = get_ai_response(prompt)
    
    # Lưu vào chat history
    save_chat_history(user_id, user_message, ai_reply)
    
    return jsonify({
        'message': user_message,
        'reply': ai_reply,
        'response_type': 'ai',
        'llm_provider': LLM_PROVIDER,
        'web_search': True if web_search_results and 'error' not in web_search_results else False
    }), 200


@ai_bp.route('/chat/history', methods=['GET'])
@token_required
def get_chat_history(current_user):
    """
    Lấy lịch sử chat
    
    Query params:
        - limit: số lượng (default: 20)
    """
    user_id = current_user['user_id']
    limit = request.args.get('limit', 20, type=int)
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, user_msg, ai_reply, timestamp
            FROM chat_history
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (user_id, limit))
        
        history = cursor.fetchall()
    
    history_list = []
    for row in history:
        history_list.append({
            'id': row['id'],
            'user_message': row['user_msg'],
            'ai_reply': row['ai_reply'],
            'timestamp': row['timestamp']
        })
    
    return jsonify({
        'count': len(history_list),
        'history': history_list
    }), 200


@ai_bp.route('/chat/history/<int:chat_id>', methods=['DELETE'])
@token_required
def delete_chat(current_user, chat_id):
    """Xóa một tin nhắn chat"""
    user_id = current_user['user_id']
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM chat_history
            WHERE id = ? AND user_id = ?
        ''', (chat_id, user_id))
        
        if cursor.rowcount == 0:
            return jsonify({'error': 'Chat not found'}), 404
    
    return jsonify({'message': 'Chat deleted'}), 200


@ai_bp.route('/chat/clear', methods=['DELETE'])
@token_required
def clear_chat_history(current_user):
    """Xóa toàn bộ lịch sử chat"""
    user_id = current_user['user_id']
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM chat_history WHERE user_id = ?', (user_id,))
        deleted_count = cursor.rowcount
    
    return jsonify({
        'message': 'Chat history cleared',
        'deleted_count': deleted_count
    }), 200


@ai_bp.route('/suggestions', methods=['GET'])
@token_required
def get_suggestions(current_user):
    """
    Gợi ý câu hỏi dựa trên context hiện tại
    """
    user_id = current_user['user_id']
    user_context = get_user_context(user_id)
    
    suggestions = [
        "Hôm nay tôi có lịch gì?",
        "Tuần này tôi học mấy tiết?"
    ]
    
    # Thêm suggestions động
    if user_context['pending_tasks']:
        suggestions.append("Nhiệm vụ nào cần làm trước?")
    
    if user_context['overdue_count'] > 0:
        suggestions.append("Tasks nào đã quá hạn?")
    
    if user_context['upcoming_schedules']:
        suggestions.append("Khi nào tôi rảnh để học thêm?")
    
    return jsonify({
        'suggestions': suggestions
    }), 200


@ai_bp.route('/research', methods=['POST'])
@token_required
def research_subject(current_user):
    """
    API nghiên cứu (chế độ chat tự do)
    
    Request Body:
    {
        "query": "Câu hỏi/đề bài tự do",
        "use_web_search": true/false (optional, default: false)
    }
    """
    data = request.get_json()
    user_id = current_user['user_id']
    
    if not data or 'query' not in data:
        return jsonify({'error': 'Thiếu câu hỏi'}), 400
    
    query = data['query'].strip()
    if not query:
        return jsonify({'error': 'Câu hỏi không được để trống'}), 400
    
    # Tùy chọn: subject có thể được gửi lên nhưng không bắt buộc
    subject = (data.get('subject') or '').strip() or None
    
    # Chỉ thực hiện tìm kiếm web với Tavily API khi người dùng yêu cầu
    web_search_results = None
    if data.get('use_web_search') is True:
        web_search_results = search_web(query)
    
    # Tạo prompt dạng chat tự do, không nhắc lại lịch hay chủ đề
    prompt = f"""
Bạn là trợ lý AI tạo sinh. Hãy trả lời tự nhiên, rõ ràng, hữu ích và tập trung vào câu hỏi sau bằng tiếng Việt. Tránh lặp lại đề bài, không nhắc lại lịch học hay chủ đề đã chọn.

Câu hỏi:
{query}
"""
    
    # Thêm kết quả tìm kiếm web vào prompt nếu có
    if web_search_results and 'error' not in web_search_results:
        prompt += "\n\nTham khảo một số kết quả tìm kiếm web:\n"
        
        # Thêm câu trả lời tổng hợp nếu có
        if 'answer' in web_search_results and web_search_results['answer']:
            prompt += f"Tóm tắt: {web_search_results['answer']}\n\n"
        
        # Thêm các kết quả tìm kiếm
        if 'results' in web_search_results and web_search_results['results']:
            prompt += "Các nguồn thông tin:\n"
            for i, result in enumerate(web_search_results['results'], 1):
                prompt += f"{i}. {result.get('title', 'Không có tiêu đề')}\n"
                prompt += f"   URL: {result.get('url', 'Không có URL')}\n"
                prompt += f"   Nội dung: {result.get('content', 'Không có nội dung')}\n\n"
    
    prompt += (
        "\nYÊU CẦU TRÌNH BÀY:\n"
        "- Bắt đầu bằng phần TL;DR: 2–4 câu tóm tắt chính.\n"
        "- Trình bày bằng Markdown: dùng tiêu đề (##, ###), danh sách, bảng (nếu hữu ích).\n"
        "- Có cấu trúc rõ ràng, dễ đọc; không lặp lại đề bài.\n"
        "- Độ dài tùy nội dung, không giới hạn số từ." 
    )
    
    # Gọi LLM để lấy kết quả nghiên cứu
    research_result = get_ai_response_long(prompt, max_tokens=2200)
    
    # Lưu lịch sử nghiên cứu vào database
    subject_to_save = subject or 'General'
    research_id = save_research_history(user_id, subject_to_save, query, research_result)
    
    return jsonify({
        'id': research_id,
        'subject': subject_to_save,
        'query': query,
        'result': research_result,
        'web_search': True if (web_search_results and 'error' not in web_search_results) else False
    }), 200


def get_subject_details(user_id, subject_name):
    """Lấy thông tin chi tiết về một môn học từ lịch"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Lấy tất cả các buổi học của môn này
        cursor.execute('''
            SELECT start_time, end_time, location, type
            FROM schedule
            WHERE user_id = ? AND subject = ?
            ORDER BY start_time ASC
        ''', (user_id, subject_name))
        
        sessions = cursor.fetchall()
    
    if not sessions:
        return {
            'session_count': 0,
            'schedule_times': 'Không có lịch',
            'locations': 'Không xác định'
        }
    
    # Xử lý thông tin
    locations = set()
    for session in sessions:
        if session['location']:
            locations.add(session['location'])
    
    # Format thời gian học
    schedule_times = []
    if len(sessions) > 0:
        first_session = sessions[0]
        schedule_times.append(f"Buổi gần nhất: {first_session['start_time']} - {first_session['end_time']}")
    
    return {
        'session_count': len(sessions),
        'schedule_times': ', '.join(schedule_times),
        'locations': ', '.join(locations) if locations else 'Không xác định'
    }


def save_chat_history(user_id, user_msg, ai_reply):
    """Lưu chat history vào database"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO chat_history (user_id, user_msg, ai_reply)
            VALUES (?, ?, ?)
        ''', (user_id, user_msg, ai_reply))
        return cursor.lastrowid


def save_research_history(user_id, subject, query, result):
    """Lưu lịch sử nghiên cứu vào database"""
    with get_db() as conn:
        cursor = conn.cursor()
        # Kiểm tra xem bảng research_history đã tồn tại chưa
        cursor.execute('''
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='research_history'
        ''')
        if not cursor.fetchone():
            # Tạo bảng nếu chưa tồn tại
            cursor.execute('''
                CREATE TABLE research_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    subject TEXT NOT NULL,
                    query TEXT NOT NULL,
                    result TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_research_user ON research_history(user_id)')
        
        # Lưu lịch sử nghiên cứu
        cursor.execute('''
            INSERT INTO research_history (user_id, subject, query, result)
            VALUES (?, ?, ?, ?)
        ''', (user_id, subject, query, result))
        return cursor.lastrowid


@ai_bp.route('/research/history', methods=['GET'])
@token_required
def get_research_history(current_user):
    """
    Lấy lịch sử nghiên cứu
    
    Query params:
        - limit: số lượng (default: 20)
    """
    user_id = current_user['user_id']
    limit = request.args.get('limit', 20, type=int)
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Kiểm tra xem bảng research_history đã tồn tại chưa
        cursor.execute('''
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='research_history'
        ''')
        if not cursor.fetchone():
            return jsonify({
                'count': 0,
                'history': []
            }), 200
        
        cursor.execute('''
            SELECT id, subject, query, result, timestamp
            FROM research_history
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (user_id, limit))
        
        history = cursor.fetchall()
    
    history_list = []
    for row in history:
        history_list.append({
            'id': row['id'],
            'subject': row['subject'],
            'query': row['query'],
            'result': row['result'],
            'timestamp': row['timestamp']
        })
    
    return jsonify({
        'count': len(history_list),
        'history': history_list
    }), 200


@ai_bp.route('/research/history/<int:research_id>', methods=['DELETE'])
@token_required
def delete_research(current_user, research_id):
    """Xóa một mục lịch sử nghiên cứu"""
    user_id = current_user['user_id']
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Kiểm tra xem bảng research_history đã tồn tại chưa
        cursor.execute('''
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='research_history'
        ''')
        if not cursor.fetchone():
            return jsonify({'error': 'Research history not found'}), 404
        
        cursor.execute('''
            DELETE FROM research_history
            WHERE id = ? AND user_id = ?
        ''', (research_id, user_id))
        
        if cursor.rowcount == 0:
            return jsonify({'error': 'Research not found'}), 404
    
    return jsonify({'message': 'Research deleted'}), 200


@ai_bp.route('/research/history', methods=['DELETE'])
@token_required
def clear_research_history(current_user):
    """Xóa toàn bộ lịch sử nghiên cứu"""
    user_id = current_user['user_id']
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Kiểm tra xem bảng research_history đã tồn tại chưa
        cursor.execute('''
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='research_history'
        ''')
        if not cursor.fetchone():
            return jsonify({
                'message': 'Không có lịch sử để xóa',
                'deleted_count': 0
            }), 200
        
        cursor.execute('DELETE FROM research_history WHERE user_id = ?', (user_id,))
        deleted_count = cursor.rowcount
    
    return jsonify({
        'message': 'Đã xóa toàn bộ lịch sử nghiên cứu',
        'deleted_count': deleted_count
    }), 200


@ai_bp.route('/research/history/<int:history_id>', methods=['DELETE'])
@token_required
def delete_research_history_item(current_user, history_id):
    """
    Xóa một mục lịch sử nghiên cứu cụ thể
    
    Path params:
        - history_id: ID của mục lịch sử cần xóa
    """
    user_id = current_user['user_id']
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Kiểm tra xem mục lịch sử có tồn tại và thuộc về người dùng hiện tại không
        cursor.execute('''
            SELECT id FROM research_history
            WHERE id = ? AND user_id = ?
        ''', (history_id, user_id))
        
        if not cursor.fetchone():
            return jsonify({'error': 'Không tìm thấy mục lịch sử hoặc bạn không có quyền xóa'}), 404
        
        # Xóa mục lịch sử
        cursor.execute('DELETE FROM research_history WHERE id = ? AND user_id = ?', (history_id, user_id))
        
        return jsonify({'message': 'Đã xóa mục lịch sử thành công'}), 200
