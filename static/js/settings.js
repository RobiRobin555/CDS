// ============================================
// SETTINGS.JS - Trang cài đặt người dùng
// ============================================

(function() {
  const form = document.getElementById('settings-form');
  const emailEnabledEl = document.getElementById('email_enabled');
  const telegramEnabledEl = document.getElementById('telegram_enabled');
  const inAppEnabledEl = document.getElementById('in_app_enabled');
  const emailReminderEl = document.getElementById('email_reminder_offset');
  const telegramReminderEl = document.getElementById('telegram_reminder_offset');
  const telegramIdEl = document.getElementById('telegram_id');
  const nameEl = document.getElementById('name');
  const themeEl = document.getElementById('theme');
  const applyThemeBtn = document.getElementById('apply-theme');
  const resetBtn = document.getElementById('reset-settings');
  const telegramCurrentWrap = document.getElementById('telegram-current');
  const telegramCurrentValueEl = document.getElementById('telegram_current_value');
  const telegramNotSetEl = document.getElementById('telegram_not_set');
  // Account section elements
  const changePasswordBtn = document.getElementById('change-password-btn');
  const deleteAccountBtn = document.getElementById('delete-account-btn');
  const changePasswordModal = document.getElementById('change-password-modal');
  const deleteAccountModal = document.getElementById('delete-account-modal');
  const oldPasswordEl = document.getElementById('old-password');
  const newPasswordEl = document.getElementById('new-password');
  const confirmPasswordEl = document.getElementById('confirm-password');
  const confirmChangePasswordBtn = document.getElementById('confirm-change-password');
  const cancelChangePasswordBtn = document.getElementById('cancel-change-password');
  const deletePasswordEl = document.getElementById('delete-password');
  const confirmDeleteAccountBtn = document.getElementById('confirm-delete-account');
  const cancelDeleteAccountBtn = document.getElementById('cancel-delete-account');

  // Apply theme immediately and persist to localStorage
  function resolveTheme(value) {
    if (value === 'system') {
      const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
      return prefersDark ? 'dark' : 'light';
    }
    return value === 'dark' ? 'dark' : 'light';
  }

  function applyTheme(value) {
    const computed = resolveTheme(value);
    document.documentElement.setAttribute('data-theme', computed === 'dark' ? 'dark' : 'light');
  }

  function saveTheme(value) {
    try { localStorage.setItem('theme', value); } catch(_) {}
  }

  async function loadSettings() {
    try {
      // Fetch notification settings
      const notify = await api.request('/notify/settings', { method: 'GET' });
      const s = notify?.settings || notify; // handle both shapes
      if (s) {
        emailEnabledEl.checked = !!s.email_enabled;
        telegramEnabledEl.checked = !!s.telegram_enabled;
        inAppEnabledEl.checked = !!s.in_app_enabled;
        emailReminderEl.value = s.email_reminder_offset != null ? s.email_reminder_offset : '';
        telegramReminderEl.value = s.telegram_reminder_offset != null ? s.telegram_reminder_offset : '';
      }

      // Fetch profile
      const meResp = await api.request('/auth/me', { method: 'GET' });
      const me = meResp?.user || meResp; // unwrap { user: {...} }
      if (me) {
        nameEl.value = me.name || '';
        telegramIdEl.value = me.telegram_id || '';
        // Hiển thị username đã lưu (nếu có)
        const saved = (me.telegram_id || '').trim();
        if (telegramCurrentWrap) {
          if (saved) {
            telegramCurrentValueEl.textContent = saved.startsWith('@') ? saved : `@${saved}`;
            telegramCurrentValueEl.style.display = 'inline';
            telegramNotSetEl.style.display = 'none';
          } else {
            telegramCurrentValueEl.textContent = '';
            telegramCurrentValueEl.style.display = 'none';
            telegramNotSetEl.style.display = 'inline';
          }
        }
      }

      // Initialize theme select from localStorage
      const savedTheme = localStorage.getItem('theme') || 'system';
      themeEl.value = savedTheme;
      applyTheme(savedTheme);

    } catch (error) {
      // Error already notified by api.request
      console.error('Load settings failed:', error);
    }
  }

  function validateReminderTimes() {
    const emailVal = parseInt(emailReminderEl.value, 10);
    const telegramVal = parseInt(telegramReminderEl.value, 10);
    if (Number.isNaN(emailVal) || emailVal < 0 || emailVal > 10080) {
      api.showNotification('Thời gian nhắc Email phải từ 0-10080 phút', 'error');
      return false;
    }
    if (Number.isNaN(telegramVal) || telegramVal < 0 || telegramVal > 10080) {
      api.showNotification('Thời gian nhắc Telegram phải từ 0-10080 phút', 'error');
      return false;
    }
    return true;
  }

  async function saveNotificationSettings() {
    if (!validateReminderTimes()) return false;
    // Nhắc người dùng tương tác với bot trước khi bật Telegram
    if (telegramEnabledEl.checked) {
      api.showNotification('Vui lòng mở và nhắn "Start" với bot tại t.me/ScheduleSmartAIbot trước khi bật Telegram', 'info');
    }
    const payload = {
      email_enabled: !!emailEnabledEl.checked,
      telegram_enabled: !!telegramEnabledEl.checked,
      in_app_enabled: !!inAppEnabledEl.checked,
      email_reminder_offset: parseInt(emailReminderEl.value, 10),
      telegram_reminder_offset: parseInt(telegramReminderEl.value, 10)
    };
    await api.request('/notify/settings', {
      method: 'PUT',
      body: JSON.stringify(payload)
    });
    api.showNotification('Đã lưu cài đặt thông báo', 'success');
    return true;
  }

  async function saveProfile() {
    const payload = {
      name: (nameEl.value || '').trim(),
      telegram_id: (telegramIdEl.value || '').trim()
    };
    await api.request('/auth/update-profile', {
      method: 'PUT',
      body: JSON.stringify(payload)
    });
    // Persist name locally for navbar
    try { localStorage.setItem('user_name', payload.name || ''); } catch(_) {}
    api.showNotification('Đã cập nhật hồ sơ', 'success');
    // Cập nhật hiển thị username Telegram hiện tại
    const saved = payload.telegram_id;
    if (telegramCurrentWrap) {
      if (saved) {
        telegramCurrentValueEl.textContent = saved.startsWith('@') ? saved : `@${saved}`;
        telegramCurrentValueEl.style.display = 'inline';
        telegramNotSetEl.style.display = 'none';
      } else {
        telegramCurrentValueEl.textContent = '';
        telegramCurrentValueEl.style.display = 'none';
        telegramNotSetEl.style.display = 'inline';
      }
    }
  }

  // Event: submit form
  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      // Save notify + profile
      await saveNotificationSettings();
      await saveProfile();
      api.showNotification('Đã lưu thành công tất cả cài đặt', 'success');
    } catch (err) {
      console.error('Save settings error:', err);
      api.showNotification(err?.message || 'Lưu cài đặt thất bại', 'error');
    }
  });

  // Event: apply theme button
  applyThemeBtn?.addEventListener('click', () => {
    const value = themeEl.value || 'system';
    applyTheme(value);
    saveTheme(value);
    api.showNotification('Đã áp dụng chế độ màu', 'info');
  });

  // Event: reset settings to defaults
  resetBtn?.addEventListener('click', async () => {
    if (!confirm('Khôi phục cài đặt về mặc định?')) return;
    try {
      // Defaults
      emailEnabledEl.checked = false;
      telegramEnabledEl.checked = false;
      inAppEnabledEl.checked = true;
      emailReminderEl.value = 30;
      telegramReminderEl.value = 30;

      await saveNotificationSettings();

      // Clear optional profile fields
      telegramIdEl.value = '';
      await saveProfile();

      // Theme back to system
      themeEl.value = 'system';
      applyTheme('system');
      saveTheme('system');
      api.showNotification('Đã khôi phục mặc định', 'success');
    } catch (error) {
      api.showNotification(error?.message || 'Khôi phục thất bại', 'error');
    }
  });

  // Event: khi bật Telegram, hiển thị hướng dẫn ngay
  telegramEnabledEl?.addEventListener('change', (e) => {
    if (e.target.checked) {
      api.showNotification('Để nhận Telegram, hãy nhắn "Start" với bot: t.me/ScheduleSmartAIbot', 'info');
    }
  });

  // ===== Account actions =====
  function openModal(el) { if (el) el.style.display = 'block'; }
  function closeModal(el) { if (el) el.style.display = 'none'; }

  changePasswordBtn?.addEventListener('click', () => openModal(changePasswordModal));
  deleteAccountBtn?.addEventListener('click', () => openModal(deleteAccountModal));

  cancelChangePasswordBtn?.addEventListener('click', () => {
    closeModal(changePasswordModal);
    if (oldPasswordEl) oldPasswordEl.value = '';
    if (newPasswordEl) newPasswordEl.value = '';
    if (confirmPasswordEl) confirmPasswordEl.value = '';
  });

  cancelDeleteAccountBtn?.addEventListener('click', () => {
    closeModal(deleteAccountModal);
    if (deletePasswordEl) deletePasswordEl.value = '';
  });

  confirmChangePasswordBtn?.addEventListener('click', async () => {
    const oldPass = (oldPasswordEl?.value || '').trim();
    const newPass = (newPasswordEl?.value || '').trim();
    const confirmPass = (confirmPasswordEl?.value || '').trim();
    if (!oldPass || !newPass) {
      api.showNotification('Vui lòng nhập đầy đủ mật khẩu cũ và mới', 'error');
      return;
    }
    if (newPass !== confirmPass) {
      api.showNotification('Xác nhận mật khẩu không khớp', 'error');
      return;
    }
    try {
      await api.request('/auth/change-password', {
        method: 'PUT',
        body: JSON.stringify({ old_password: oldPass, new_password: newPass })
      });
      api.showNotification('Đổi mật khẩu thành công', 'success');
      closeModal(changePasswordModal);
      if (oldPasswordEl) oldPasswordEl.value = '';
      if (newPasswordEl) newPasswordEl.value = '';
      if (confirmPasswordEl) confirmPasswordEl.value = '';
    } catch (err) {
      console.error('Change password error:', err);
      api.showNotification(err?.message || 'Đổi mật khẩu thất bại', 'error');
    }
  });

  confirmDeleteAccountBtn?.addEventListener('click', async () => {
    const pass = (deletePasswordEl?.value || '').trim();
    if (!pass) {
      api.showNotification('Vui lòng nhập mật khẩu để xác nhận', 'error');
      return;
    }
    if (!confirm('Bạn chắc chắn muốn xóa tài khoản? Hành động này không thể hoàn tác.')) return;
    try {
      await api.request('/auth/delete-account', {
        method: 'DELETE',
        body: JSON.stringify({ password: pass })
      });
      api.showNotification('Tài khoản đã được xóa', 'success');
      // Clear auth and redirect
      try { localStorage.removeItem('jwt_token'); localStorage.removeItem('user_name'); } catch(_) {}
      window.location.href = '/login.html';
    } catch (err) {
      console.error('Delete account error:', err);
      api.showNotification(err?.message || 'Xóa tài khoản thất bại', 'error');
    }
  });

  // Init
  document.addEventListener('DOMContentLoaded', loadSettings);
})();
