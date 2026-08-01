"""
User Profile Page for AI Cartoonization Platform
Displays user information, processing history, payment history, and account management
"""

import streamlit as st
from PIL import Image as PILImage
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os
from pathlib import Path
import zipfile
import shutil
import io
import hashlib

# Import backend modules
from backend.database import get_db_connection
from backend.download_manager import get_download_history, log_download


DATABASE_FOLDER = Path(__file__).parent.parent / "database"
OUTPUTS_FOLDER = Path(__file__).parent.parent / "outputs"
THUMBNAIL_SIZE = (150, 150)


def get_user_profile(username: str) -> dict:
    """Get user profile information."""
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT username, email, created_at FROM Users WHERE username = ?
        """, (username,))
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return {
                "username": user['username'],
                "email": user['email'],
                "created_at": user['created_at']
            }
        return None
    except Exception as e:
        st.error(f"Error fetching user profile: {str(e)}")
        return None


def get_user_stats(username: str) -> dict:
    """Get user statistics."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get user_id from username
        cursor.execute("""
            SELECT user_id FROM Users WHERE username = ?
        """, (username,))
        user_id_result = cursor.fetchone()
        if not user_id_result:
            return {
                "total_images": 0,
                "total_spent": 0,
                "account_created": None,
                "last_processed": None
            }
        user_id = user_id_result[0]
        
        # Total images processed
        cursor.execute("""
            SELECT COUNT(*) as total FROM ImageHistory WHERE user_id = ?
        """, (user_id,))
        total_images = cursor.fetchone()[0]
        
        # Total amount spent
        cursor.execute("""
            SELECT SUM(amount) as total FROM Transactions 
            WHERE user_id = ? AND status = 'success'
        """, (user_id,))
        result = cursor.fetchone()
        total_spent = (result[0] / 100) if result[0] else 0  # Convert from paise
        
        # Last login (use account creation as first use)
        cursor.execute("""
            SELECT created_at FROM Users WHERE username = ?
        """, (username,))
        user = cursor.fetchone()
        account_created = user[0] if user else None
        
        # Last image processed
        cursor.execute("""
            SELECT processing_date FROM ImageHistory 
            WHERE user_id = ? ORDER BY processing_date DESC LIMIT 1
        """, (user_id,))
        last_image = cursor.fetchone()
        last_processed = last_image[0] if last_image else None
        
        conn.close()
        
        return {
            "total_images": total_images,
            "total_spent": total_spent,
            "account_created": account_created,
            "last_processed": last_processed
        }
    except Exception as e:
        st.error(f"Error fetching user stats: {str(e)}")
        return {
            "total_images": 0,
            "total_spent": 0,
            "account_created": None,
            "last_processed": None
        }


def get_processing_history(username: str) -> list:
    """Get user's image processing history."""
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get user_id from username
        cursor.execute("""
            SELECT user_id FROM Users WHERE username = ?
        """, (username,))
        user_id_result = cursor.fetchone()
        if not user_id_result:
            return []
        user_id = user_id_result[0]
        
        cursor.execute("""
            SELECT * FROM ImageHistory 
            WHERE user_id = ? 
            ORDER BY processing_date DESC
        """, (user_id,))
        
        history = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return history
    except Exception as e:
        st.error(f"Error fetching processing history: {str(e)}")
        return []


def get_payment_history(username: str) -> list:
    """Get user's payment history."""
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get user_id from username
        cursor.execute("""
            SELECT user_id FROM Users WHERE username = ?
        """, (username,))
        user_id_result = cursor.fetchone()
        if not user_id_result:
            return []
        user_id = user_id_result[0]
        
        cursor.execute("""
            SELECT * FROM Transactions 
            WHERE user_id = ? 
            ORDER BY transaction_date DESC
        """, (user_id,))
        
        history = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return history
    except Exception as e:
        st.error(f"Error fetching payment history: {str(e)}")
        return []


def display_profile_header(username: str):
    """Display user profile header with avatar and basic info."""
    profile = get_user_profile(username)
    stats = get_user_stats(username)
    
    if not profile:
        st.error("Unable to load profile information")
        return
    
    # Create avatar from username
    st.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                   padding: 30px; border-radius: 15px; text-align: center; color: white;">
            <h1 style="margin: 0; font-size: 3em;">👤</h1>
            <h2 style="margin: 10px 0 0 0;">{profile['username']}</h2>
            <p style="margin: 5px 0; opacity: 0.9;">{profile['email']}</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Display stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Images Processed",
            stats['total_images'],
            delta="Total all time"
        )
    
    with col2:
        st.metric(
            "Amount Spent",
            f"₹{stats['total_spent']:.2f}",
            delta="Total paid"
        )
    
    with col3:
        if stats['account_created']:
            st.metric(
                "Member Since",
                datetime.fromisoformat(stats['account_created']).strftime("%b %Y")
            )
    
    with col4:
        if stats['last_processed']:
            last_date = datetime.fromisoformat(stats['last_processed'])
            days_ago = (datetime.now() - last_date).days
            st.metric(
                "Last Active",
                f"{days_ago}d ago" if days_ago > 0 else "Today"
            )


def display_processing_history(username: str):
    """Display processing history with gallery and filters."""
    st.subheader("📸 Processing History")
    
    history = get_processing_history(username)
    
    if not history:
        st.info("No images processed yet. Start by uploading an image!")
        return
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        style_filter = st.multiselect(
            "Filter by Style",
            options=list(set([h['style'] for h in history if h.get('style')])),
            default=[]
        )
    
    with col2:
        intensity_filter = st.multiselect(
            "Filter by Intensity",
            options=list(set([h['intensity'] for h in history if h.get('intensity')])),
            default=[]
        )
    
    with col3:
        date_range = st.slider(
            "Filter by Date (days ago)",
            min_value=0,
            max_value=365,
            value=(0, 365),
            step=1
        )
    
    # Apply filters
    filtered_history = history.copy()
    
    if style_filter:
        filtered_history = [h for h in filtered_history if h.get('style') in style_filter]
    
    if intensity_filter:
        filtered_history = [h for h in filtered_history if h.get('intensity') in intensity_filter]
    
    # Date range filter
    now = datetime.now()
    min_date = now - timedelta(days=date_range[1])
    max_date = now - timedelta(days=date_range[0])
    
    filtered_history = [
        h for h in filtered_history
        if h.get('processing_date') and
        min_date <= datetime.fromisoformat(h['processing_date']) <= max_date
    ]
    
    if not filtered_history:
        st.info("No images match the selected filters")
        return
    
    # Display gallery
    st.write(f"**Showing {len(filtered_history)} image(s)**")
    
    # Create thumbnails gallery
    cols_per_row = 4
    cols = st.columns(cols_per_row)
    
    for idx, image_record in enumerate(filtered_history):
        col = cols[idx % cols_per_row]
        
        with col:
            # Try to display thumbnail
            image_path = image_record.get('original_image_path')
            
            with st.container(border=True):
                try:
                    if image_path and os.path.exists(image_path):
                        img = PILImage.open(image_path)
                        img.thumbnail(THUMBNAIL_SIZE)
                        st.image(img, use_container_width=True)
                    else:
                        st.image("https://via.placeholder.com/150?text=Image", use_container_width=True)
                except Exception as e:
                    st.image("https://via.placeholder.com/150?text=Error", use_container_width=True)
                
                # Image details
                style = image_record.get('style', 'Unknown')
                intensity = image_record.get('intensity', 'N/A')
                proc_time = image_record.get('processing_time', 0)
                
                st.caption(f"**{style}**")
                st.caption(f"Intensity: {intensity}")
                st.caption(f"⏱️ {proc_time:.1f}s")
                
                # File sizes
                orig_size = image_record.get('original_size', 0)
                proc_size = image_record.get('processed_size', 0)
                
                st.caption(f"📦 {orig_size/1024:.0f}KB → {proc_size/1024:.0f}KB")
                
                processed_date = datetime.fromisoformat(image_record['processing_date']).strftime("%d %b %Y")
                st.caption(f"📅 {processed_date}")
                
                # Action buttons
                if st.button("🔄 Re-process", key=f"reprocess_{idx}"):
                    st.session_state.reprocess_image = image_record
                    st.session_state.page = "Style Selection"
                    st.rerun()


def display_payment_history(username: str):
    """Display payment history table."""
    st.subheader("💳 Payment History")
    
    payments = get_payment_history(username)
    
    if not payments:
        st.info("No payment history yet")
        return
    
    # Create DataFrame for better display
    payment_data = []
    for p in payments:
        payment_data.append({
            "Date": datetime.fromisoformat(p['created_at']).strftime("%Y-%m-%d %H:%M"),
            "Order ID": p['order_id'][:12] + "..." if len(p['order_id']) > 12 else p['order_id'],
            "Amount": f"₹{p['amount']/100:.2f}",
            "Status": p['status'].upper(),
            "Images": p.get('image_count', '-'),
            "Payment ID": p.get('payment_id', 'N/A')[:12] + "..." if p.get('payment_id') else 'N/A'
        })
    
    df = pd.DataFrame(payment_data)
    
    # Filter options
    col1, col2 = st.columns(2)
    
    with col1:
        status_filter = st.multiselect(
            "Filter by Status",
            options=["SUCCESS", "PENDING", "FAILED"],
            default=["SUCCESS"],
            key="payment_status_filter"
        )
    
    with col2:
        # Amount range filter
        amounts = [p['amount']/100 for p in payments]
        if amounts:
            min_amt, max_amt = st.slider(
                "Amount Range (₹)",
                min_value=int(min(amounts)),
                max_value=int(max(amounts)) + 1,
                value=(int(min(amounts)), int(max(amounts)) + 1),
                key="amount_range"
            )
        
            df = df[df['Amount'].str.replace('₹', '').astype(float) >= min_amt]
            df = df[df['Amount'].str.replace('₹', '').astype(float) <= max_amt]
    
    # Apply status filter
    df = df[df['Status'].isin(status_filter)]
    
    if df.empty:
        st.info("No payments match the selected filters")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Summary statistics
    col1, col2, col3 = st.columns(3)
    
    successful_payments = [p for p in payments if p['status'] == 'success']
    
    with col1:
        st.metric("Total Transactions", len(payments))
    
    with col2:
        st.metric("Successful", len(successful_payments))
    
    with col3:
        total_amount = sum([p['amount']/100 for p in successful_payments])
        st.metric("Total Paid", f"₹{total_amount:.2f}")


def display_download_history(username: str):
    """Display re-download options for paid images."""
    st.subheader("📥 Re-download Paid Images")
    
    download_history = get_download_history(username)
    
    if not download_history:
        st.info("No downloads yet. Purchase and download an image to see them here.")
        return
    
    # Filter only paid downloads
    paid_downloads = [d for d in download_history if d.get('payment_status') == 'paid']
    
    if not paid_downloads:
        st.info("No paid downloads found")
        return
    
    st.write(f"**{len(paid_downloads)} paid image(s) available for re-download**")
    
    # Create list of downloadable files
    for idx, download in enumerate(paid_downloads):
        col1, col2, col3 = st.columns([3, 1, 1])
        
        filename = download.get('filename', 'Unknown')
        download_date = download.get('download_date', 'Unknown')
        file_size = download.get('file_size_bytes', 0)
        file_path = download.get('file_path')
        
        with col1:
            st.write(f"**{filename}**")
            st.caption(f"Downloaded: {download_date} | Size: {file_size/1024/1024:.2f}MB")
        
        with col2:
            # Direct download button
            if file_path and os.path.exists(file_path):
                try:
                    with open(file_path, 'rb') as f:
                        file_data = f.read()
                    
                    st.download_button(
                        label="📥 Download",
                        data=file_data,
                        file_name=filename,
                        mime="image/png",
                        key=f"download_btn_{idx}",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Cannot read file: {str(e)}")
            else:
                st.button("❌ File Missing", disabled=True, use_container_width=True)
        
        with col3:
            if st.button("Remove", key=f"remove_{idx}", use_container_width=True):
                # Option to remove from history
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        DELETE FROM DownloadHistory 
                        WHERE user_id = ? AND filename = ?
                    """, (username, filename))
                    conn.commit()
                    conn.close()
                    st.success("Removed from history")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error removing: {str(e)}")


def display_bulk_download_zip(username: str):
    """Provide option to download all processed images as ZIP."""
    st.subheader("📦 Download All")
    
    history = get_processing_history(username)
    
    if not history:
        st.info("No images to download")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📦 Create ZIP of All Images"):
            try:
                # Create temporary ZIP file
                zip_buffer = io.BytesIO()
                
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for idx, image_record in enumerate(history):
                        image_path = image_record.get('original_image_path')
                        
                        if image_path and os.path.exists(image_path):
                            style = image_record.get('style', 'unknown')
                            intensity = image_record.get('intensity', 'medium')
                            processed_date = datetime.fromisoformat(
                                image_record['processing_date']
                            ).strftime("%Y%m%d")
                            
                            # Create filename
                            file_name = f"{processed_date}_{style}_{intensity}_{idx}.png"
                            
                            # Add file to ZIP
                            try:
                                with open(image_path, 'rb') as f:
                                    zip_file.writestr(file_name, f.read())
                            except Exception as e:
                                st.warning(f"Could not add {image_path}: {str(e)}")
                
                zip_buffer.seek(0)
                
                # Provide download button
                st.download_button(
                    label="📥 Download ZIP File",
                    data=zip_buffer,
                    file_name=f"{username}_images_{datetime.now().strftime('%Y%m%d')}.zip",
                    mime="application/zip",
                    use_container_width=True,
                    type="primary"
                )
                
                st.success(f"✅ ZIP created with {len(history)} images")
            
            except Exception as e:
                st.error(f"Error creating ZIP: {str(e)}")
    
    with col2:
        # Statistics
        total_size = sum([h.get('processed_size', 0) for h in history])
        st.metric(
            "Total Size",
            f"{total_size/1024/1024:.2f} MB",
            delta=f"{len(history)} images"
        )


def display_account_management(username: str):
    """Display account settings (change password, update email)."""
    st.subheader("⚙️ Account Management")
    
    tab1, tab2, tab3 = st.tabs(["Change Password", "2FA & Email", "Delete Account"])
    
    with tab1:
        st.write("**Change Your Password**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            current_password = st.text_input(
                "Current Password",
                type="password",
                key="current_pwd"
            )
        
        new_password = st.text_input(
            "New Password",
            type="password",
            key="new_pwd"
        )
        
        confirm_password = st.text_input(
            "Confirm New Password",
            type="password",
            key="confirm_pwd"
        )
        
        if st.button("🔄 Update Password", use_container_width=True):
            if not current_password or not new_password or not confirm_password:
                st.error("All fields are required")
            elif new_password != confirm_password:
                st.error("Passwords do not match")
            elif len(new_password) < 6:
                st.error("Password must be at least 6 characters")
            else:
                try:
                    # Verify current password and update
                    from backend.auth import verify_password, hash_password
                    
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    
                    cursor.execute(
                        "SELECT password_hash FROM Users WHERE username = ?",
                        (username,)
                    )
                    result = cursor.fetchone()
                    
                    if result and verify_password(current_password, result[0]):
                        new_hash = hash_password(new_password)
                        cursor.execute(
                            "UPDATE Users SET password_hash = ? WHERE username = ?",
                            (new_hash, username)
                        )
                        conn.commit()
                        conn.close()
                        
                        st.success("✅ Password updated successfully!")
                    else:
                        st.error("❌ Current password is incorrect")
                        conn.close()
                
                except Exception as e:
                    st.error(f"Error updating password: {str(e)}")
    
    with tab2:
        st.write("**Two-Factor Authentication (2FA) & Email Management**")
        
        current_email_result = get_user_profile(username)
        current_email = current_email_result['email'] if current_email_result else ''
        
        # 2FA Section
        st.subheader("🔐 Two-Factor Authentication")
        st.info(f"📧 2FA will be sent to: {current_email}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📨 Send OTP via Email", use_container_width=True):
                # Generate OTP
                import random
                import string
                otp = ''.join(random.choices(string.digits, k=6))
                
                # Store OTP in session
                st.session_state[f'otp_{username}'] = otp
                st.session_state[f'otp_time_{username}'] = datetime.now()
                
                # In production, send actual email
                st.success(f"✅ OTP sent to {current_email}")
                st.info(f"**Demo OTP: {otp}** (Valid for 5 minutes)")
        
        with col2:
            if st.session_state.get(f'otp_{username}'):
                otp_input = st.text_input("Enter OTP (6 digits)", key="otp_verify", max_chars=6)
                
                if st.button("✓ Verify OTP", use_container_width=True):
                    otp_time = st.session_state.get(f'otp_time_{username}')
                    if (datetime.now() - otp_time).seconds > 300:
                        st.error("OTP expired. Request a new one.")
                        del st.session_state[f'otp_{username}']
                    elif otp_input == st.session_state[f'otp_{username}']:
                        # Update 2FA status
                        try:
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute(
                                "UPDATE Users SET two_factor_enabled = 1 WHERE username = ?",
                                (username,)
                            )
                            conn.commit()
                            conn.close()
                            st.success("✅ 2FA enabled successfully!")
                            del st.session_state[f'otp_{username}']
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error enabling 2FA: {str(e)}")
                    else:
                        st.error("❌ Incorrect OTP")
        
        # Email Update Section
        st.divider()
        st.subheader("📧 Update Email Address")
        st.write(f"Current Email: **{current_email}**")
        
        new_email = st.text_input("New Email Address", key="new_email_tab2")
        
        if st.button("📧 Update Email", use_container_width=True):
            if not new_email:
                st.error("Email is required")
            elif '@' not in new_email:
                st.error("Please enter a valid email address")
            elif new_email == current_email:
                st.error("New email must be different from current email")
            else:
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    
                    # Check if email already exists
                    cursor.execute(
                        "SELECT username FROM Users WHERE email = ? AND username != ?",
                        (new_email, username)
                    )
                    
                    if cursor.fetchone():
                        st.error("Email already in use")
                    else:
                        cursor.execute(
                            "UPDATE Users SET email = ? WHERE username = ?",
                            (new_email, username)
                        )
                        conn.commit()
                        conn.close()
                        
                        st.success("✅ Email updated successfully!")
                        st.rerun()
                
                except Exception as e:
                    st.error(f"Error updating email: {str(e)}")
    
    with tab3:
        st.warning("⚠️ **Delete Account - Danger Zone**")
        st.write("**Deleting your account will:**")
        st.write("- ❌ Remove all your account data")
        st.write("- ❌ Delete your processing and payment history")
        st.write("- ❌ This action cannot be undone")
        
        confirm = st.checkbox("I understand that this action is permanent")
        
        if confirm:
            password = st.text_input(
                "Enter your password to confirm deletion",
                type="password",
                key="delete_confirm_pwd"
            )
            
            if st.button("🗑️ Delete Account", use_container_width=True, type="secondary"):
                if password:
                    try:
                        from backend.auth import verify_password
                        
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        
                        cursor.execute(
                            "SELECT password_hash FROM Users WHERE username = ?",
                            (username,)
                        )
                        result = cursor.fetchone()
                        
                        if result and verify_password(password, result[0]):
                            # Get user_id first
                            cursor.execute("SELECT user_id FROM Users WHERE username = ?", (username,))
                            user_id_result = cursor.fetchone()
                            user_id = user_id_result[0] if user_id_result else None
                            
                            # Delete user data
                            if user_id:
                                cursor.execute("DELETE FROM DownloadLinks WHERE user_id = ?", (user_id,))
                                cursor.execute("DELETE FROM DownloadHistory WHERE user_id = ?", (user_id,))
                                cursor.execute("DELETE FROM ImageHistory WHERE user_id = ?", (user_id,))
                                cursor.execute("DELETE FROM Transactions WHERE user_id = ?", (user_id,))
                            cursor.execute("DELETE FROM Users WHERE username = ?", (username,))
                            
                            conn.commit()
                            conn.close()
                            
                            st.success("Account deleted successfully")
                            st.session_state.user_authenticated = False
                            st.session_state.page = "Home"
                            st.rerun()
                        else:
                            st.error("Password is incorrect")
                            conn.close()
                    
                    except Exception as e:
                        st.error(f"Error deleting account: {str(e)}")
                else:
                    st.error("Password is required")


def profile_page():
    """Main profile page function."""
    # Check authentication
    if 'user_authenticated' not in st.session_state or not st.session_state.user_authenticated:
        st.error("❌ Please login first to view your profile")
        return
    
    username = st.session_state.get('username')
    
    if not username:
        st.error("Username not found in session")
        return
    
    # Page header
    st.markdown("""
        <style>
            .profile-header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
                text-align: center;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Back to dashboard button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("← Back to Dashboard"):
            st.session_state.page = "Dashboard"
            st.rerun()
    
    with col3:
        if st.button("🚪 Logout"):
            st.session_state.user_authenticated = False
            st.session_state.page = "Home"
            st.rerun()
    
    # Display profile header
    display_profile_header(username)
    
    st.markdown("---")
    
    # Create tabs for different sections (Settings removed - account management disabled)
    tab1, tab2, tab3, tab4 = st.tabs([
        "📸 Processing History",
        "💳 Payment History",
        "📥 Re-download",
        "📦 Bulk Download"
    ])

    with tab1:
        display_processing_history(username)

    with tab2:
        display_payment_history(username)

    with tab3:
        display_download_history(username)

    with tab4:
        display_bulk_download_zip(username)


def profile_settings_page():
    """Render only the Account Management (settings) section."""
    # Check authentication
    if 'user_authenticated' not in st.session_state or not st.session_state.user_authenticated:
        st.error("❌ Please login first to view settings")
        return

    username = st.session_state.get('username')
    if not username:
        st.error("Username not found in session")
        return

    # Simple header and back button
    st.markdown("""
        <style>
            .settings-header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 16px;
                border-radius: 8px;
                margin-bottom: 12px;
                text-align: center;
            }
        </style>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("← Back", key="settings_back"):
            st.session_state.page = "Dashboard"
            st.rerun()

    with col2:
        st.markdown(f"<div class=\"settings-header\"><h2>⚙️ Account Settings for {username}</h2></div>", unsafe_allow_html=True)

    display_account_management(username)


if __name__ == "__main__":
    profile_page()
