"""
Streamlit Registration Page UI for AI Cartoonization Platform
Handles user registration with validation and feedback
"""

import streamlit as st
import re
from backend.auth import register_user, validate_password, validate_email
from backend.auth import PasswordValidationError, EmailValidationError


def get_password_strength(password: str) -> tuple:
    """
    Calculate password strength and return strength level and color
    
    Args:
        password: Password to check
    
    Returns:
        Tuple of (strength_level, color, percentage, description)
    """
    if not password:
        return "None", "#e5e5e5", 0, ""
    
    score = 0
    max_score = 5
    
    # Length check
    if len(password) >= 8:
        score += 1
    if len(password) >= 12:
        score += 1
    
    # Character variety checks
    if re.search(r'[a-z]', password):
        score += 1
    if re.search(r'[A-Z]', password):
        score += 1
    if re.search(r'[0-9]', password):
        score += 1
    if re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', password):
        score += 1
    
    percentage = int((score / max_score) * 100)
    
    if score < 2:
        return "Weak", "#ff4444", percentage, "Very weak password"
    elif score < 3:
        return "Fair", "#ff9800", percentage, "Password is fair"
    elif score < 4:
        return "Good", "#ffc107", percentage, "Good password"
    elif score < 5:
        return "Strong", "#4caf50", percentage, "Strong password"
    else:
        return "Very Strong", "#2196F3", percentage, "Excellent password"


def validate_passwords_match(password: str, confirm_password: str) -> bool:
    """Check if passwords match"""
    return password == confirm_password


def show_registration_page():
    """Display the registration page with all components"""
    
    # Page styling
    st.markdown("""
        <style>
            .register-container {
                max-width: 500px;
                margin: 0 auto;
                padding: 30px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            }
            
            .form-title {
                color: white;
                text-align: center;
                font-size: 2em;
                margin-bottom: 10px;
                font-weight: 700;
            }
            
            .form-subtitle {
                color: rgba(255, 255, 255, 0.9);
                text-align: center;
                margin-bottom: 30px;
                font-size: 1em;
            }
            
            .input-label {
                color: white;
                font-weight: 600;
                margin-top: 15px;
                margin-bottom: 5px;
                display: block;
            }
            
            .password-strength-container {
                margin-top: 10px;
                margin-bottom: 15px;
            }
            
            .strength-bar {
                height: 6px;
                border-radius: 3px;
                background-color: #e5e5e5;
                overflow: hidden;
                margin-bottom: 5px;
            }
            
            .strength-label {
                font-size: 0.85em;
                font-weight: 600;
                display: flex;
                justify-content: space-between;
                color: white;
            }
            
            .form-error {
                color: #ff4444;
                font-size: 0.9em;
                margin-top: 5px;
                padding: 8px 12px;
                background-color: rgba(255, 68, 68, 0.1);
                border-radius: 5px;
                border-left: 3px solid #ff4444;
            }
            
            .form-success {
                color: #4caf50;
                font-size: 0.9em;
                margin-top: 5px;
                padding: 8px 12px;
                background-color: rgba(76, 175, 80, 0.1);
                border-radius: 5px;
                border-left: 3px solid #4caf50;
            }
            
            .checkbox-container {
                background-color: rgba(255, 255, 255, 0.1);
                padding: 15px;
                border-radius: 8px;
                margin: 20px 0;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            
            .checkbox-label {
                color: white;
                font-size: 0.95em;
            }
            
            .terms-link {
                color: #4caf50;
                text-decoration: none;
                font-weight: 600;
            }
            
            .terms-link:hover {
                text-decoration: underline;
            }
            
            .register-btn-container {
                margin-top: 25px;
                width: 100%;
            }
            
            .helper-text {
                color: rgba(255, 255, 255, 0.8);
                font-size: 0.85em;
                margin-top: 3px;
            }
            
            .requirements-list {
                color: rgba(255, 255, 255, 0.9);
                font-size: 0.9em;
                margin-top: 8px;
                padding-left: 20px;
            }
            
            .requirement-item {
                margin: 3px 0;
            }
            
            .requirement-met {
                color: #4caf50;
            }
            
            .requirement-unmet {
                color: #ff9800;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Main container
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
            <div class="register-container">
                <div class="form-title">🎨 Create Account</div>
                <div class="form-subtitle">Join AI Cartoonization Platform</div>
            </div>
        """, unsafe_allow_html=True)
        
        # Initialize session state for password visibility
        if 'show_password' not in st.session_state:
            st.session_state.show_password = False
        if 'show_confirm_password' not in st.session_state:
            st.session_state.show_confirm_password = False
        
        # Username input
        st.markdown('<label class="input-label">👤 Username</label>', unsafe_allow_html=True)
        username = st.text_input(
            "Enter username",
            placeholder="john_doe",
            label_visibility="collapsed",
            key="register_username"
        )
        st.markdown('<p class="helper-text">3-50 characters, alphanumeric, underscore, hyphen</p>', 
                   unsafe_allow_html=True)
        
        # Email input
        st.markdown('<label class="input-label">📧 Email Address</label>', unsafe_allow_html=True)
        email = st.text_input(
            "Enter email",
            placeholder="your@email.com",
            label_visibility="collapsed",
            key="register_email"
        )
        st.markdown('<p class="helper-text">We\'ll send a confirmation link to this email</p>', 
                   unsafe_allow_html=True)
        
        # Password input with show/hide toggle
        st.markdown('<label class="input-label">🔐 Password</label>', unsafe_allow_html=True)
        col_pwd, col_toggle = st.columns([0.9, 0.1])
        
        with col_pwd:
            password_type = "default" if st.session_state.show_password else "password"
            password = st.text_input(
                "Enter password",
                placeholder="SecurePass123!",
                type=password_type,
                label_visibility="collapsed",
                key="register_password"
            )
        
        with col_toggle:
            if st.button("👁️" if st.session_state.show_password else "👁️‍🗨️", 
                        help="Show/Hide password", key="toggle_pwd"):
                st.session_state.show_password = not st.session_state.show_password
                st.rerun()
        
        # Password strength indicator
        if password:
            strength_level, color, percentage, description = get_password_strength(password)
            st.markdown("""
                <div class="password-strength-container">
                    <div class="strength-bar" style="background: linear-gradient(90deg, """ + color + """ """ + str(percentage) + """%, #e5e5e5 """ + str(percentage) + """%)">
                    </div>
                    <div class="strength-label">
                        <span>Password Strength: <strong style="color: """ + color + """;">""" + strength_level + """</strong></span>
                        <span>""" + str(percentage) + """%</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            # Show password requirements checklist
            has_length = len(password) >= 8
            has_upper = bool(re.search(r'[A-Z]', password))
            has_lower = bool(re.search(r'[a-z]', password))
            has_number = bool(re.search(r'[0-9]', password))
            has_special = bool(re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', password))
            
            st.markdown("""
                <div class="requirements-list">
                    <div class="requirement-item """ + ("requirement-met" if has_length else "requirement-unmet") + """">
                        """ + ("✅" if has_length else "❌") + """ Minimum 8 characters
                    </div>
                    <div class="requirement-item """ + ("requirement-met" if has_upper else "requirement-unmet") + """">
                        """ + ("✅" if has_upper else "❌") + """ At least 1 uppercase letter
                    </div>
                    <div class="requirement-item """ + ("requirement-met" if has_lower else "requirement-unmet") + """">
                        """ + ("✅" if has_lower else "❌") + """ At least 1 lowercase letter
                    </div>
                    <div class="requirement-item """ + ("requirement-met" if has_number else "requirement-unmet") + """">
                        """ + ("✅" if has_number else "❌") + """ At least 1 number
                    </div>
                    <div class="requirement-item """ + ("requirement-met" if has_special else "requirement-unmet") + """">
                        """ + ("✅" if has_special else "❌") + """ At least 1 special character (!@#$%^&*...)
                    </div>
                </div>
            """, unsafe_allow_html=True)
        
        # Confirm password input
        st.markdown('<label class="input-label">🔐 Confirm Password</label>', unsafe_allow_html=True)
        col_confirm, col_toggle_confirm = st.columns([0.9, 0.1])
        
        with col_confirm:
            confirm_password_type = "default" if st.session_state.show_confirm_password else "password"
            confirm_password = st.text_input(
                "Confirm password",
                placeholder="SecurePass123!",
                type=confirm_password_type,
                label_visibility="collapsed",
                key="register_confirm_password"
            )
        
        with col_toggle_confirm:
            if st.button("👁️" if st.session_state.show_confirm_password else "👁️‍🗨️",
                        help="Show/Hide password", key="toggle_confirm_pwd"):
                st.session_state.show_confirm_password = not st.session_state.show_confirm_password
                st.rerun()
        
        # Password match indicator
        if password and confirm_password:
            if validate_passwords_match(password, confirm_password):
                st.markdown('<p class="form-success">✅ Passwords match</p>', unsafe_allow_html=True)
            else:
                st.markdown('<p class="form-error">❌ Passwords do not match</p>', unsafe_allow_html=True)
        
        # Terms and Conditions checkbox
        st.markdown("""
            <div class="checkbox-container">
                <div class="checkbox-label">
        """, unsafe_allow_html=True)
        
        terms_agreed = st.checkbox(
            "I agree to the Terms of Service and Privacy Policy",
            value=False
        )
        
        st.markdown("""
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Register button
        st.markdown('<div class="register-btn-container">', unsafe_allow_html=True)
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            register_button = st.button(
                "✨ Create Account",
                use_container_width=True,
                type="primary"
            )
        
        with col_btn2:
            if st.button("← Back", use_container_width=True):
                st.session_state.page = "Home"
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Handle registration form submission
        if register_button:
            # Validate all fields
            errors = []
            
            if not username:
                errors.append("Username is required")
            elif len(username) < 3:
                errors.append("Username must be at least 3 characters")
            elif len(username) > 50:
                errors.append("Username must not exceed 50 characters")
            
            if not email:
                errors.append("Email is required")
            else:
                try:
                    validate_email(email)
                except EmailValidationError as e:
                    errors.append(str(e))
            
            if not password:
                errors.append("Password is required")
            else:
                try:
                    validate_password(password)
                except PasswordValidationError as e:
                    errors.append(str(e))
            
            if not confirm_password:
                errors.append("Please confirm your password")
            elif not validate_passwords_match(password, confirm_password):
                errors.append("Passwords do not match")
            
            if not terms_agreed:
                errors.append("You must agree to the Terms of Service and Privacy Policy")
            
            # Show errors if any
            if errors:
                st.markdown('<div class="form-error">', unsafe_allow_html=True)
                error_message = "❌ Registration failed:\n\n"
                for error in errors:
                    error_message += f"• {error}\n"
                st.error(error_message)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                # Call registration function
                with st.spinner("Creating your account..."):
                    success, message, user_id = register_user(username, email, password)
                
                if success:
                    st.success(f"✅ {message}")
                    st.balloons()
                    # Store user info in session state
                    st.session_state.user_registered = True
                    st.session_state.new_user_id = user_id
                    st.session_state.new_username = username
                    
                    # Show next steps
                    st.info("📧 You should receive a confirmation email shortly. Check your inbox!")
                    
                    # Show login prompt
                    st.markdown("""
                        <div style="background: rgba(76, 175, 80, 0.1); padding: 15px; border-radius: 8px; border-left: 3px solid #4caf50; margin-top: 15px;">
                            <p style="color: #2e7d32; margin: 0;">Ready to login? Use your email and password to access your account.</p>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown('<div class="form-error">', unsafe_allow_html=True)
                    st.error(f"❌ Registration failed:\n\n{message}")
                    st.markdown('</div>', unsafe_allow_html=True)
        
        # Login link
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<p style="text-align: center; color: #666; margin-bottom: 10px;">Already have an account?</p>', unsafe_allow_html=True)
            if st.button("🔐 Login Here", use_container_width=True):
                st.session_state.page = "Login"
                st.rerun()


if __name__ == "__main__":
    show_registration_page()
