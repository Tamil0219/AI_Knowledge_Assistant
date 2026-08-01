"""
Streamlit Dashboard Page for AI Cartoonization Platform
Displays user dashboard with image history and conversion options
"""

import streamlit as st
from datetime import datetime
from frontend.image_upload import image_upload_page
import sqlite3
import os
from pathlib import Path
from PIL import Image as PILImage
import pandas as pd
import time
import cv2
import numpy as np


DATABASE_FOLDER = Path(__file__).parent.parent / "database"
THUMBNAIL_SIZE = (150, 150)


def get_db_connection():
    """Get database connection."""
    from backend.database import get_db_connection as get_conn
    return get_conn()


def get_user_images(username: str) -> list:
    """Get user's processed images."""
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
        
        images = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return images
    except Exception as e:
        st.error(f"Error fetching images: {str(e)}")
        return []


def get_available_styles_count() -> int:
    """Get count of available cartoon styles."""
    try:
        from frontend.style_selection import STYLES
        return len(STYLES)
    except:
        return 10  # Fallback


def get_user_downloads(username: str) -> list:
    """Get user's download history."""
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
            SELECT * FROM DownloadHistory 
            WHERE user_id = ? 
            ORDER BY download_date DESC LIMIT 50
        """, (user_id,))
        
        downloads = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return downloads
    except Exception as e:
        st.error(f"Error fetching downloads: {str(e)}")
        return []


def process_image_record(image_record: dict, intensity: str = "medium") -> bool:
    """
    Process an image record using the backend image processing pipeline,
    save the processed image to outputs/processed_images and update the DB.

    Returns True on success, False on error.
    """
    try:
        from backend.image_processing import apply_classic_cartoon

        original_path = image_record.get('original_image_path')
        image_id = image_record.get('image_id')
        if not original_path or not os.path.exists(original_path):
            st.error("Original image not found on disk.")
            return False

        out_dir = Path("outputs") / "processed_images"
        out_dir.mkdir(parents=True, exist_ok=True)

        start = time.time()
        cartoon = apply_classic_cartoon(original_path, intensity=intensity)
        duration = time.time() - start

        # Save result
        out_name = f"{Path(original_path).stem}_cartoon_{int(time.time())}.jpg"
        out_path = out_dir / out_name
        success = cv2.imwrite(str(out_path), cartoon)
        if not success:
            st.error("Failed to save processed image.")
            return False

        # Update DB record
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE ImageHistory SET processed_image_path = ?, style_applied = ?, processing_time_seconds = ?, intensity_level = ? WHERE image_id = ?",
            (str(out_path), 'classic', float(duration), intensity, image_id)
        )
        conn.commit()
        conn.close()

        st.success(f"Processed image saved: {out_path.name} ({duration:.1f}s)")
        return True
    except Exception as e:
        st.error(f"Error processing image: {str(e)}")
        return False


def show_dashboard():
    """Display the user dashboard"""

    
    # Check if user is authenticated
    if 'user_authenticated' not in st.session_state or not st.session_state.user_authenticated:
        st.error("Please login first to access the dashboard")
        st.stop()
    
    # Dashboard styling
    st.markdown("""
        <style>
            .dashboard-header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                border-radius: 15px;
                margin-bottom: 30px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            
            .dashboard-title {
                font-size: 2.2em;
                font-weight: 700;
                margin: 0;
            }
            
            .dashboard-subtitle {
                font-size: 1.1em;
                opacity: 0.9;
                margin: 8px 0 0 0;
            }
            
            .user-info {
                background: rgba(255, 255, 255, 0.95);
                padding: 15px;
                border-radius: 8px;
                margin-top: 15px;
                font-size: 0.95em;
                color: #333;
            }
            
            .stat-card {
                background: white;
                padding: 20px;
                border-radius: 10px;
                border-left: 5px solid #667eea;
                text-align: center;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
            }
            
            .stat-number {
                font-size: 2em;
                font-weight: 700;
                color: #667eea;
                margin: 10px 0;
            }
            
            .stat-label {
                color: #666;
                font-size: 0.9em;
            }
            
            .upload-section {
                background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
                border: 2px dashed #667eea;
                padding: 40px;
                border-radius: 10px;
                text-align: center;
                margin: 30px 0;
            }
            
            .upload-icon {
                font-size: 3em;
                margin-bottom: 10px;
            }
            
            .logout-button {
                margin-top: 20px;
            }
            
            .welcome-message {
                color: white;
                font-size: 1.1em;
                margin: 5px 0;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Sidebar logout button
    with st.sidebar:
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            # Clear session state
            st.session_state.user_authenticated = False
            st.session_state.user_id = None
            st.session_state.username = None
            st.session_state.email = None
            st.session_state.page = "Home"
            st.rerun()
    
    # Dashboard header
    st.markdown(f"""
        <div class="dashboard-header">
            <h1 class="dashboard-title">🎨 Welcome to Your Dashboard</h1>
            <p class="dashboard-subtitle">AI Cartoonization Platform</p>
            <p class="welcome-message">Hello, <strong>{st.session_state.username}</strong>! Ready to cartoonize some images?</p>
            <div class="user-info">
                <strong>Email:</strong> {st.session_state.email}<br>
                <strong>Member Since:</strong> {st.session_state.created_at if st.session_state.created_at else 'Just now'}
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Statistics
    col1, col2, col3, col4 = st.columns(4)
    
    # Get actual stats
    user_images = get_user_images(st.session_state.username)
    user_downloads = get_user_downloads(st.session_state.username)
    available_styles = get_available_styles_count()
    
    images_processed = len(user_images)
    conversions_available = len(user_downloads)
    
    with col1:
        st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{images_processed}</div>
                <div class="stat-label">Images Processed</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{conversions_available}</div>
                <div class="stat-label">Downloads</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{available_styles}</div>
                <div class="stat-label">Cartoon Styles</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
            <div class="stat-card">
                <div class="stat-number">Free</div>
                <div class="stat-label">Account Type</div>
            </div>
        """, unsafe_allow_html=True)
    
    # Main content tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📸 Cartoonize Image", "🖼️ Image History", "📥 Downloads", "💳 Payment History", "⚙️ Profile"])
    
    with tab1:
        st.subheader("Upload and Cartoonize Your Image")
        
        # Get user images to check if this is a new account
        user_images = get_user_images(st.session_state.username)
        is_new_user = len(user_images) == 0
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # For new accounts (no images yet), don't show upload here.
            # Force them to use the Image History tab and click "Upload Image Now".
            # For existing accounts, show the upload form directly for convenience.
            if not is_new_user and not st.session_state.get("show_upload_from_history"):
                # Only show for users with images
                image_upload_page()
            elif is_new_user:
                st.info("👋 Welcome! Go to your **Image History** tab and click **📸 Upload Image Now** to get started.")
            elif st.session_state.get("show_upload_from_history"):
                st.info("📤 The upload form is open below in your image history section.")
        
        with col2:
            st.subheader("Cartoon Styles")
            style = st.radio(
                "Select a style",
                ["Classic", "Comic", "Oil Painting", "Pencil Sketch", "Watercolor"],
                label_visibility="collapsed"
            )
            
            # Show conversion button if image is uploaded
            if 'uploaded_image_path' in st.session_state and st.session_state.uploaded_image_path:
                st.markdown("---")
                if st.button("🎨 Convert to Cartoon", use_container_width=True, type="primary"):
                    st.session_state.page = "StyleSelection"
                    st.rerun()
    
    with tab2:
        st.subheader("Your Image History")
        
        if not user_images:
            st.info("📭 No images processed yet. Upload your first image to get started!")
            # clicking the button will show the upload widget directly below
            if st.button("📸 Upload Image Now", use_container_width=True, type="primary"):
                # we stay on dashboard but activate inline upload area
                st.session_state.show_upload_from_history = True
                st.rerun()

            # render upload area if flag is set
            if st.session_state.get("show_upload_from_history"):
                # use a different key prefix so widgets are unique
                image_upload_page(key_prefix="history_")
                # after showing upload page we bail out to avoid drawing the rest of history UI
                return
        else:
            # if images appear again, make sure upload flag is cleared so future visits behave normally
            if st.session_state.get("show_upload_from_history"):
                st.session_state.pop("show_upload_from_history", None)
            st.write(f"**Total Images: {len(user_images)}**")
            st.markdown("---")
            
            # Display images in a grid
            cols_per_row = 4
            cols = st.columns(cols_per_row)
            
            for idx, image_record in enumerate(user_images):
                col = cols[idx % cols_per_row]
                
                with col:
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
                        style = image_record.get('style_applied', 'Unknown')
                        processing_date = image_record.get('processing_date', 'N/A')
                        
                        st.caption(f"**{style}**")
                        if processing_date:
                            st.caption(f"📅 {processing_date[:10]}")
                        
                        # Click to view in profile
                        if st.button("📂 View in Profile", key=f"profile_{idx}", use_container_width=True):
                            st.session_state.page = "Profile"
                            st.session_state.scroll_to_image = idx
                            st.rerun()
                        # Add Process / Re-process action
                        proc_label = "🔄 Re-process" if image_record.get('processed_image_path') else "🎛️ Process"
                        if st.button(proc_label, key=f"process_{idx}", use_container_width=True):
                            with st.spinner("Processing image..."):
                                ok = process_image_record(image_record, intensity='medium')
                                if ok:
                                    st.rerun()
            
            st.markdown("---")
            if st.button("👤 View All in Profile", use_container_width=True, type="secondary"):
                st.session_state.page = "Profile"
                st.rerun()
    
    with tab3:
        st.subheader("📥 Download History")
        
        # Get user downloads
        user_downloads = get_user_downloads(st.session_state.username)
        
        if not user_downloads:
            st.info("📭 No downloads yet. Process and download your first image to get started!")
            if st.button("🎨 Process Image", use_container_width=True, type="primary"):
                st.session_state.page = "StyleSelection"
                st.rerun()
        else:
            st.write(f"**Total Downloads: {len(user_downloads)}**")
            st.markdown("---")
            
            # Display downloads in a table
            download_data = []
            for idx, download in enumerate(user_downloads):
                download_date = download.get('download_date', 'N/A')
                filename = download.get('filename', 'Unknown')
                file_size = download.get('file_size_bytes', 0)
                payment_status = download.get('payment_status', 'unknown')
                
                # Convert file size to human readable format
                if file_size < 1024:
                    size_str = f"{file_size} B"
                elif file_size < 1024 * 1024:
                    size_str = f"{file_size / 1024:.1f} KB"
                else:
                    size_str = f"{file_size / (1024 * 1024):.1f} MB"
                
                # Format date
                if isinstance(download_date, str):
                    date_str = download_date[:10]
                else:
                    date_str = 'N/A'
                
                download_data.append({
                    "Date": date_str,
                    "Filename": filename,
                    "Size": size_str,
                    "Status": payment_status.upper()
                })
            
            # Display as table
            if download_data:
                df = pd.DataFrame(download_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                st.markdown("---")
                
                # Show stats
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    total_downloads = len(user_downloads)
                    st.metric("📥 Total Downloads", total_downloads)
                
                with col2:
                    # Calculate total size downloaded
                    total_size = sum(d.get('file_size_bytes', 0) for d in user_downloads)
                    if total_size < 1024 * 1024:
                        total_size_str = f"{total_size / 1024:.1f} KB"
                    else:
                        total_size_str = f"{total_size / (1024 * 1024):.1f} MB"
                    st.metric("💾 Total Data", total_size_str)
                
                with col3:
                    # Most recent download
                    if user_downloads:
                        recent = user_downloads[0].get('download_date', 'Recently')
                        st.metric("⏱️ Last Download", recent[:10] if isinstance(recent, str) else 'Recently')
    
    with tab4:
        st.subheader("💳 Payment History")
        
        # Payment history info
        st.markdown("""
            <div style="background: rgba(102, 126, 234, 0.1); padding: 15px; border-radius: 8px; border-left: 4px solid #667eea; margin-bottom: 20px;">
                <p style="margin: 0;">View all your transactions and payment records below.</p>
            </div>
        """, unsafe_allow_html=True)
        
        # Table headers
        col1, col2, col3, col4, col5 = st.columns([2, 2, 1.5, 1.5, 1])
        
        with col1:
            st.markdown("**Date**")
        with col2:
            st.markdown("**Order ID**")
        with col3:
            st.markdown("**Amount**")
        with col4:
            st.markdown("**Status**")
        with col5:
            st.markdown("**Action**")
        
        st.markdown("---")
        
        # No transactions yet
        st.info("💰 No payment transactions yet. Your conversions will appear here once you complete a purchase.")
        
        # Payment methods section (only UPI supported)
        st.markdown("### Payment Methods & Balances")

        with st.container():
            st.markdown("""
                <div style="border: 2px solid #ddd; padding: 15px; border-radius: 8px; text-align: center;">
                    <p style="font-size: 2em; margin: 0;">🏦</p>
                    <p style="margin: 10px 0 0 0;"><strong>UPI Payment</strong></p>
                    <p style="color: #666; font-size: 0.9em; margin: 5px 0;">Fast & Secure</p>
                </div>
            """, unsafe_allow_html=True)
        
        # Add payment method toggle
        if st.button("➕ Add Payment Method", use_container_width=True):
            st.session_state.show_add_method = True

        # show UPI input form when requested
        if st.session_state.get("show_add_method"):
            new_id = st.text_input("Enter UPI ID", key="new_upi")
            if st.button("Save UPI ID"):
                st.session_state.stored_upi_id = new_id
                st.success("✅ UPI ID saved")

        if st.session_state.get("stored_upi_id"):
            st.markdown(f"**Saved UPI ID:** {st.session_state.stored_upi_id}")
            # if an order was started, show the amount pending
            if st.session_state.get("current_amount"):
                st.markdown(f"**Amount to pay:** ₹{st.session_state.current_amount/100}")
    
    with tab5:
        st.subheader("👤 Profile Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Personal Information**")
            st.text_input("Username", value=st.session_state.username, disabled=True)
            st.text_input("Email", value=st.session_state.email, disabled=True)
            st.text_input("Member Since", value=str(st.session_state.created_at if st.session_state.created_at else "Just now"), disabled=True)
        
        with col2:
            st.markdown("**Account Preferences**")
            notifications = st.checkbox("Email Notifications", value=True)
            marketing = st.checkbox("Marketing Emails", value=False)
            dark_mode = st.checkbox("Dark Mode", value=False)
        
        st.markdown("---")
        
        # Password and Security
        st.markdown("### 🔒 Security")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔑 Change Password", use_container_width=True):
                st.info("Password change feature coming soon")
        
        with col2:
            if st.button("🔐 Two-Factor Authentication", use_container_width=True):
                st.info("2FA feature coming soon")
        
        st.markdown("---")
        
        # Danger Zone
        st.markdown("### ⚠️ Danger Zone")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 Download My Data", use_container_width=True):
                st.warning("Data export coming soon")
        
        with col2:
            if st.button("❌ Delete Account", use_container_width=True):
                st.warning("Account deletion feature coming soon - please contact support")


if __name__ == "__main__":
    show_dashboard()
