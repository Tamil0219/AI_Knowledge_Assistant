"""
Style Selection and Image Processing Page
Allows users to select cartoon styles and process uploaded images
"""

import streamlit as st
from PIL import Image as PILImage
import cv2
import numpy as np
from pathlib import Path
import io
from datetime import datetime
import time
import sqlite3

# Import image processing functions
from backend.image_processing import (
    apply_cartoon_effect,
    apply_classic_cartoon,
    apply_sketch_effect,
    apply_pencil_color,
    apply_bilateral_filter,
    color_quantization,
    reduce_color_saturation,
    apply_median_blur,
    apply_canny_edge,
    apply_adaptive_threshold,
    load_image,
    save_image
)

# Import download logging
from backend.download_manager import log_download


# Output folder for processed images
OUTPUTS_FOLDER = Path(__file__).parent.parent / "outputs" / "processed_images"
OUTPUTS_FOLDER.mkdir(parents=True, exist_ok=True)


def save_processed_image_to_db(
    username: str,
    original_image_path: str,
    processed_image_path: str,
    style_name: str,
    intensity: str,
    processing_time: float
) -> bool:
    """
    Save processed image record to the database.
    
    Args:
        username: Username of the user
        original_image_path: Path to original image
        processed_image_path: Path to processed image
        style_name: Style applied
        intensity: Intensity level used
        processing_time: Time taken to process in seconds
        
    Returns:
        bool: True if saved successfully
    """
    try:
        from backend.database import get_db_connection as get_conn
        conn = get_conn()
        cursor = conn.cursor()
        
        # Get user_id from username
        cursor.execute("SELECT user_id FROM Users WHERE username = ?", (username,))
        user_result = cursor.fetchone()
        if not user_result:
            return False
        
        user_id = user_result[0]
        
        # Get file sizes
        import os
        original_size = os.path.getsize(original_image_path) if os.path.exists(original_image_path) else 0
        processed_size = os.path.getsize(processed_image_path) if os.path.exists(processed_image_path) else 0
        
        # Insert into ImageHistory.  Columns `processing_time_seconds` and
        # `intensity_level` were added later; if they do not exist the ALTER
        # logic in the database initialization will add them on startup.  We
        # still wrap the operation in try/except so that if the schema is
        # somehow out-of-date the error is surfaced.
        try:
            cursor.execute("""
                INSERT INTO ImageHistory 
                (user_id, original_image_path, processed_image_path, style_applied, 
                 processing_date, payment_status, processing_time_seconds, intensity_level)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, 'free', ?, ?)
            """, (user_id, original_image_path, processed_image_path, style_name, 
                  processing_time, intensity))
        except sqlite3.OperationalError as op_err:
            # Attempt fallback to older schema without the new columns
            if 'no such column' in str(op_err).lower():
                cursor.execute("""
                    INSERT INTO ImageHistory 
                    (user_id, original_image_path, processed_image_path, style_applied, 
                     processing_date, payment_status)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, 'free')
                """, (user_id, original_image_path, processed_image_path, style_name))
            else:
                raise
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving processed image to database: {str(e)}")
        return False


# Style definitions
STYLES = {
    "Classic Cartoon": {
        "description": "Bold, colorful cartoon effect with outlined features",
        "icon": "🎨",
        "function": apply_classic_cartoon,
        "param_name": "intensity"
    },
    "Sketch": {
        "description": "Realistic pencil sketch with fine details",
        "icon": "✏️",
        "function": apply_sketch_effect,
        "param_name": "intensity"
    },
    "Pencil Color": {
        "description": "Colored pencil sketch with muted, artistic colors",
        "icon": "🖍️",
        "function": apply_pencil_color,
        "param_name": "intensity"
    }
}


# Additional wrappers so every style accepts (image_path, intensity)
def _posterize_cartoon_wrapper(image_path, intensity="medium"):
    mapping = {
        "light": (1, 12, 100, 200),
        "medium": (2, 8, 150, 250),
        "strong": (3, 5, 180, 260)
    }
    bp, num_colors, t1, t2 = mapping.get(intensity, mapping["medium"])
    cartoon, _ = apply_cartoon_effect(
        image_path,
        bilateral_passes=bp,
        num_colors=num_colors,
        edge_threshold1=t1,
        edge_threshold2=t2
    )
    return cartoon


def _bilateral_wrapper(image_path, intensity="medium"):
    mapping = {"light": 5, "medium": 9, "strong": 15}
    diameter = mapping.get(intensity, 9)
    return apply_bilateral_filter(image_path, diameter=diameter)


def _quantize_wrapper(image_path, intensity="medium"):
    mapping = {"light": 12, "medium": 8, "strong": 5}
    k = mapping.get(intensity, 8)
    return color_quantization(image_path, k=k)


def _desaturate_wrapper(image_path, intensity="medium"):
    mapping = {"light": 0.7, "medium": 0.4, "strong": 0.2}
    factor = mapping.get(intensity, 0.4)
    return reduce_color_saturation(image_path, saturation_factor=factor)


def _median_blur_wrapper(image_path, intensity="medium"):
    mapping = {"light": 3, "medium": 5, "strong": 9}
    k = mapping.get(intensity, 5)
    return apply_median_blur(image_path, kernel_size=k)


def _edge_outline_wrapper(image_path, intensity="medium"):
    mapping = {
        "light": (50, 150),
        "medium": (100, 200),
        "strong": (150, 250)
    }
    t1, t2 = mapping.get(intensity, (100, 200))
    return apply_canny_edge(image_path, threshold1=t1, threshold2=t2)


def _adaptive_threshold_wrapper(image_path, intensity="medium"):
    # intensity not used for adaptive threshold - keep signature compatible
    return apply_adaptive_threshold(image_path)


# Extend STYLES with additional options
STYLES.update({
    "Posterize Cartoon": {
        "description": "Strong posterized cartoon with bold color blocks",
        "icon": "🧩",
        "function": _posterize_cartoon_wrapper,
        "param_name": "intensity"
    },
    "Bilateral Smooth": {
        "description": "Smooth, edge-preserving filter for a painted look",
        "icon": "✨",
        "function": _bilateral_wrapper,
        "param_name": "intensity"
    },
    "Color Quantize": {
        "description": "Reduce palette for a posterized, cartoon-like look",
        "icon": "🔷",
        "function": _quantize_wrapper,
        "param_name": "intensity"
    },
    "Desaturated": {
        "description": "Muted colors for an artistic, soft look",
        "icon": "🪄",
        "function": _desaturate_wrapper,
        "param_name": "intensity"
    },
    "Median Blur": {
        "description": "Remove noise and create painterly smoothing",
        "icon": "🧽",
        "function": _median_blur_wrapper,
        "param_name": "intensity"
    },
    "Edge Outline": {
        "description": "Black-and-white edge-only outline of the image",
        "icon": "🖼️",
        "function": _edge_outline_wrapper,
        "param_name": "intensity"
    },
    "Adaptive Threshold": {
        "description": "Binary stylized image based on local thresholding",
        "icon": "⚪",
        "function": _adaptive_threshold_wrapper,
        "param_name": "intensity"
    }
})

INTENSITY_LEVELS = {
    "Light": "light",
    "Medium": "medium",
    "Strong": "strong"
}


def log_image_download(username: str, filename: str, file_size_bytes: int, style: str):
    """
    Log a download to the database.
    
    Args:
        username: Username of the user
        filename: Name of the downloaded file
        file_size_bytes: Size of the file in bytes
        style: Style that was applied
    """
    try:
        # Get user_id
        import sqlite3
        from backend.database import get_db_connection as get_conn
        
        conn = get_conn()
        cursor = conn.cursor()
        
        cursor.execute("SELECT user_id FROM Users WHERE username = ?", (username,))
        user_result = cursor.fetchone()
        
        if user_result:
            user_id = user_result[0]
            
            # Insert into DownloadHistory directly with file size
            cursor.execute("""
                INSERT INTO DownloadHistory (
                    user_id,
                    file_path,
                    filename,
                    file_size_bytes,
                    payment_status
                ) VALUES (?, ?, ?, ?, ?)
            """, (user_id, "", filename, file_size_bytes, "free"))
            
            conn.commit()
            conn.close()
            return True
    except Exception as e:
        st.warning(f"Could not log download: {str(e)}")
    
    return False


def cv2_to_pil(cv2_image: np.ndarray) -> PILImage.Image:
    """
    Convert OpenCV (BGR) image to PIL Image (RGB).
    
    Args:
        cv2_image: Image in BGR format (OpenCV)
        
    Returns:
        PILImage.Image: Image in RGB format (PIL)
    """
    # Convert BGR to RGB
    rgb_image = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB)
    pil_image = PILImage.fromarray(rgb_image)
    return pil_image


def pil_to_cv2(pil_image: PILImage.Image) -> np.ndarray:
    """
    Convert PIL Image (RGB) to OpenCV (BGR) image.
    
    Args:
        pil_image: Image in RGB format (PIL)
        
    Returns:
        np.ndarray: Image in BGR format (OpenCV)
    """
    rgb_array = np.array(pil_image)
    bgr_image = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)
    return bgr_image


def process_image_with_style(
    image_path: str,
    style: str,
    intensity: str = "medium"
) -> np.ndarray:
    """
    Process image with selected style.
    
    Args:
        image_path: Path to the image file
        style: Selected style name
        intensity: Intensity level (light, medium, strong)
        
    Returns:
        np.ndarray: Processed image
        
    Raises:
        ValueError: If style is not valid
    """
    if style not in STYLES:
        raise ValueError(f"Unknown style: {style}")
    
    style_config = STYLES[style]
    processing_function = style_config["function"]
    
    # Process image with selected style
    processed = processing_function(image_path, intensity=intensity)
    
    return processed


def display_image_comparison(
    original_image: np.ndarray,
    processed_image: np.ndarray,
    style_name: str
):
    """
    Display original and processed images side by side.
    
    Args:
        original_image: Original image (BGR format)
        processed_image: Processed image
        style_name: Name of applied style
    """
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Original Image")
        # Convert BGR to RGB for PIL
        original_rgb = cv2.cvtColor(original_image, cv2.COLOR_BGR2RGB)
        st.image(original_rgb, use_container_width=True, output_format="RGB")
    
    with col2:
        st.subheader(f"{STYLES[style_name]['icon']} {style_name}")
        # Handle both BGR and grayscale processed images
        if len(processed_image.shape) == 2:  # Grayscale
            # Convert grayscale to RGB for Streamlit (st.image doesn't accept cmap)
            processed_rgb = cv2.cvtColor(processed_image, cv2.COLOR_GRAY2RGB)
            st.image(processed_rgb, use_container_width=True, output_format="RGB")
        else:  # BGR format
            processed_rgb = cv2.cvtColor(processed_image, cv2.COLOR_BGR2RGB)
            st.image(processed_rgb, use_container_width=True, output_format="RGB")


def download_processed_image(
    processed_image: np.ndarray,
    style_name: str
) -> bytes:
    """
    Generate downloadable image file.
    
    Args:
        processed_image: Processed image (OpenCV format)
        style_name: Style that was applied
        
    Returns:
        bytes: Image data as bytes (PNG format)
    """
    # Convert to RGB if BGR, or keep if grayscale
    if len(processed_image.shape) == 3:
        display_image = cv2.cvtColor(processed_image, cv2.COLOR_BGR2RGB)
    else:
        display_image = processed_image
    
    # Convert to PIL and save to bytes
    pil_image = PILImage.fromarray(display_image)
    img_bytes = io.BytesIO()
    pil_image.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    return img_bytes.getvalue()


def get_image_size_info(image: np.ndarray) -> dict:
    """
    Get image dimensions and file size information.
    
    Args:
        image: Image array
        
    Returns:
        dict: Dictionary with size information
    """
    height, width = image.shape[:2]
    
    # Calculate approximate file size in memory (bytes)
    file_size_bytes = image.nbytes
    
    # Convert to human-readable format
    if file_size_bytes < 1024:
        size_str = f"{file_size_bytes} B"
    elif file_size_bytes < 1024 * 1024:
        size_str = f"{file_size_bytes / 1024:.1f} KB"
    else:
        size_str = f"{file_size_bytes / (1024 * 1024):.1f} MB"
    
    return {
        "width": width,
        "height": height,
        "dimensions": f"{width} × {height} px",
        "size": size_str,
        "pixels": width * height
    }


def create_side_by_side_comparison(
    original_image: np.ndarray,
    processed_image: np.ndarray,
    style_name: str
) -> np.ndarray:
    """
    Create a side-by-side comparison image.
    
    Args:
        original_image: Original image (BGR format)
        processed_image: Processed image
        style_name: Name of the style applied
        
    Returns:
        np.ndarray: Combined comparison image
    """
    # Ensure both images have the same height
    h_original = original_image.shape[0]
    h_processed = processed_image.shape[0]
    
    if h_original != h_processed:
        scale = h_original / h_processed if h_processed > 0 else 1
        new_width = int(processed_image.shape[1] * scale)
        processed_resized = cv2.resize(processed_image, (new_width, h_original))
    else:
        processed_resized = processed_image
    
    # Convert grayscale to BGR if needed
    if len(processed_resized.shape) == 2:
        processed_resized = cv2.cvtColor(processed_resized, cv2.COLOR_GRAY2BGR)
    
    # Create white separator line
    separator = np.ones((h_original, 2, 3), dtype=np.uint8) * 255
    
    # Concatenate images
    comparison = np.hstack([original_image, separator, processed_resized])
    
    # Add labels
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1
    font_color = (0, 0, 0)
    thickness = 2
    
    # Original label
    cv2.putText(
        comparison,
        "ORIGINAL",
        (20, 40),
        font,
        font_scale,
        font_color,
        thickness
    )
    
    # Processed label
    processed_x = original_image.shape[1] + separator.shape[1] + 20
    cv2.putText(
        comparison,
        style_name.upper(),
        (processed_x, 40),
        font,
        font_scale,
        font_color,
        thickness
    )
    
    return comparison


def create_before_after_comparison(
    original_image: np.ndarray,
    processed_image: np.ndarray
) -> np.ndarray:
    """
    Create a before/after toggle-style comparison image.
    
    Args:
        original_image: Original image (BGR format)
        processed_image: Processed image
        
    Returns:
        np.ndarray: Split before/after comparison image
    """
    # Resize to same dimensions
    h_original = original_image.shape[0]
    h_processed = processed_image.shape[0]
    
    if h_original != h_processed:
        scale = h_original / h_processed if h_processed > 0 else 1
        new_width = int(processed_image.shape[1] * scale)
        processed_resized = cv2.resize(processed_image, (new_width, h_original))
    else:
        processed_resized = processed_image
    
    # Get width
    w_original = original_image.shape[1]
    w_processed = processed_resized.shape[1]
    
    # Use the width for the comparison
    target_width = min(w_original, w_processed)
    
    # Resize both to same dimensions
    original_resized = cv2.resize(original_image, (target_width, h_original))
    processed_resized = cv2.resize(processed_resized, (target_width, h_original))
    
    # Convert grayscale to BGR if needed
    if len(processed_resized.shape) == 2:
        processed_resized = cv2.cvtColor(processed_resized, cv2.COLOR_GRAY2BGR)
    
    # Stack vertically
    comparison = np.vstack([original_resized, processed_resized])
    
    # Add labels
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1
    font_color = (255, 255, 255)
    thickness = 2
    
    # Before label (white text with semi-transparent background)
    cv2.putText(
        comparison,
        "BEFORE",
        (20, 40),
        font,
        font_scale,
        font_color,
        thickness
    )
    
    # After label
    cv2.putText(
        comparison,
        "AFTER",
        (20, h_original + 40),
        font,
        font_scale,
        font_color,
        thickness
    )
    
    return comparison


def style_selection_page():
    """
    Main style selection and image processing page.
    """
    # Page header
    st.markdown("""
        <style>
            .style-header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                border-radius: 15px;
                margin-bottom: 30px;
                text-align: center;
            }
            
            .style-title {
                font-size: 2em;
                font-weight: 700;
                margin: 0;
            }
            
            .style-subtitle {
                font-size: 1.1em;
                opacity: 0.9;
                margin: 10px 0 0 0;
            }
            
            .style-card {
                background: white;
                border: 2px solid #e0e0e0;
                border-radius: 10px;
                padding: 20px;
                margin: 10px 0;
                transition: all 0.3s ease;
                cursor: pointer;
            }
            
            .style-card:hover {
                border-color: #667eea;
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
            }
            
            .style-icon {
                font-size: 2.5em;
                margin-bottom: 10px;
            }
            
            .style-name {
                font-size: 1.2em;
                font-weight: 600;
                color: #1e293b;
                margin: 10px 0;
            }
            
            .style-description {
                color: #666;
                font-size: 0.9em;
                line-height: 1.4;
            }
            
            .intensity-container {
                background: #f5f5f5;
                padding: 15px;
                border-radius: 8px;
                margin: 20px 0;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("""
        <div class="style-header">
            <h1 class="style-title">🎬 Choose Your Style</h1>
            <p class="style-subtitle">Transform your image with artistic effects</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Check if image is uploaded
    if 'uploaded_image_path' not in st.session_state or not st.session_state.uploaded_image_path:
        st.info("📤 Please upload an image first on the 'Cartoonize Image' tab.")
        if st.button("← Back to Dashboard"):
            st.session_state.page = "Dashboard"
            st.rerun()
        return
    
    # Initialize session state
    if 'selected_style' not in st.session_state:
        st.session_state.selected_style = "Classic Cartoon"
    
    if 'processed_image' not in st.session_state:
        st.session_state.processed_image = None
    
    if 'selected_intensity' not in st.session_state:
        st.session_state.selected_intensity = "Medium"
    
    if 'processing_time' not in st.session_state:
        st.session_state.processing_time = None
    
    if 'view_mode' not in st.session_state:
        st.session_state.view_mode = "side_by_side"
    
    # Style selection
    st.subheader("Available Styles")
    
    # Single radio control for selecting style (prevents multiple selections)
    style_names = list(STYLES.keys())
    try:
        default_index = style_names.index(st.session_state.selected_style)
    except Exception:
        default_index = 0

    selected_radio = st.radio(
        "Select a style",
        style_names,
        index=default_index,
        horizontal=True,
        key="selected_style_radio"
    )

    # Update session state
    st.session_state.selected_style = selected_radio

    # Display style cards in a responsive 3-column grid
    for i in range(0, len(style_names), 3):
        row = style_names[i:i+3]
        cols = st.columns(3)
        for style_name, col in zip(row, cols):
            with col:
                style_info = STYLES[style_name]
                is_selected = (style_name == st.session_state.selected_style)
                card_border = "2px solid #667eea" if is_selected else "2px solid #e0e0e0"
                shadow = "box-shadow: 0 6px 18px rgba(102,126,234,0.25);" if is_selected else ""
                st.markdown(f"""
                    <div class="style-card" style="border: {card_border}; {shadow}">
                        <div class="style-icon">{style_info['icon']}</div>
                        <div class="style-name">{style_name}</div>
                        <div class="style-description">{style_info['description']}</div>
                    </div>
                """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Intensity selection
    st.subheader("Effect Intensity")
    st.markdown("""
        <div class="intensity-container">
            <p style="margin: 0 0 10px 0;"><strong>Choose how strong the effect should be:</strong></p>
            <ul style="margin: 0; color: #666; font-size: 0.9em;">
                <li><strong>Light:</strong> Subtle effect, preserves more original details</li>
                <li><strong>Medium:</strong> Balanced effect with good detail and style blend</li>
                <li><strong>Strong:</strong> Heavy effect, maximum transformation</li>
            </ul>
        </div>
    """, unsafe_allow_html=True)
    
    intensity_col1, intensity_col2, intensity_col3 = st.columns(3)
    
    with intensity_col1:
        if st.button("☀️ Light", use_container_width=True):
            st.session_state.selected_intensity = "Light"
    
    with intensity_col2:
        if st.button("⭐ Medium", use_container_width=True, type="secondary"):
            st.session_state.selected_intensity = "Medium"
    
    with intensity_col3:
        if st.button("⚡ Strong", use_container_width=True):
            st.session_state.selected_intensity = "Strong"
    
    # Display selected intensity
    st.caption(f"Selected: **{st.session_state.selected_intensity}**")
    
    st.markdown("---")
    
    # Process button
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col2:
        process_button = st.button(
            "🎨 Process Image",
            use_container_width=True,
            type="primary"
        )
    
    # Process image
    if process_button:
        image_path = st.session_state.uploaded_image_path
        style = st.session_state.selected_style
        intensity = INTENSITY_LEVELS[st.session_state.selected_intensity]
        
        try:
            with st.spinner(f"✨ Processing with {style}... This may take a moment."):
                # Track processing time
                start_time = time.time()
                
                # Process image
                processed = process_image_with_style(image_path, style, intensity)
                
                # Calculate processing time
                end_time = time.time()
                processing_time = end_time - start_time
                
                # Save processed image to file
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"cartoon_{style.lower().replace(' ', '_')}_{timestamp}.png"
                processed_image_path = OUTPUTS_FOLDER / filename
                
                # Handle grayscale images
                if len(processed.shape) == 2:
                    # Convert grayscale to BGR for saving
                    processed_bgr = cv2.cvtColor(processed, cv2.COLOR_GRAY2BGR)
                    save_image(processed_bgr, processed_image_path)
                else:
                    save_image(processed, processed_image_path)
                
                # Store in session state
                st.session_state.processed_image = processed
                st.session_state.processed_style = style
                st.session_state.processed_intensity = intensity
                st.session_state.processing_time = processing_time
                st.session_state.processed_image_path = str(processed_image_path)
                
                # Save to database
                if 'username' in st.session_state:
                    saved = save_processed_image_to_db(
                        st.session_state.username,
                        image_path,
                        str(processed_image_path),
                        style,
                        intensity,
                        processing_time
                    )
                    if not saved:
                        st.warning("⚠️ The image was processed but we were unable to log the result in your history."
                                   " Please try again later or contact support.")
                
                st.success("✅ Processing complete!")
        
        except Exception as e:
            st.error(f"❌ Error processing image: {str(e)}")
    
    # Display results
    if st.session_state.processed_image is not None:
        st.markdown("---")
        st.subheader("Results")
        
        # Load original image
        original_image = load_image(st.session_state.uploaded_image_path)
        processed_image = st.session_state.processed_image
        
        # Get image information
        original_info = get_image_size_info(original_image)
        processed_info = get_image_size_info(processed_image)
        
        # Display stats in columns
        stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
        
        with stat_col1:
            st.metric("Original Size", original_info["dimensions"])
        
        with stat_col2:
            st.metric("Processed Size", processed_info["dimensions"])
        
        with stat_col3:
            st.metric("File Size", original_info["size"])
        
        with stat_col4:
            if st.session_state.processing_time:
                st.metric("Processing Time", f"{st.session_state.processing_time:.2f}s")
        
        st.markdown("---")
        
        # View mode toggle
        st.subheader("View Options")
        view_col1, view_col2 = st.columns(2)
        
        with view_col1:
            if st.button("📊 Side-by-Side", use_container_width=True, 
                        type="primary" if st.session_state.view_mode == "side_by_side" else "secondary"):
                st.session_state.view_mode = "side_by_side"
                st.rerun()
        
        with view_col2:
            if st.button("🔄 Before/After", use_container_width=True,
                        type="primary" if st.session_state.view_mode == "before_after" else "secondary"):
                st.session_state.view_mode = "before_after"
                st.rerun()
        
        st.markdown("---")
        
        # Display comparison based on selected view mode
        if st.session_state.view_mode == "side_by_side":
            display_image_comparison(original_image, processed_image, st.session_state.processed_style)
        else:
            # Before/After view
            comparison_img = create_before_after_comparison(original_image, processed_image)
            comparison_rgb = cv2.cvtColor(comparison_img, cv2.COLOR_BGR2RGB)
            st.image(comparison_rgb, use_container_width=True, output_format="RGB")
        
        st.markdown("---")
        
        # Download options
        st.subheader("📥 Download Your Processed Image")
        
        st.info("ℹ️ Your processed images are displayed above. Click the buttons below to download them. Downloads will be tracked in your Downloads section.")
        
        down_col1, down_col2, down_col3 = st.columns(3)
        
        with down_col1:
            # Download processed image
            image_data = download_processed_image(processed_image, st.session_state.processed_style)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"cartoon_{st.session_state.processed_style.lower().replace(' ', '_')}_{timestamp}.png"
            
            # Calculate file size
            file_size = len(image_data)
            
            st.download_button(
                label="📥 Processed Image",
                data=image_data,
                file_name=filename,
                mime="image/png",
                use_container_width=True,
                key="download_processed"
            )
            
            # Add a button to track the download
            if st.button("✅ Log Download", key="log_download_1", use_container_width=True, help="Click to log this download"):
                if 'username' in st.session_state:
                    if log_image_download(st.session_state.username, filename, file_size, st.session_state.processed_style):
                        st.success(f"✅ Download logged: {filename}")
                    else:
                        st.warning("Could not log download")
        
        with down_col2:
            # Download comparison image
            if st.session_state.view_mode == "side_by_side":
                comparison_img = create_side_by_side_comparison(
                    original_image,
                    processed_image,
                    st.session_state.processed_style
                )
            else:
                comparison_img = create_before_after_comparison(original_image, processed_image)
            
            comparison_data = download_processed_image(comparison_img, "comparison")
            comparison_filename = f"comparison_{st.session_state.processed_style.lower().replace(' ', '_')}_{timestamp}.png"
            comparison_file_size = len(comparison_data)
            
            st.download_button(
                label="📊 Comparison Image",
                data=comparison_data,
                file_name=comparison_filename,
                mime="image/png",
                use_container_width=True,
                key="download_comparison"
            )
            
            # Add a button to track the download
            if st.button("✅ Log Download", key="log_download_2", use_container_width=True, help="Click to log this download"):
                if 'username' in st.session_state:
                    if log_image_download(st.session_state.username, comparison_filename, comparison_file_size, "Comparison"):
                        st.success(f"✅ Download logged: {comparison_filename}")
                    else:
                        st.warning("Could not log download")
        
        with down_col3:
            if st.button("📤 New Image", use_container_width=True):
                st.session_state.uploaded_image_path = None
                st.session_state.processed_image = None
                st.rerun()
        
        st.markdown("---")
        
        # Action buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Try Another Style", use_container_width=True):
                st.session_state.processed_image = None
                st.rerun()
        
        with col2:
            if st.button("💳 Proceed to Payment", use_container_width=True, type="primary"):
                st.session_state.page = "Payment"
                st.rerun()
        
        with col3:
            if st.button("🏠 Dashboard", use_container_width=True):
                st.session_state.page = "Dashboard"
                st.rerun()
        
        # Display processing info
        st.markdown("---")
        with st.expander("ℹ️ Processing Details"):
            st.json({
                "style": st.session_state.processed_style,
                "intensity": st.session_state.processed_intensity,
                "processing_time_seconds": round(st.session_state.processing_time, 2) if st.session_state.processing_time else None,
                "original_dimensions": f"{original_info['width']}x{original_info['height']}",
                "processed_dimensions": f"{processed_info['width']}x{processed_info['height']}",
                "timestamp": datetime.now().isoformat()
            })


if __name__ == "__main__":
    style_selection_page()
