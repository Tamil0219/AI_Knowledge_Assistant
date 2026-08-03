import streamlit as st
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Defensive shim: ensure query-param helpers exist on older/newer Streamlit builds
if not hasattr(st, 'experimental_get_query_params'):
    setattr(st, 'experimental_get_query_params', lambda: {})
if not hasattr(st, 'get_query_params'):
    setattr(st, 'get_query_params', lambda: {})
import os
from backend.database import initialize_database
from frontend import show_login_page, show_registration_page, show_dashboard, payment_page, style_selection_page, profile_page, show_password_reset_page
from frontend.profile_page import profile_settings_page

# Initialize database on startup
initialize_database()

# Configure page settings
st.set_page_config(
    page_title="AI Cartoonization Platform",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'page' not in st.session_state:
    st.session_state.page = "Home"

if 'user_authenticated' not in st.session_state:
    st.session_state.user_authenticated = False

# Custom CSS for professional styling
st.markdown("""
    <style>
        :root {
            --primary-color: #6366f1;
            --secondary-color: #8b5cf6;
            --background-color: #f8fafc;
            --text-color: #1e293b;
        }
        
        .main {
            background-color: var(--background-color);
        }
        
        .stTitle {
            color: var(--text-color);
            font-size: 3em;
            font-weight: 700;
            margin-bottom: 20px;
        }
        
        .welcome-message {
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            color: white;
            padding: 40px;
            border-radius: 12px;
            text-align: center;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        .welcome-message h2 {
            font-size: 1.8em;
            margin-bottom: 15px;
        }
        
        .welcome-message p {
            font-size: 1.1em;
            line-height: 1.6;
        }
        
        .feature-box {
            background: white;
            padding: 20px;
            border-radius: 10px;
            border-left: 5px solid #6366f1;
            margin-bottom: 15px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }
        
        .feature-box h4 {
            color: #1e293b;
            font-size: 1.2em;
            margin: 0 0 10px 0;
        }
        
        .feature-box p {
            color: #64748b;
            font-size: 1em;
            margin: 0;
        }
        
        .nav-button {
            width: 100%;
            padding: 12px;
            margin: 8px 0;
            border-radius: 8px;
            font-weight: 600;
            border: none;
            cursor: pointer;
            transition: all 0.3s ease;
        }
    </style>
""", unsafe_allow_html=True)

# Sidebar Navigation
with st.sidebar:
    st.markdown("## 🎨 AI Cartoonization")
    
    if st.session_state.user_authenticated:
        # Show user info if authenticated
        st.markdown(f"**{st.session_state.username}**")
        st.caption(st.session_state.email)
        st.markdown("---")
        
        # Navigation for authenticated users
        st.markdown("### Navigation")
        if st.button("🏠 Dashboard", use_container_width=True, key="nav_dashboard"):
            st.session_state.page = "Dashboard"
            st.rerun()
        
        if st.button("� Profile", use_container_width=True, key="nav_profile"):
            st.session_state.page = "Profile"
            st.rerun()
        
        if st.button("�🖼️ My Images", use_container_width=True, key="nav_images"):
            st.session_state.page = "Images"
            st.rerun()
        
        if st.button("⚙️ Settings", use_container_width=True, key="nav_settings"):
            st.session_state.page = "ProfileSettings"
            st.rerun()
        
        st.markdown("---")
        
        if st.button("🚪 Logout", use_container_width=True, key="nav_logout"):
            st.session_state.user_authenticated = False
            st.session_state.user_id = None
            st.session_state.username = None
            st.session_state.email = None
            st.session_state.page = "Home"
            st.rerun()
    else:
        # Navigation for unauthenticated users
        st.markdown("### Navigation")
        if st.button("🏠 Home", use_container_width=True, key="nav_home"):
            st.session_state.page = "Home"
            st.rerun()
        
        if st.button("🔐 Login", use_container_width=True, key="nav_login"):
            st.session_state.page = "Login"
            st.rerun()
        
        if st.button("📝 Register", use_container_width=True, key="nav_register"):
            st.session_state.page = "Register"
            st.rerun()
    
    st.markdown("---")
    
    # Additional sidebar info
    st.markdown("""
    ### About
    **AI Cartoonization Platform** transforms your photos into stunning cartoon artwork using advanced AI technology.
    
    ### Features
    - 🎨 High-quality cartoon conversion
    - 💫 Multiple style options
    - ⚡ Fast processing
    - 🔒 Secure image handling
    """)
    
    st.markdown("---")
    st.caption("Version 1.0.0 | AI Cartoon App 2026")

# Main Content Area - Route based on session state
# Safely detect reset token in query params and route to reset page
def _safe_get_query_params():
    # Use getattr to avoid AttributeError during attribute access
    fn = getattr(st, 'experimental_get_query_params', None)
    if callable(fn):
        return fn()
    fn2 = getattr(st, 'get_query_params', None)
    if callable(fn2):
        return fn2()
    return {}

params = _safe_get_query_params()
if params and params.get('reset_token'):
    st.session_state.reset_token = params['reset_token'][0]
    st.session_state.page = "ResetPassword"

if st.session_state.user_authenticated:
    # User is logged in - show appropriate page
    if st.session_state.page == "Payment":
        payment_page()
    elif st.session_state.page == "StyleSelection":
        style_selection_page()
    elif st.session_state.page == "Profile":
        profile_page()
    elif st.session_state.page == "ProfileSettings":
        profile_settings_page()
    else:
        show_dashboard()
elif st.session_state.page == "Login":
    show_login_page()
elif st.session_state.page == "Register":
    show_registration_page()
elif st.session_state.page == "ResetPassword":
    show_password_reset_page()
else:
    # Default: Home page
    st.title("🎨 AI Cartoonization Platform")
    
    # Welcome message section
    st.markdown("""
    <div class="welcome-message">
        <h2>Welcome to AI Cartoonization Platform</h2>
        <p>Transform your ordinary photos into extraordinary cartoon masterpieces using cutting-edge artificial intelligence.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Features section
    st.markdown("## Why Choose Our Platform?")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="feature-box">
            <h4>🚀 Lightning Fast</h4>
            <p>Get your cartoon conversion in seconds, not minutes.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="feature-box">
            <h4>🎯 Precision Quality</h4>
            <p>Advanced AI ensures stunning results with perfect details.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="feature-box">
            <h4>🔒 Privacy First</h4>
            <p>Your images are secure and never stored permanently.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Call to action
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("📝 New user? Register for a free account to get started!")
    
    with col2:
        st.success("✅ Ready to cartoonize? Login to upload your photos!")
    
    # Getting started section
    st.markdown("## Getting Started")
    with st.expander("How to use the platform"):
        st.markdown("""
        1. **Register** - Create a free account to unlock all features
        2. **Login** - Access your account and dashboard
        3. **Upload** - Choose an image from your device
        4. **Customize** - Select your preferred cartoon style
        5. **Convert** - Watch as AI transforms your photo
        6. **Download** - Save your cartoon artwork
        """)
    
    # Action buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📝 Get Started - Register", use_container_width=True, type="primary"):
            st.session_state.page = "Register"
            st.rerun()
    
    with col2:
        if st.button("🔐 Login to Continue", use_container_width=True):
            st.session_state.page = "Login"
            st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #64748b; font-size: 0.9em;">
    <p>© 2026 AI Cartoonization Platform. All rights reserved.</p>
    <p>Version 1.0.0 | Built with ❤️ using Streamlit</p>
</div>
""", unsafe_allow_html=True)
