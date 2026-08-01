"""
Streamlit Login Page UI for AI Cartoonization Platform
Handles user authentication with email or username
"""

import streamlit as st
from backend.auth import login_user


def show_login_page():
    """Display the login page with authentication form"""
    
    # Page styling
    st.markdown("""
        <style>
            .login-container {
                max-width: 450px;
                margin: 0 auto;
                padding: 40px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            }
            
            .login-title {
                color: white;
                text-align: center;
                font-size: 2.2em;
                margin-bottom: 10px;
                font-weight: 700;
            }
            
            .login-subtitle {
                color: rgba(255, 255, 255, 0.9);
                text-align: center;
                margin-bottom: 35px;
                font-size: 1em;
            }
            
            .input-label {
                color: white;
                font-weight: 600;
                margin-top: 15px;
                margin-bottom: 8px;
                display: block;
                font-size: 0.95em;
            }
            
            .login-input {
                background-color: rgba(255, 255, 255, 0.95);
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 8px;
                padding: 12px;
                font-size: 1em;
            }
            
            .remember-container {
                background-color: rgba(255, 255, 255, 0.1);
                padding: 12px;
                border-radius: 8px;
                margin: 20px 0;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            
            .remember-label {
                color: white;
                font-size: 0.95em;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            
            .form-error {
                color: #ff4444;
                font-size: 0.95em;
                padding: 12px;
                background-color: rgba(255, 68, 68, 0.15);
                border-radius: 8px;
                border-left: 4px solid #ff4444;
                margin-bottom: 15px;
            }
            
            .form-success {
                color: #4caf50;
                font-size: 0.95em;
                padding: 12px;
                background-color: rgba(76, 175, 80, 0.15);
                border-radius: 8px;
                border-left: 4px solid #4caf50;
                margin-bottom: 15px;
            }
            
            .helper-text {
                color: rgba(255, 255, 255, 0.8);
                font-size: 0.85em;
                margin-top: 5px;
            }
            
            .button-group {
                display: flex;
                gap: 10px;
                margin-top: 25px;
            }
            
            .forgot-password {
                text-align: center;
                margin-top: 15px;
            }
            
            .forgot-link {
                color: rgba(255, 255, 255, 0.8);
                font-size: 0.9em;
                text-decoration: none;
            }
            
            .forgot-link:hover {
                color: white;
                text-decoration: underline;
            }
            
            .signup-prompt {
                text-align: center;
                margin-top: 25px;
                padding-top: 20px;
                border-top: 1px solid rgba(255, 255, 255, 0.2);
            }
            
            .signup-text {
                color: rgba(255, 255, 255, 0.9);
                font-size: 0.95em;
            }
            
            .signup-link {
                color: #4caf50;
                text-decoration: none;
                font-weight: 600;
                margin-left: 5px;
            }
            
            .signup-link:hover {
                text-decoration: underline;
            }
            
            .info-box {
                background-color: rgba(76, 175, 80, 0.15);
                border-left: 4px solid #4caf50;
                color: rgba(255, 255, 255, 0.95);
                padding: 12px;
                border-radius: 8px;
                font-size: 0.9em;
                margin-bottom: 15px;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Main login container
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
            <div class="login-container">
                <div class="login-title">🔐 Sign In</div>
                <div class="login-subtitle">Welcome back to AI Cartoonization Platform</div>
            </div>
        """, unsafe_allow_html=True)
        
        # Initialize session state
        if 'show_password' not in st.session_state:
            st.session_state.show_password = False
        
        if 'login_error' not in st.session_state:
            st.session_state.login_error = None
        
        # Email/Username input
        st.markdown('<label class="input-label">📧 Email or Username</label>', unsafe_allow_html=True)
        identifier = st.text_input(
            "Enter email or username",
            placeholder="your@email.com or username",
            label_visibility="collapsed",
            key="login_identifier"
        )
        st.markdown('<p class="helper-text">Use your registered email address or username</p>', 
                   unsafe_allow_html=True)
        
        # Password input with show/hide toggle
        st.markdown('<label class="input-label">🔑 Password</label>', unsafe_allow_html=True)
        col_pwd, col_toggle = st.columns([0.9, 0.1])
        
        with col_pwd:
            password_type = "default" if st.session_state.show_password else "password"
            password = st.text_input(
                "Enter password",
                placeholder="••••••••",
                type=password_type,
                label_visibility="collapsed",
                key="login_password"
            )
        
        with col_toggle:
            if st.button("👁️" if st.session_state.show_password else "👁️‍🗨️",
                        help="Show/Hide password", key="toggle_login_pwd", use_container_width=True):
                st.session_state.show_password = not st.session_state.show_password
                st.rerun()
        
        # Remember Me checkbox
        st.markdown("""
            <div class="remember-container">
        """, unsafe_allow_html=True)
        
        remember_me = st.checkbox(
            "Remember me for 30 days",
            value=False,
            help="Keep you logged in on this device"
        )
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Display error if exists
        if st.session_state.login_error:
            st.markdown(f'<div class="form-error">{st.session_state.login_error}</div>', 
                       unsafe_allow_html=True)
        
        # Demo account info
        st.markdown("""
            <div class="info-box">
                <strong>Demo Account:</strong><br>
                Email: demo@example.com<br>
                Username: demo_user<br>
                Password: DemoPass123!
            </div>
        """, unsafe_allow_html=True)
        
        # Login button
        col_login, col_back = st.columns(2)
        
        with col_login:
            login_button = st.button(
                "🚀 Sign In",
                use_container_width=True,
                type="primary"
            )
        
        with col_back:
            if st.button("← Back", use_container_width=True):
                st.session_state.page = "Home"
                st.rerun()
        
        # Handle login
        if login_button:
            st.session_state.login_error = None  # Clear previous errors
            
            # Validate inputs
            if not identifier:
                st.session_state.login_error = "❌ Please enter your email or username"
                st.rerun()
            elif not password:
                st.session_state.login_error = "❌ Please enter your password"
                st.rerun()
            else:
                # Attempt login
                with st.spinner("🔍 Verifying credentials..."):
                    success, message, user_data = login_user(identifier, password)
                
                if success:
                    # Store user info in session state
                    st.session_state.user_authenticated = True
                    st.session_state.user_id = user_data['user_id']
                    st.session_state.username = user_data['username']
                    st.session_state.email = user_data['email']
                    st.session_state.created_at = user_data['created_at']
                    st.session_state.last_login = user_data['last_login']
                    
                    # Store remember me preference
                    if remember_me:
                        st.session_state.remember_me = True
                    
                    st.success("✅ Login successful! Redirecting to dashboard...")
                    st.balloons()
                    
                    # Redirect to dashboard
                    st.session_state.page = "Dashboard"
                    st.rerun()
                else:
                    # Show error message
                    st.session_state.login_error = f"❌ {message}"
                    st.rerun()
        
        # Forgot password: replace inert anchor with interactive flow
        if 'show_forgot_form' not in st.session_state:
            st.session_state.show_forgot_form = False

        col_fp1, col_fp2, col_fp3 = st.columns([1, 2, 1])
        with col_fp2:
            if st.button("Forgot your password?", key="forgot_pwd_btn"):
                st.session_state.show_forgot_form = True

            if st.session_state.show_forgot_form:
                st.markdown('<div style="padding:8px 0">', unsafe_allow_html=True)
                reset_email = st.text_input(
                    "Enter your registered email",
                    placeholder="you@email.com",
                    key="forgot_email",
                    label_visibility="collapsed"
                )

                if st.button("Send reset link", key="send_reset_link"):
                    from backend.auth import validate_email
                    from backend.password_reset import send_reset_email
                    try:
                        validate_email(reset_email)
                        try:
                            success, token, message = send_reset_email(reset_email)
                            if success:
                                st.success(f"✅ {message}")
                            else:
                                st.warning(f"⚠️ {message}")
                            st.session_state.show_forgot_form = False
                        except Exception as err:
                            st.error(f"❌ Error sending reset email: {err}")

                    except Exception as e:
                        st.error(str(e))

                if st.button("Cancel", key="cancel_forgot"):
                    st.session_state.show_forgot_form = False

                st.markdown('</div>', unsafe_allow_html=True)
        
        # Sign up prompt
        st.markdown("---")
        col_signup1, col_signup2, col_signup3 = st.columns([1, 2, 1])
        with col_signup2:
            st.markdown('<p style="text-align: center; color: rgba(255, 255, 255, 0.9);">Don\'t have an account?</p>', unsafe_allow_html=True)
            if st.button("📝 Sign up here", use_container_width=True):
                st.session_state.page = "Register"
                st.rerun()


if __name__ == "__main__":
    show_login_page()
