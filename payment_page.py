"""
Payment Page for AI Cartoonization Platform
Handles payment processing and download of processed images
"""

import streamlit as st
from PIL import Image as PILImage
import cv2
import numpy as np
from datetime import datetime
import json

# Import payment and download modules
from backend.payment import create_payment_order, confirm_payment, get_payment_statistics, verify_payment_before_download
from backend.download_manager import prepare_download, OUTPUTS_FOLDER, create_download_link, log_download, mark_download_link_used

import qrcode
from io import BytesIO


# Payment plans
PAYMENT_PLANS = {
    "premium": {
        "amount_key": "premium",
        "price": 10,
        "name": "Premium - Single Image",
        "description": "Download 1 high-quality image without watermark",
        "features": [
            "✓ Remove watermark",
            "✓ High quality export",
            "✓ Support our platform",
            "✓ One-time purchase"
        ]
    },
    "pro": {
        "amount_key": "pro",
        "price": 50,
        "name": "Pro - 5 Images Bundle",
        "description": "Download 5 images without watermark",
        "features": [
            "✓ 5 high-quality exports",
            "✓ Remove watermarks",
            "✓ Best value",
            "✓ Valid for 30 days"
        ]
    }
}


def cv2_to_pil(cv2_image: np.ndarray) -> PILImage.Image:
    """
    Convert OpenCV (BGR) image to PIL Image (RGB).
    
    Args:
        cv2_image: Image in BGR format
        
    Returns:
        PILImage.Image: Image in RGB format
    """
    rgb_image = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB)
    return PILImage.fromarray(rgb_image)


def generate_upi_qr(upi_id: str, amount_paise: int) -> BytesIO:
    """Generate a UPI QR code stream for the given UPI ID and amount.

    The UPI deep link will include the payment address and amount in rupees.
    """
    amount_rupees = amount_paise / 100
    upi_link = f"upi://pay?pa={upi_id}&pn=AI+Cartoon&am={amount_rupees:.2f}&cu=INR"
    img = qrcode.make(upi_link)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def display_payment_plans():
    """Display available payment plans."""
    st.subheader("💳 Select Your Plan")
    
    col1, col2 = st.columns(2)
    
    with col1:
        with st.container():
            st.markdown("""
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                           padding: 20px; border-radius: 10px; color: white;">
                    <h3 style="margin: 0;">🎨 Premium</h3>
                    <p style="margin: 5px 0; font-size: 28px; font-weight: bold;">₹10</p>
                    <p style="margin: 10px 0; opacity: 0.9;">Single Image Download</p>
                </div>
            """, unsafe_allow_html=True)
            
            plan = PAYMENT_PLANS["premium"]
            for feature in plan["features"]:
                st.markdown(feature, unsafe_allow_html=True)
            
            if st.button("🛒 Choose Premium", use_container_width=True, key="plan_premium"):
                st.session_state.selected_plan = "premium"
                st.rerun()
    
    with col2:
        with st.container():
            st.markdown("""
                <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                           padding: 20px; border-radius: 10px; color: white;">
                    <h3 style="margin: 0;">⭐ Pro (Best Value)</h3>
                    <p style="margin: 5px 0; font-size: 28px; font-weight: bold;">₹50</p>
                    <p style="margin: 10px 0; opacity: 0.9;">5 Images Bundle</p>
                </div>
            """, unsafe_allow_html=True)
            
            plan = PAYMENT_PLANS["pro"]
            for feature in plan["features"]:
                st.markdown(feature, unsafe_allow_html=True)
            
            if st.button("🛒 Choose Pro", use_container_width=True, key="plan_pro"):
                st.session_state.selected_plan = "pro"
                st.rerun()


def display_order_summary():
    """Display order summary with image details."""
    if 'processed_image' not in st.session_state or st.session_state.processed_image is None:
        st.warning("❌ No processed image found. Please process an image first.")
        return False
    
    if 'selected_plan' not in st.session_state:
        st.warning("⚠️ Please select a payment plan first.")
        return False
    
    st.subheader("📋 Order Summary")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown("**Image Details**")
        
        # Display processed image
        processed_image = st.session_state.processed_image
        if len(processed_image.shape) == 2:  # Grayscale
            st.image(processed_image, use_container_width=True, caption="Your Processed Image", output_format="auto")
        else:  # BGR
            image_rgb = cv2.cvtColor(processed_image, cv2.COLOR_BGR2RGB)
            st.image(image_rgb, use_container_width=True, caption="Your Processed Image", output_format="RGB")
    
    with col2:
        st.write("")  # Spacer
        st.markdown("**Details**")
        
        # Get image info
        h, w = processed_image.shape[:2]
        st.caption(f"📐 Size: {w}×{h}px")
        st.caption(f"🎨 Style: {st.session_state.processed_style if 'processed_style' in st.session_state else 'Unknown'}")
        
        if 'selected_intensity' in st.session_state:
            st.caption(f"💫 Intensity: {st.session_state.selected_intensity}")
    
    with col3:
        st.write("")  # Spacer
        st.markdown("**Pricing**")
        
        plan = PAYMENT_PLANS[st.session_state.selected_plan]
        st.metric("Plan", plan["name"].split(" - ")[0])
        st.metric("Price", f"₹{plan['price']}")
    
    st.markdown("---")
    return True


def initiate_payment():
    """Initiate payment based on the selected method (UPI or Card)."""
    if 'user_authenticated' not in st.session_state or not st.session_state.user_authenticated:
        st.error("❌ You must be logged in to make a payment.")
        return
    
    if 'selected_plan' not in st.session_state:
        st.error("❌ Please select a payment plan first.")
        return
    
    try:
        plan = PAYMENT_PLANS[st.session_state.selected_plan]
        upi_id = st.session_state.get("upi_id")

        if not upi_id:
            st.error("❌ Please enter your UPI ID before proceeding.")
            return

        order_result = create_payment_order(
            user_id=st.session_state.username,
            amount_key=plan["amount_key"],
            description=f"{plan['name']} - AI Cartoonization",
            image_count=1 if st.session_state.selected_plan == "premium" else 5,
            payment_method="upi",
            upi_id=upi_id
        )

        if not order_result["success"]:
            st.error(f"❌ Failed to create payment order: {order_result['status']}")
            return

        # Store order details in session
        st.session_state.current_order_id = order_result["order_id"]
        st.session_state.current_amount = order_result["amount"]
        st.session_state.key_id = order_result.get("key_id")
        st.session_state.payment_method = "upi"

        # show QR code or instructions
        qr_buf = generate_upi_qr(upi_id, order_result["amount"])
        st.image(qr_buf, caption="Scan this QR code with your UPI app to pay", use_column_width=True)
        st.info(f"You can also send money directly to **{upi_id}** using any UPI app.")
        if st.button("✅ I have completed the payment"):
            st.session_state.payment_successful = True
            st.session_state.payment_id = order_result["order_id"]
            st.success("✅ Payment recorded (mock). Showing success page...")
            st.rerun()

        return order_result

    except Exception as e:
        st.error(f"❌ Error initiating payment: {str(e)}")


def display_payment_success():
    """Display payment success confirmation."""
    st.markdown("""
        <div style="background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%); 
                   padding: 30px; border-radius: 15px; text-align: center; color: white;">
            <h2 style="margin: 0; color: #1e293b;">✅ Payment Successful!</h2>
            <p style="margin: 10px 0; font-size: 1.1em; color: #1e293b;">Thank you for your purchase</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Display transaction details
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Transaction ID",
            st.session_state.payment_id[:12] + "..." if len(st.session_state.payment_id) > 12 else st.session_state.payment_id
        )
    
    with col2:
        st.metric("Amount Paid", f"₹{st.session_state.current_amount / 100}")
    
    with col3:
        st.metric(
            "Date",
            datetime.now().strftime("%Y-%m-%d %H:%M")
        )
    
    st.markdown("---")
    
    # Show download button
    st.subheader("📥 Your Download")
    
    try:
        # Verify payment before allowing download
        verification = verify_payment_before_download(st.session_state.username)
        
        if not verification["authorized"]:
            st.error(f"⚠️ Payment verification failed: {verification['message']}")
            return
        
        st.success(f"✅ Payment verified! Download authorized.")
        
        # Prepare download
        processed_image = st.session_state.processed_image
        
        download_result = prepare_download(
            image=processed_image,
            user_id=st.session_state.username,
            original_filename="cartoon_image.jpg",
            style=st.session_state.processed_style if 'processed_style' in st.session_state else "Unknown",
            output_format="png",
            watermark=False,  # No watermark for paid
            intensity=st.session_state.selected_intensity if 'selected_intensity' in st.session_state else "medium",
            processing_time=st.session_state.processing_time if 'processing_time' in st.session_state else 0.0,
            payment_status="paid"
        )
        
        if download_result["success"]:
            # Create temporary download link
            link_result = create_download_link(
                user_id=st.session_state.username,
                file_path=download_result["file_path"],
                filename=download_result["filename"],
                expiry_hours=1
            )
            
            if link_result["success"]:
                # Log the download
                log_download(
                    user_id=st.session_state.username,
                    file_path=download_result["file_path"],
                    filename=download_result["filename"],
                    payment_status="paid",
                    order_id=st.session_state.current_order_id if 'current_order_id' in st.session_state else None
                )
                
                # Read file for download
                with open(download_result["file_path"], "rb") as f:
                    file_data = f.read()
                
                st.download_button(
                    label="📥 Download High-Quality Image (PNG)",
                    data=file_data,
                    file_name=download_result["filename"],
                    mime="image/png",
                    use_container_width=True,
                    type="primary"
                )
                
                st.success(f"✅ File ready: {download_result['filename']}")
                st.caption(f"Size: {download_result['file_size'] / 1024:.1f} KB")
                
                # Display download link info
                with st.expander("ℹ️ Download Link Information"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Link Token", link_result["token"][:16] + "...")
                    with col2:
                        st.metric("Expires At", link_result["expires_at"][-8:])
            else:
                st.error(f"Error creating download link: {link_result['status']}")
        else:
            st.error(f"Error preparing download: {download_result['status']}")
    
    except Exception as e:
        st.error(f"Error processing download: {str(e)}")
    
    st.markdown("---")
    
    # Action buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🎨 Process Another Image", use_container_width=True):
            st.session_state.processed_image = None
            st.session_state.payment_successful = False
            st.rerun()
    
    with col2:
        if st.button("📊 View Payment History", use_container_width=True):
            st.session_state.show_payment_history = True
            st.rerun()
    
    with col3:
        if st.button("🏠 Return to Dashboard", use_container_width=True):
            st.session_state.page = "Dashboard"
            st.rerun()


def display_payment_failure():
    """Display payment failure message."""
    st.markdown("""
        <div style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); 
                   padding: 30px; border-radius: 15px; text-align: center; color: white;">
            <h2 style="margin: 0; color: #1e293b;">❌ Payment Failed</h2>
            <p style="margin: 10px 0; font-size: 1.1em; color: #1e293b;">Unfortunately, your payment could not be processed</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    if 'failure_reason' in st.session_state:
        st.error(f"Reason: {st.session_state.failure_reason}")
    
    st.info("""
    **What can you do?**
    - Check your internet connection
    - Try a different payment method
    - Ensure your payment method has sufficient balance
    - Contact support if the problem persists
    """)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Retry Payment", use_container_width=True, type="primary"):
            st.session_state.payment_successful = False
            st.session_state.payment_failed = False
            st.rerun()
    
    with col2:
        if st.button("🏠 Return to Dashboard", use_container_width=True):
            st.session_state.page = "Dashboard"
            st.rerun()


def display_payment_history():
    """Display user's payment history."""
    st.subheader("📊 Payment History")
    
    try:
        stats = get_payment_statistics(st.session_state.username)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Spent",
                f"₹{stats['total_spent_rupees']:.2f}"
            )
        
        with col2:
            st.metric(
                "Successful Payments",
                stats['successful_payments']
            )
        
        with col3:
            st.metric(
                "Failed Payments",
                stats['failed_payments']
            )
        
        with col4:
            st.metric(
                "Images Downloaded",
                stats['total_images_purchased']
            )
        
        st.markdown("---")
        st.info("Detailed transaction history can be viewed in your account settings.")
        
    except Exception as e:
        st.error(f"Error loading payment history: {str(e)}")


def payment_page():
    """
    Main payment page component.
    """
    # Page header
    st.markdown("""
        <style>
            .payment-header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                border-radius: 15px;
                margin-bottom: 30px;
                text-align: center;
            }
            
            .payment-title {
                font-size: 2em;
                font-weight: 700;
                margin: 0;
            }
            
            .payment-subtitle {
                font-size: 1.1em;
                opacity: 0.9;
                margin: 10px 0 0 0;
            }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""
        <div class="payment-header">
            <h1 class="payment-title">💳 Proceed to Payment</h1>
            <p class="payment-subtitle">Download your high-quality cartoon image</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    if 'selected_plan' not in st.session_state:
        st.session_state.selected_plan = None
    
    if 'payment_successful' not in st.session_state:
        st.session_state.payment_successful = False
    
    if 'payment_failed' not in st.session_state:
        st.session_state.payment_failed = False
    
    if 'show_payment_history' not in st.session_state:
        st.session_state.show_payment_history = False
    
    # Check authentication
    if 'user_authenticated' not in st.session_state or not st.session_state.user_authenticated:
        st.error("❌ Please login first to proceed with payment.")
        return
    
    # Display payment history if requested
    if st.session_state.show_payment_history:
        display_payment_history()
        if st.button("← Back to Payment"):
            st.session_state.show_payment_history = False
            st.rerun()
        return
    
    # Show success page
    if st.session_state.payment_successful and 'payment_id' in st.session_state:
        display_payment_success()
        return
    
    # Show failure page
    if st.session_state.payment_failed:
        display_payment_failure()
        return
    
    # Main payment flow
    # Display payment plans
    display_payment_plans()
    
    st.markdown("---")
    
    # Display order summary if plan is selected
    if st.session_state.selected_plan:
        if not display_order_summary():
            return
        
        # currently only UPI payments are supported
        st.markdown("### 🪪 Payment Method")
        st.text_input(
            "Enter your UPI ID (example@upi)",
            key="upi_id",
            value=st.session_state.get("stored_upi_id", "")
        )
        
        st.markdown("---")
        # show amount due again for clarity
        plan = PAYMENT_PLANS[st.session_state.selected_plan]
        st.markdown(f"**Amount to pay: ₹{plan['price']}**")
        
        # Payment button
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            if st.button(
                f"💳 Proceed to Payment (₹{plan['price']})",
                use_container_width=True,
                type="primary"
            ):
                initiate_payment()
    else:
        st.info("""
        **How to download your image:**
        
        1️⃣ **Select a Plan** - Choose between Premium (₹10) or Pro (₹50) above
        2️⃣ **Review Order** - Check your image details and style
        3️⃣ **Complete Payment** - Use Razorpay secure checkout
        4️⃣ **Download** - Get your high-quality image immediately after payment
        
        **Why buy?**
        - ✅ Remove watermark
        - ✅ Full-quality PNG export
        - ✅ Support the platform
        - ✅ Fast and secure payment
        """)


if __name__ == "__main__":
    payment_page()
