"""
Frontend Module for AI Cartoonization Platform
Contains all Streamlit UI pages
"""

from frontend.login_page import show_login_page
from frontend.register_page import show_registration_page
from frontend.dashboard import show_dashboard
from frontend.style_selection import style_selection_page
from frontend.payment_page import payment_page
from frontend.profile_page import profile_page
from frontend.password_reset_page import show_password_reset_page

__all__ = [
    'show_login_page',
    'show_registration_page',
    'show_dashboard',
    'style_selection_page',
    'payment_page',
    'profile_page'
    'show_password_reset_page'
]
