// ============================================
// AUTH.JS - Authentication Helper Functions
// ============================================

/**
 * Authentication utilities for login/register pages
 * Handles form validation, API calls, and redirects
 */

// Check if user is already authenticated
function checkIfLoggedIn() {
    const token = localStorage.getItem('jwt_token');
    if(token) {
        // Already logged in, redirect to dashboard
        window.location.href = '/dashboard.html';
        return true;
    }
    return false;
}

// Validate email format
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// Validate password strength
function validatePassword(password) {
    const errors = [];
    
    if(password.length < 6) {
        errors.push('Mật khẩu phải có ít nhất 6 ký tự');
    }
    
    if(password.length > 50) {
        errors.push('Mật khẩu không được quá 50 ký tự');
    }
    
    return {
        valid: errors.length === 0,
        errors: errors
    };
}

// Calculate password strength (0-5)
function calculatePasswordStrength(password) {
    let strength = 0;
    
    if(password.length >= 6) strength++;
    if(password.length >= 10) strength++;
    if(/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++;
    if(/\d/.test(password)) strength++;
    if(/[^a-zA-Z\d]/.test(password)) strength++;
    
    return strength;
}

// Show/hide password toggle
function setupPasswordToggle(inputId, toggleButtonId) {
    const input = document.getElementById(inputId);
    const button = document.getElementById(toggleButtonId);
    
    if(!input || !button) return;
    
    button.addEventListener('click', function() {
        const type = input.getAttribute('type');
        if(type === 'password') {
            input.setAttribute('type', 'text');
            button.textContent = '🙈';
        } else {
            input.setAttribute('type', 'password');
            button.textContent = '👁️';
        }
    });
}

// Handle login form submission
async function handleLogin(email, password, errorElement, buttonElement) {
    // Validate inputs
    if(!email || !password) {
        showError(errorElement, 'Vui lòng nhập đầy đủ thông tin');
        return false;
    }
    
    if(!isValidEmail(email)) {
        showError(errorElement, 'Email không hợp lệ');
        return false;
    }
    
    // Disable button and show loading
    setButtonLoading(buttonElement, true, 'Đang đăng nhập...');
    hideError(errorElement);
    
    try {
        // Call API
        const result = await api.login(email, password);
        
        if(result && result.token) {
            // Success
            showSuccess('Đăng nhập thành công! Đang chuyển hướng...');
            
            // Redirect after short delay
            setTimeout(() => {
                window.location.href = '/dashboard.html';
            }, 1000);
            
            return true;
        } else {
            throw new Error('Login failed');
        }
    } catch(error) {
        console.error('Login error:', error);
        showError(errorElement, 'Email hoặc mật khẩu không đúng');
        setButtonLoading(buttonElement, false, '🔐 Đăng nhập');
        return false;
    }
}

// Handle register form submission
async function handleRegister(name, email, password, confirmPassword, errorElement, successElement, buttonElement) {
    // Clear previous messages
    hideError(errorElement);
    hideSuccess(successElement);

    // Validate inputs
    if(!name || !email || !password || !confirmPassword) {
        showError(errorElement, 'Vui lòng nhập đầy đủ thông tin');
        return false;
    }
    
    if(name.length < 2) {
        showError(errorElement, 'Họ tên phải có ít nhất 2 ký tự');
        return false;
    }
    
    if(!isValidEmail(email)) {
        showError(errorElement, 'Email không hợp lệ');
        return false;
    }
    
    // Validate password
    const passwordValidation = validatePassword(password);
    if(!passwordValidation.valid) {
        showError(errorElement, passwordValidation.errors[0]);
        return false;
    }
    
    // Check password match
    if(password !== confirmPassword) {
        showError(errorElement, 'Mật khẩu xác nhận không khớp');
        return false;
    }
    
    // Disable button and show loading
    setButtonLoading(buttonElement, true, 'Đang đăng ký...');
    hideError(errorElement);
    hideSuccess(successElement);
    
    try {
        // Call API
        const result = await api.register(name, email, password);
        
        if(result && result.success) {
            // Success
            showSuccess(successElement, 'Đăng ký thành công! Bạn có thể đăng nhập ngay bây giờ.');
            // Clear form fields
            document.getElementById('name').value = '';
            document.getElementById('email').value = '';
            document.getElementById('password').value = '';
            document.getElementById('confirmPassword').value = '';
            setButtonLoading(buttonElement, false, '✨ Đăng ký');
            
            // Optional: Redirect to login after a delay
            setTimeout(() => {
                window.location.href = '/login.html';
            }, 3000); // 3-second delay
            
            return true;
        } else {
            throw new Error(result.message || 'Registration failed');
        }
    } catch(error) {
        console.error('Register error:', error);
        const errorMessage = error.message || 'Email đã được sử dụng hoặc có lỗi xảy ra';
        showError(errorElement, errorMessage);
        setButtonLoading(buttonElement, false, '✨ Đăng ký');
        return false;
    }
}

// Logout user
function logout() {
    if(confirm('Bạn có chắc muốn đăng xuất?')) {
        localStorage.removeItem('jwt_token');
        localStorage.removeItem('user_name');
        localStorage.removeItem('user_email');
        window.location.href = '/login.html';
    }
}

// UI Helper Functions

function showError(element, message) {
    if(!element) return;
    element.textContent = '❌ ' + message;
    element.classList.add('active');
}

function hideError(element) {
    if(!element) return;
    element.classList.remove('active');
}

function showSuccess(elementOrMessage, message) {
    if(typeof elementOrMessage === 'string') {
        // Show toast notification
        const notification = document.createElement('div');
        notification.className = 'notification notification-success';
        notification.textContent = elementOrMessage;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #10b981;
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 0.5rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            z-index: 9999;
            animation: slideIn 0.3s ease;
        `;
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 3000);
    } else {
        // Show in element
        if(!elementOrMessage) return;
        elementOrMessage.textContent = '✅ ' + message;
        elementOrMessage.classList.add('active');
    }
}

function hideSuccess(element) {
    if(!element) return;
    element.classList.remove('active');
}

function setButtonLoading(button, isLoading, text) {
    if(!button) return;
    
    if(isLoading) {
        button.disabled = true;
        button.dataset.originalText = button.textContent;
        button.textContent = text || '⏳ Đang xử lý...';
    } else {
        button.disabled = false;
        button.textContent = text || button.dataset.originalText || 'Submit';
    }
}

// Remember me functionality
function setupRememberMe(checkboxId, emailInputId) {
    const checkbox = document.getElementById(checkboxId);
    const emailInput = document.getElementById(emailInputId);
    if(!checkbox || !emailInput) return;

    // Load saved email
    const savedEmail = localStorage.getItem('remembered_email');
    if(savedEmail) {
        emailInput.value = savedEmail;
        checkbox.checked = true;
    }

    // Save email when checkbox changes
    checkbox.addEventListener('change', function() {
        if(this.checked) {
            localStorage.setItem('remembered_email', emailInput.value);
        } else {
            localStorage.removeItem('remembered_email');
        }
    });
}

function getUserInfo() {
    const name = localStorage.getItem('user_name');
    const email = localStorage.getItem('user_email');
    return { name, email };
}

function isTokenExpired() {
    // Basic check using exp in JWT (if available)
    const token = localStorage.getItem('jwt_token');
    if(!token) return true;
    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        if(payload.exp) {
            return Date.now() >= payload.exp * 1000;
        }
        return false;
    } catch(e) {
        return false;
    }
}

function checkTokenExpiration() {
    if(isTokenExpired()) {
        // Token expired - redirect to login
        localStorage.removeItem('jwt_token');
        window.location.href = '/login.html';
    }
}

setInterval(checkTokenExpiration, 5 * 60 * 1000);

if(typeof module !== 'undefined' && module.exports) {
    module.exports = {
        checkIfLoggedIn,
        isValidEmail,
        validatePassword,
        calculatePasswordStrength,
        handleLogin,
        handleRegister,
        logout,
        getUserInfo,
        isTokenExpired
    };
}