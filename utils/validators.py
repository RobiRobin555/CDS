"""
utils/validators.py - Bộ validator dùng chung cho API

Mục tiêu: chuẩn hóa kiểm tra đầu vào cho các route (auth, schedule, notify).
"""

import re
from datetime import datetime


ALLOWED_SCHEDULE_TYPES = {"class", "exam", "meeting", "other"}


def validate_name(name: str):
    if not isinstance(name, str):
        return False, "Name must be a string"
    name = name.strip()
    if len(name) < 2 or len(name) > 60:
        return False, "Name length must be 2-60 characters"
    # Allow letters, spaces, hyphens, apostrophes
    if not re.match(r"^[A-Za-zÀ-ỹ\-'\s]+$", name):
        return False, "Name contains invalid characters"
    return True, "OK"


def validate_color_hex(color: str):
    if color is None:
        return True, "OK"
    if not isinstance(color, str):
        return False, "Color must be a string"
    if not re.match(r"^#(?:[0-9a-fA-F]{3}){1,2}$", color.strip()):
        return False, "Color must be a valid hex (e.g., #3788d8)"
    return True, "OK"


def validate_reminder_minutes(value):
    try:
        ivalue = int(value)
    except (ValueError, TypeError):
        return False, "reminder_time must be an integer"
    if ivalue < 0 or ivalue > 180:
        return False, "reminder_time must be between 0 and 180 minutes"
    return True, "OK"


def validate_schedule_type(value):
    if value is None:
        return True, "OK"
    if value not in ALLOWED_SCHEDULE_TYPES:
        return False, f"type must be one of: {', '.join(sorted(ALLOWED_SCHEDULE_TYPES))}"
    return True, "OK"


def validate_subject(subject: str):
    if not isinstance(subject, str):
        return False, "subject must be a string"
    subject = subject.strip()
    if not subject:
        return False, "subject is required"
    if len(subject) > 200:
        return False, "subject must be <= 200 characters"
    return True, "OK"


def validate_date_str(date_str: str):
    """Validate date string as YYYY-MM-DD (for filters)."""
    if date_str is None:
        return True, "OK"
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True, "OK"
    except Exception:
        return False, "Date must be in YYYY-MM-DD format"


def validate_datetime_str(dt_str: str):
    """Validate datetime string in ISO format 'YYYY-MM-DD HH:MM:SS'."""
    try:
        datetime.fromisoformat(dt_str)
        return True, "OK"
    except Exception:
        return False, "Invalid datetime format. Use: YYYY-MM-DD HH:MM:SS"


def validate_channels(channels):
    """Validate channels input for notifications test route."""
    allowed = {"email", "telegram", "in-app"}
    if channels is None:
        return False, "channels is required"
    if isinstance(channels, str):
        channels = [channels]
    if not isinstance(channels, list):
        return False, "channels must be a list of strings"
    normalized = []
    for ch in channels:
        if not isinstance(ch, str):
            return False, "channels must be strings"
        ch = ch.strip().lower()
        if ch not in allowed:
            return False, "channels must be one of: email, telegram, in-app"
        if ch not in normalized:
            normalized.append(ch)
    if not normalized:
        return False, "channels must not be empty"
    return True, normalized


def validate_telegram_id(value: str):
    """
    Accept either numeric chat_id or username starting with '@' and 5-32 chars.
    """
    if value is None:
        return True, "OK"
    if not isinstance(value, str):
        return False, "telegram_id must be a string"
    v = value.strip()
    if v.isdigit():
        return True, "OK"
    if v.startswith('@'):
        uname = v[1:]
        if 5 <= len(uname) <= 32 and re.match(r"^[A-Za-z0-9_]+$", uname):
            return True, "OK"
        return False, "Telegram username must be 5-32 chars [A-Za-z0-9_]"
    return False, "Telegram id must be numeric chat_id or start with @"


def validate_schedule_payload_basic(data: dict):
    """Basic validation for schedule create/update payload fields (excluding time conflicts)."""
    # subject
    ok, msg = validate_subject(data.get('subject', ''))
    if not ok:
        return False, msg
    # type
    ok, msg = validate_schedule_type(data.get('type'))
    if not ok:
        return False, msg
    # reminder_time
    ok, msg = validate_reminder_minutes(data.get('reminder_time', 30))
    if not ok:
        return False, msg
    # color
    ok, msg = validate_color_hex(data.get('color'))
    if not ok:
        return False, msg
    # location/description length bounds (optional)
    for key, max_len in [("location", 120), ("description", 500)]:
        val = data.get(key)
        if val is not None and isinstance(val, str) and len(val) > max_len:
            return False, f"{key} must be <= {max_len} characters"
    return True, "OK"

