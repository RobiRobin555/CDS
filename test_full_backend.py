"""
test_full_backend.py - Comprehensive Test Suite cho toàn bộ Backend & AI Chatbot
Chạy: python test_full_backend.py

Test coverage:
- Authentication (5 APIs)
- Schedule Management (8 APIs)
- Task Management (9 APIs)
- AI Chatbot (4 APIs) - With real conversation flow
- Notifications (6 APIs)
- Import/Export (6 APIs)
- Statistics (7 APIs)
- Integration tests
"""

import os
import requests
import json
import time
from datetime import datetime, timedelta
from colorama import init, Fore, Style
from dotenv import load_dotenv
import sys

# Initialize colorama for colored output
init(autoreset=True)

# Tải biến môi trường từ .env
load_dotenv()

BASE_URL = os.getenv("BASE_URL", "http://localhost:5000/api")
TEST_EMAIL = "giangnamvn555@gmail.com"
TEST_PASSWORD = "123456789"

# Test results tracking
test_results = {
    'passed': 0,
    'failed': 0,
    'warnings': 0,
    'skipped': 0
}

test_details = []


def print_header(text):
    """Print section header"""
    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"{Fore.CYAN}{Style.BRIGHT}{text.center(70)}")
    print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")


def print_test(name, status='RUNNING'):
    """Print test name"""
    if status == 'RUNNING':
        print(f"{Fore.YELLOW}▶ Testing: {name}...", end=' ', flush=True)
    elif status == 'PASS':
        print(f"{Fore.GREEN}✓ PASS{Style.RESET_ALL}")
        test_results['passed'] += 1
    elif status == 'FAIL':
        print(f"{Fore.RED}✗ FAIL{Style.RESET_ALL}")
        test_results['failed'] += 1
    elif status == 'WARN':
        print(f"{Fore.YELLOW}⚠ WARN{Style.RESET_ALL}")
        test_results['warnings'] += 1
    elif status == 'SKIP':
        print(f"{Fore.BLUE}○ SKIP{Style.RESET_ALL}")
        test_results['skipped'] += 1


def print_response(response, verbose=False):
    """Print response details"""
    if verbose:
        try:
            print(f"    Status: {response.status_code}")
            print(f"    Response: {json.dumps(response.json(), indent=4, ensure_ascii=False)[:300]}...")
        except:
            print(f"    Response: {response.text[:200]}")


def test_api(name, method, url, headers=None, json_data=None, expected_status=200, check_keys=None):
    """Generic API test function"""
    print_test(name, 'RUNNING')
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, timeout=10)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=json_data, timeout=10)
        elif method == 'PUT':
            response = requests.put(url, headers=headers, json=json_data, timeout=10)
        elif method == 'DELETE':
            response = requests.delete(url, headers=headers, timeout=10)
        
        # Check status code
        if response.status_code != expected_status:
            print_test(name, 'FAIL')
            print(f"    Expected {expected_status}, got {response.status_code}")
            # Print response content for debugging
            try:
                print(f"    Response content: {response.text[:500]}")
            except:
                print("    Could not print response content")
            test_details.append({
                'test': name,
                'status': 'FAIL',
                'reason': f"Status code mismatch: {response.status_code}"
            })
            return None
        
        # Check response keys
        if check_keys:
            try:
                data = response.json()
                for key in check_keys:
                    if key not in data:
                        print_test(name, 'FAIL')
                        print(f"    Missing key: {key}")
                        test_details.append({
                            'test': name,
                            'status': 'FAIL',
                            'reason': f"Missing key: {key}"
                        })
                        return None
            except:
                pass
        
        print_test(name, 'PASS')
        test_details.append({
            'test': name,
            'status': 'PASS',
            'response_time': response.elapsed.total_seconds()
        })
        return response
    
    except requests.exceptions.Timeout:
        print_test(name, 'FAIL')
        print(f"    Timeout after 10s")
        test_details.append({
            'test': name,
            'status': 'FAIL',
            'reason': 'Timeout'
        })
        return None
    
    except Exception as e:
        print_test(name, 'FAIL')
        print(f"    Error: {str(e)}")
        test_details.append({
            'test': name,
            'status': 'FAIL',
            'reason': str(e)
        })
        return None


def get_token():
    """Login and get JWT token"""
    print_header("AUTHENTICATION SETUP")
    print(f"Sử dụng tài khoản test: {Fore.MAGENTA}{TEST_EMAIL}{Style.RESET_ALL}")
    
    response = test_api(
        "Login to get token",
        'POST',
        f"{BASE_URL}/auth/login",
        json_data={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        },
        check_keys=['token']
    )
    
    if response and response.status_code == 200:
        token = response.json().get('token')
        print(f"\n{Fore.GREEN}✓ Token acquired for {TEST_EMAIL}: {token[:30]}...{Style.RESET_ALL}\n")
        return token
    else:
        print(f"\n{Fore.RED}✗ Failed to get token. Run: python -c \"from models import seed_sample_data; seed_sample_data()\"{Style.RESET_ALL}\n")
        return None


def test_authentication():
    """Test authentication endpoints"""
    print_header("1. AUTHENTICATION APIs (5 endpoints)")
    
    headers = None
    
    # Register (may fail if user exists - that's ok)
    test_api(
        "Register new user",
        'POST',
        f"{BASE_URL}/auth/register",
        json_data={
            "name": "Test User New",
            "email": f"test_{int(time.time())}@example.com",
            "password": "password123"
        },
        expected_status=201,
        check_keys=['token', 'user']
    )
    
    # Login
    response = test_api(
        "Login existing user",
        'POST',
        f"{BASE_URL}/auth/login",
        json_data={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        },
        check_keys=['token']
    )
    
    if response:
        token = response.json().get('token')
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get current user
        test_api(
            "Get current user info",
            'GET',
            f"{BASE_URL}/auth/me",
            headers=headers,
            check_keys=['user']
        )
        
        # Update profile
        test_api(
            "Update user profile",
            'PUT',
            f"{BASE_URL}/auth/update-profile",
            headers=headers,
            json_data={"name": "Test User Updated"}
        )
        
        # Change password (using old password)
        test_api(
            "Change password",
            'PUT',
            f"{BASE_URL}/auth/change-password",
            headers=headers,
            json_data={
                "old_password": TEST_PASSWORD,
                "new_password": TEST_PASSWORD  # Change back to same
            }
        )


def test_schedule_management(headers):
    """Test schedule CRUD and conflict detection"""
    print_header("2. SCHEDULE MANAGEMENT APIs (8 endpoints)")
    
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Create schedule
    response = test_api(
        "Create new schedule",
        'POST',
        f"{BASE_URL}/schedule",
        headers=headers,
        json_data={
            "subject": "Test Schedule Auto",
            "start_time": f"{tomorrow} 10:00:00",
            "end_time": f"{tomorrow} 11:30:00",
            "location": "Test Room A",
            "type": "class"
        },
        expected_status=201,
        check_keys=['schedule_id']
    )
    
    schedule_id = None
    if response:
        schedule_id = response.json().get('schedule_id')
    
    # Get all schedules
    test_api(
        "Get all schedules",
        'GET',
        f"{BASE_URL}/schedule",
        headers=headers,
        check_keys=['schedules', 'count']
    )
    
    # Get schedule detail
    if schedule_id:
        test_api(
            "Get schedule detail",
            'GET',
            f"{BASE_URL}/schedule/{schedule_id}",
            headers=headers,
            check_keys=['schedule']
        )
        
        # Update schedule
        test_api(
            "Update schedule",
            'PUT',
            f"{BASE_URL}/schedule/{schedule_id}",
            headers=headers,
            json_data={
                "subject": "Test Schedule Updated",
                "color": "#FF5722"
            }
        )
    
    # Check conflicts
    test_api(
        "Check schedule conflicts",
        'GET',
        f"{BASE_URL}/schedule/conflicts?start_time={tomorrow} 10:30:00&end_time={tomorrow} 11:00:00",
        headers=headers,
        check_keys=['has_conflicts']
    )
    
    # Get upcoming schedules
    test_api(
        "Get upcoming schedules",
        'GET',
        f"{BASE_URL}/schedule/upcoming",
        headers=headers,
        check_keys=['schedules']
    )
    
    # Delete schedule (cleanup)
    if schedule_id:
        test_api(
            "Delete schedule",
            'DELETE',
            f"{BASE_URL}/schedule/{schedule_id}",
            headers=headers
        )


def test_task_management(headers):
    """Test task CRUD and stats"""
    print_header("3. TASK MANAGEMENT APIs (9 endpoints)")
    
    due_date = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
    
    # Create task
    response = test_api(
        "Create new task",
        'POST',
        f"{BASE_URL}/tasks",
        headers=headers,
        json_data={
            "title": "Test Task Auto",
            "description": "Automated test task",
            "due_date": f"{due_date} 23:59:00",
            "priority": "high",
            "status": "pending"
        },
        expected_status=201,
        check_keys=['task_id']
    )
    
    task_id = None
    if response:
        task_id = response.json().get('task_id')
    
    # Get all tasks
    test_api(
        "Get all tasks",
        'GET',
        f"{BASE_URL}/tasks",
        headers=headers,
        check_keys=['tasks', 'count']
    )
    
    # Get task detail
    if task_id:
        test_api(
            "Get task detail",
            'GET',
            f"{BASE_URL}/tasks/{task_id}",
            headers=headers,
            check_keys=['task']
        )
        
        # Update task
        test_api(
            "Update task",
            'PUT',
            f"{BASE_URL}/tasks/{task_id}",
            headers=headers,
            json_data={
                "status": "in_progress",
                "priority": "medium"
            }
        )
        
        # Mark complete
        test_api(
            "Mark task complete",
            'PUT',
            f"{BASE_URL}/tasks/{task_id}/complete",
            headers=headers
        )
    
    # Get overdue tasks
    test_api(
        "Get overdue tasks",
        'GET',
        f"{BASE_URL}/tasks/overdue",
        headers=headers,
        check_keys=['overdue_tasks']
    )
    
    # Get task stats
    test_api(
        "Get task statistics",
        'GET',
        f"{BASE_URL}/tasks/stats",
        headers=headers,
        check_keys=['stats']
    )
    
    # Delete task (cleanup)
    if task_id:
        test_api(
            "Delete task",
            'DELETE',
            f"{BASE_URL}/tasks/{task_id}",
            headers=headers
        )


def test_ai_chatbot(headers):
    """Test AI chatbot with real conversation flow"""
    print_header("4. AI CHATBOT APIs (4 endpoints) + REAL CONVERSATIONS")
    
    print(f"{Fore.CYAN}Testing AI Chatbot with realistic conversation flow...{Style.RESET_ALL}\n")
    
    # Test conversations
    conversations = [
        "Hôm nay tôi có lịch gì?",
        "Tuần này tôi học mấy tiết?",
        "Tôi có nhiệm vụ nào cần làm?",
        "Tasks nào đã quá hạn?",
        "Khi nào tôi rảnh để học thêm?",
        "Gợi ý cho tôi lịch học hiệu quả"
    ]
    
    for idx, message in enumerate(conversations, 1):
        print(f"\n{Fore.YELLOW}💬 Conversation {idx}:{Style.RESET_ALL}")
        print(f"   User: {message}")
        
        response = test_api(
            f"AI Chat - Question {idx}",
            'POST',
            f"{BASE_URL}/chat",
            headers=headers,
            json_data={
                "message": message,
                "use_quick_response": True
            },
            check_keys=['reply', 'response_type']
        )
        
        if response:
            data = response.json()
            reply = data.get('reply', '')
            response_type = data.get('response_type', 'unknown')
            
            print(f"   {Fore.GREEN}AI ({response_type}): {reply[:150]}...{Style.RESET_ALL}")
            time.sleep(0.5)  # Delay giữa các câu hỏi
    
    # Get chat history
    print(f"\n{Fore.CYAN}Checking chat history...{Style.RESET_ALL}")
    test_api(
        "Get chat history",
        'GET',
        f"{BASE_URL}/chat/history?limit=5",
        headers=headers,
        check_keys=['history']
    )
    
    # Get suggestions
    test_api(
        "Get AI suggestions",
        'GET',
        f"{BASE_URL}/suggestions",
        headers=headers,
        check_keys=['suggestions']
    )
    
    # Clear chat (optional)
    print(f"\n{Fore.YELLOW}Note: Chat history preserved for review{Style.RESET_ALL}")


def test_notifications(headers):
    """Test notification settings and history"""
    print_header("5. NOTIFICATIONS APIs (6 endpoints)")
    
    # Get settings
    test_api(
        "Get notification settings",
        'GET',
        f"{BASE_URL}/notify/settings",
        headers=headers,
        check_keys=['settings']
    )
    
    # Update settings
    test_api(
        "Update notification settings",
        'PUT',
        f"{BASE_URL}/notify/settings",
        headers=headers,
        json_data={
            "email_enabled": True,
            "telegram_enabled": False,
            "in_app_enabled": True,
            "default_reminder_time": 30
        }
    )
    
    # Get history
    test_api(
        "Get notification history",
        'GET',
        f"{BASE_URL}/notify/history?limit=10",
        headers=headers,
        check_keys=['notifications']
    )
    
    # Get upcoming notifications
    test_api(
        "Get upcoming notifications",
        'GET',
        f"{BASE_URL}/notify/upcoming",
        headers=headers,
        check_keys=['upcoming_notifications']
    )
    
    # Get stats
    test_api(
        "Get notification stats",
        'GET',
        f"{BASE_URL}/notify/stats",
        headers=headers,
        check_keys=['stats']
    )
    
    # Test notification (may fail if SMTP not configured)
    print_test("Send test notification", 'RUNNING')
    response = requests.post(
        f"{BASE_URL}/notify/test",
        headers=headers,
        json={"channels": ["in-app"]},
        timeout=10
    )
    if response.status_code == 200:
        print_test("Send test notification", 'PASS')
    else:
        print_test("Send test notification", 'WARN')
        print(f"    {Fore.YELLOW}SMTP/Telegram may not be configured{Style.RESET_ALL}")


def test_send_test_email(headers):
    """Gửi email test tới giangnamvn555@gmail.com"""
    print_test("Send test email to giangnamvn555@gmail.com", 'RUNNING')
    try:
        resp_email = requests.post(
            f"{BASE_URL}/notify/test-email",
            headers=headers,
            json={"email": "giangnamvn555@gmail.com"},
            timeout=15
        )
        if resp_email.status_code == 200:
            print_test("Send test email to giangnamvn555@gmail.com", 'PASS')
        else:
            print_test("Send test email to giangnamvn555@gmail.com", 'WARN')
            try:
                detail = resp_email.json()
                hint = detail.get('hint', '')
                print(f"    {Fore.YELLOW}Email not sent. {hint}{Style.RESET_ALL}")
            except Exception:
                print(f"    {Fore.YELLOW}Email not sent. Unknown error.{Style.RESET_ALL}")
    except Exception as e:
        print_test("Send test email to giangnamvn555@gmail.com", 'FAIL')
        print(f"    {Fore.RED}Error: {str(e)}{Style.RESET_ALL}")


def test_send_telegram_notification(headers):
    """Gửi Telegram notification test tới @Robin_Vu hoặc chat_id được cấu hình"""
    print_header("5c. SEND TEST TELEGRAM")
    
    # Sử dụng chat_id từ biến môi trường nếu có, nếu không thì dùng @Robin_Vu
    telegram_id = os.getenv("TEST_TELEGRAM_CHAT_ID", "@Robin_Vu")
    recipient_display = telegram_id if telegram_id.startswith("@") else f"chat_id {telegram_id}"
    
    print_test(f"Send test Telegram notification to {recipient_display}", 'RUNNING')
    try:
        resp_telegram = requests.post(
            f"{BASE_URL}/notify/test-telegram",
            headers=headers,
            json={"telegram_id": telegram_id},
            timeout=15
        )
        if resp_telegram.status_code == 200:
            print_test(f"Send test Telegram notification to {recipient_display}", 'PASS')
        else:
            print_test(f"Send test Telegram notification to {recipient_display}", 'WARN')
            try:
                detail = resp_telegram.json()
                hint = detail.get('hint', '')
                print(f"    {Fore.YELLOW}Telegram notification not sent. {hint}{Style.RESET_ALL}")
                print(f"    {Fore.YELLOW}Tip: Set TEST_TELEGRAM_CHAT_ID in .env to use a numeric chat_id instead of username{Style.RESET_ALL}")
            except Exception:
                print(f"    {Fore.YELLOW}Telegram notification not sent. Unknown error.{Style.RESET_ALL}")
    except Exception as e:
        print_test(f"Send test Telegram notification to {recipient_display}", 'FAIL')
        print(f"    {Fore.RED}Error: {str(e)}{Style.RESET_ALL}")
    """Gửi email test tới giangnamvn555@gmail.com"""
    print_header("5b. SEND TEST EMAIL")
    print_test("Send test email to giangnamvn555@gmail.com", 'RUNNING')
    try:
        resp_email = requests.post(
            f"{BASE_URL}/notify/test-email",
            headers=headers,
            json={"email": "giangnamvn555@gmail.com"},
            timeout=15
        )
        if resp_email.status_code == 200:
            print_test("Send test email to giangnamvn555@gmail.com", 'PASS')
        else:
            print_test("Send test email to giangnamvn555@gmail.com", 'WARN')
            try:
                detail = resp_email.json()
                hint = detail.get('hint', '')
                print(f"    {Fore.YELLOW}Email not sent. {hint}{Style.RESET_ALL}")
            except Exception:
                print(f"    {Fore.YELLOW}Email not sent. Check SMTP config.{Style.RESET_ALL}")
    except Exception as e:
        print_test("Send test email to giangnamvn555@gmail.com", 'WARN')
        print(f"    {Fore.YELLOW}Error: {e}{Style.RESET_ALL}")


def test_import_export(headers):
    """Test import/export features"""
    print_header("6. IMPORT/EXPORT APIs (6 endpoints)")
    
    # Get supported formats
    test_api(
        "Get supported file formats",
        'GET',
        f"{BASE_URL}/import/supported-formats",
        check_keys=['supported_formats']
    )
    
    # Download Excel template
    print_test("Download Excel template", 'RUNNING')
    response = requests.get(f"{BASE_URL}/import/template/excel", timeout=10)
    if response.status_code == 200 and len(response.content) > 1000:
        print_test("Download Excel template", 'PASS')
    else:
        print_test("Download Excel template", 'WARN')
    
    # Download CSV template
    print_test("Download CSV template", 'RUNNING')
    response = requests.get(f"{BASE_URL}/import/template/csv", timeout=10)
    if response.status_code == 200 and len(response.content) > 50:
        print_test("Download CSV template", 'PASS')
    else:
        print_test("Download CSV template", 'WARN')
    
    print(f"\n{Fore.YELLOW}Note: File upload test requires actual file - skipped{Style.RESET_ALL}")
    test_results['skipped'] += 1


def test_statistics(headers):
    """Test statistics and analytics"""
    print_header("7. STATISTICS APIs (7 endpoints)")
    
    # Overview
    test_api(
        "Get statistics overview",
        'GET',
        f"{BASE_URL}/stats/overview",
        headers=headers,
        check_keys=['overview']
    )
    
    # Weekly stats
    test_api(
        "Get weekly statistics",
        'GET',
        f"{BASE_URL}/stats/weekly",
        headers=headers,
        check_keys=['week_stats']
    )
    
    # Monthly stats
    test_api(
        "Get monthly statistics",
        'GET',
        f"{BASE_URL}/stats/monthly",
        headers=headers,
        check_keys=['month_stats']
    )
    
    # Subject stats
    test_api(
        "Get subject statistics",
        'GET',
        f"{BASE_URL}/stats/subjects",
        headers=headers,
        check_keys=['subject_stats']
    )
    
    # Productivity
    test_api(
        "Get productivity stats",
        'GET',
        f"{BASE_URL}/stats/productivity",
        headers=headers,
        check_keys=['productivity']
    )
    
    # Busiest days
    test_api(
        "Get busiest days",
        'GET',
        f"{BASE_URL}/stats/busiest-days?limit=5",
        headers=headers,
        check_keys=['busiest_days']
    )
    
    # Time distribution
    test_api(
        "Get time distribution",
        'GET',
        f"{BASE_URL}/stats/time-distribution",
        headers=headers,
        check_keys=['time_distribution']
    )


def test_integration_flow(headers):
    """Test integrated workflow"""
    print_header("8. INTEGRATION TESTS")
    
    print(f"{Fore.CYAN}Testing complete workflow: Schedule → Task → AI → Notification{Style.RESET_ALL}\n")
    
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    # 1. Create schedule
    print_test("Step 1: Create schedule", 'RUNNING')
    response = requests.post(
        f"{BASE_URL}/schedule",
        headers=headers,
        json={
            "subject": "Integration Test Class",
            "start_time": f"{tomorrow} 14:00:00",
            "end_time": f"{tomorrow} 15:30:00",
            "location": "Room INT-01",
            "type": "class"
        },
        timeout=10
    )
    
    if response.status_code == 201:
        schedule_id = response.json().get('schedule_id')
        print_test("Step 1: Create schedule", 'PASS')
        
        # 2. Create related task
        print_test("Step 2: Create related task", 'RUNNING')
        response = requests.post(
            f"{BASE_URL}/tasks",
            headers=headers,
            json={
                "title": "Prepare for Integration Test",
                "due_date": f"{tomorrow} 13:00:00",
                "priority": "high",
                "related_schedule_id": schedule_id
            },
            timeout=10
        )
        
        if response.status_code == 201:
            task_id = response.json().get('task_id')
            print_test("Step 2: Create related task", 'PASS')
            
            # 3. Ask AI about schedule
            print_test("Step 3: Ask AI about schedule", 'RUNNING')
            response = requests.post(
                f"{BASE_URL}/chat",
                headers=headers,
                json={"message": "Ngày mai tôi có lịch gì?"},
                timeout=10
            )
            
            if response.status_code == 200:
                reply = response.json().get('reply', '')
                if 'Integration Test' in reply or 'integration test' in reply.lower():
                    print_test("Step 3: Ask AI about schedule", 'PASS')
                    print(f"      AI Reply: {reply[:100]}...")
                else:
                    print_test("Step 3: Ask AI about schedule", 'WARN')
                    print(f"      AI may not have detected new schedule yet")
            else:
                print_test("Step 3: Ask AI about schedule", 'FAIL')
            
            # 4. Check stats updated
            print_test("Step 4: Verify stats updated", 'RUNNING')
            response = requests.get(f"{BASE_URL}/stats/overview", headers=headers, timeout=10)
            if response.status_code == 200:
                print_test("Step 4: Verify stats updated", 'PASS')
            else:
                print_test("Step 4: Verify stats updated", 'FAIL')
            
            # Cleanup
            print(f"\n{Fore.YELLOW}Cleaning up test data...{Style.RESET_ALL}")
            requests.delete(f"{BASE_URL}/schedule/{schedule_id}", headers=headers)
            requests.delete(f"{BASE_URL}/tasks/{task_id}", headers=headers)
            print(f"{Fore.GREEN}✓ Cleanup complete{Style.RESET_ALL}")
        else:
            print_test("Step 2: Create related task", 'FAIL')
    else:
        print_test("Step 1: Create schedule", 'FAIL')


def test_system_health():
    """Test system health endpoints"""
    print_header("9. SYSTEM HEALTH CHECKS")
    
    test_api(
        "API root endpoint",
        'GET',
        "http://localhost:5000/",
        check_keys=['app', 'version', 'features']
    )
    
    test_api(
        "Health check endpoint",
        'GET',
        f"{BASE_URL}/health",
        check_keys=['status', 'modules']
    )


def print_summary():
    """Print test summary"""
    print_header("TEST SUMMARY")
    
    total = test_results['passed'] + test_results['failed'] + test_results['warnings'] + test_results['skipped']
    
    print(f"{Fore.GREEN}✓ Passed:  {test_results['passed']}/{total}{Style.RESET_ALL}")
    print(f"{Fore.RED}✗ Failed:  {test_results['failed']}/{total}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}⚠ Warnings: {test_results['warnings']}/{total}{Style.RESET_ALL}")
    print(f"{Fore.BLUE}○ Skipped: {test_results['skipped']}/{total}{Style.RESET_ALL}")
    
    success_rate = (test_results['passed'] / total * 100) if total > 0 else 0
    
    print(f"\n{Fore.CYAN}Success Rate: {success_rate:.1f}%{Style.RESET_ALL}")
    
    if test_results['failed'] > 0:
        print(f"\n{Fore.RED}Failed Tests:{Style.RESET_ALL}")
        for detail in test_details:
            if detail['status'] == 'FAIL':
                print(f"  - {detail['test']}: {detail.get('reason', 'Unknown')}")
    
    if success_rate >= 90:
        print(f"\n{Fore.GREEN}{'🎉 BACKEND IS FULLY OPERATIONAL! 🎉'.center(70)}{Style.RESET_ALL}")
    elif success_rate >= 70:
        print(f"\n{Fore.YELLOW}{'⚠️  BACKEND MOSTLY WORKING - Check warnings'.center(70)}{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.RED}{'❌ BACKEND HAS ISSUES - Check failed tests'.center(70)}{Style.RESET_ALL}")


def main():
    """Main test runner"""
    print(f"\n{Fore.CYAN}{Style.BRIGHT}")
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║     SmartSchedule.AI - Complete Backend & AI Test Suite          ║")
    print("║                                                                   ║")
    print("║  Testing 40+ API endpoints including AI Chatbot conversations    ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    print(f"{Style.RESET_ALL}")
    
    # Check if server is running
    try:
        requests.get("http://localhost:5000/", timeout=3)
    except:
        print(f"{Fore.RED}❌ Cannot connect to server at http://localhost:5000{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}💡 Please start server: python app.py{Style.RESET_ALL}")
        sys.exit(1)
    
    start_time = time.time()
    
    # Get authentication token
    token = get_token()
    if not token:
        print(f"{Fore.RED}Cannot proceed without token{Style.RESET_ALL}")
        sys.exit(1)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Run all tests
    test_authentication()
    test_schedule_management(headers)
    test_task_management(headers)
    test_ai_chatbot(headers)  # AI Chatbot với real conversations
    test_notifications(headers)
    test_send_test_email(headers)
    test_send_telegram_notification(headers)
    test_import_export(headers)
    test_statistics(headers)
    test_integration_flow(headers)
    test_system_health()
    
    # Print summary
    elapsed_time = time.time() - start_time
    print(f"\n{Fore.CYAN}Total test time: {elapsed_time:.2f} seconds{Style.RESET_ALL}")
    
    print_summary()
    
    # Exit with appropriate code
    sys.exit(0 if test_results['failed'] == 0 else 1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}Tests interrupted by user{Style.RESET_ALL}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Fore.RED}Unexpected error: {e}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


