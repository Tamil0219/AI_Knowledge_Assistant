"""Password Reset Page for Streamlit frontend.

Supports both legacy token links and a new OTP-based flow:
- Step 1: Enter email and request OTP
- Step 2: Enter OTP + new password to reset
"""
import streamlit as st
from datetime import datetime
from backend.database import DatabaseManager, UserDatabase
from backend.auth import validate_password, hash_password, PasswordValidationError, validate_email
from backend.password_reset import send_otp, verify_otp_and_reset_password


def show_password_reset_page():
    """Render the password reset page supporting OTP and token flows."""
    st.title("🔁 Password Reset")

    # If a reset token is present in query params, keep legacy flow
    token = None
    params = {}
    fn = getattr(st, 'experimental_get_query_params', None)
    if callable(fn):
        params = fn()
    else:
        fn2 = getattr(st, 'get_query_params', None)
        if callable(fn2):
            params = fn2()

    if params and 'reset_token' in params:
        vals = params.get('reset_token')
        if vals:
            token = vals[0]
    if not token and 'reset_token' in st.session_state:
        token = st.session_state.get('reset_token')

    # Legacy token flow (unchanged)
    if token:
        dbm = DatabaseManager()
        user_db = UserDatabase(dbm)

        pr = user_db.get_password_reset(token)
        if not pr:
            st.error("Invalid or expired reset token.")
            return

        # Check used
        if pr.get('used'):
            st.error("This reset link has already been used.")
            return

        # Check expiry
        try:
            expires_at = datetime.fromisoformat(pr.get('expires_at'))
        except Exception:
            st.error("Invalid token expiry format.")
            return

        if expires_at < datetime.utcnow():
            st.error("This reset link has expired.")
            return

        st.markdown("Enter a new password for your account.")

        col1, col2 = st.columns([1, 1])
        with col1:
            new_password = st.text_input("New password", type="password", key="reset_new_pwd")
        with col2:
            confirm_password = st.text_input("Confirm password", type="password", key="reset_confirm_pwd")

        if st.button("Set new password"):
            # Basic checks
            if not new_password or not confirm_password:
                st.error("Please enter and confirm your new password.")
                return
            if new_password != confirm_password:
                st.error("Passwords do not match.")
                return

            # Validate strength
            try:
                validate_password(new_password)
            except PasswordValidationError as e:
                st.error(str(e))
                return

            # Hash and update
            try:
                new_hash = hash_password(new_password)
                updated = user_db.update_password_hash(pr['user_id'], new_hash)
                if not updated:
                    st.error("Failed to update password. Please try again later.")
                    return

                # Mark token used and reset failed attempts
                user_db.mark_password_reset_used(token)
                user_db.reset_failed_attempts(pr['user_id'])

                # Clear token from query params and redirect to login
                st.success("Your password has been reset. Redirecting to login...")
                st.experimental_set_query_params()
                st.session_state.page = "Login"
                st.experimental_rerun()

            except Exception as err:
                st.error(f"Error resetting password: {err}")
        return

    # OTP flow
    st.markdown("If you forgot your password, enter your email to receive a one-time code (OTP).")

    # Keep track of state between steps
    if 'otp_requested' not in st.session_state:
        st.session_state['otp_requested'] = False

    email = st.text_input("Email address", key="reset_email")

    if not st.session_state['otp_requested']:
        if st.button("Send OTP"):
            # Validate email format
            try:
                validate_email(email)
            except Exception as e:
                st.error(str(e))
                return

            success, otp, msg = send_otp(email)
            # For security, message is generic whether email exists or not
            if success:
                st.success(msg)
                st.session_state['otp_requested'] = True
                st.session_state['otp_email'] = email
            else:
                # Logically we still show a generic message, but display error for admins/tests
                st.error(msg)
            return

    # After OTP requested, show OTP + new password form
    if st.session_state.get('otp_requested'):
        st.info("Enter the OTP sent to your email and choose a new password.")

        otp_input = st.text_input("OTP code", key="reset_otp")
        col1, col2 = st.columns([1, 1])
        with col1:
            new_password = st.text_input("New password", type="password", key="otp_new_pwd")
        with col2:
            confirm_password = st.text_input("Confirm password", type="password", key="otp_confirm_pwd")

        if st.button("Reset Password"):
            # Basic checks
            if not otp_input or not new_password or not confirm_password:
                st.error("Please provide the OTP and enter/confirm your new password.")
                return
            if new_password != confirm_password:
                st.error("Passwords do not match.")
                return

            # Validate password strength
            try:
                validate_password(new_password)
            except PasswordValidationError as e:
                st.error(str(e))
                return

            # Hash and call verify
            try:
                new_hash = hash_password(new_password)
                email_for_reset = st.session_state.get('otp_email') or email
                ok, message = verify_otp_and_reset_password(email_for_reset, otp_input, new_hash)
                if ok:
                    st.success(message)
                    # clear state and redirect to login
                    st.session_state['otp_requested'] = False
                    st.session_state.pop('otp_email', None)
                    st.session_state.page = "Login"
                    st.experimental_rerun()
                else:
                    st.error(message)
            except Exception as err:
                st.error(f"Error resetting password: {err}")
