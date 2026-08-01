import streamlit as st
from PIL import Image
import os
from pathlib import Path
import uuid
from datetime import datetime
import shutil


# Configuration
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
UPLOAD_FOLDER = Path('uploads')

# Create uploads folder if it doesn't exist
UPLOAD_FOLDER.mkdir(exist_ok=True)


def validate_file_type(file) -> bool:
    """
    Validate if the uploaded file has an allowed extension.
    
    Args:
        file: Streamlit UploadedFile object
        
    Returns:
        bool: True if file type is valid, False otherwise
    """
    file_extension = Path(file.name).suffix.lower()
    return file_extension in ALLOWED_EXTENSIONS


def validate_file_size(file) -> bool:
    """
    Validate if the file size is within the allowed limit.
    
    Args:
        file: Streamlit UploadedFile object
        
    Returns:
        bool: True if file size is valid, False otherwise
    """
    file_size = file.size if hasattr(file, 'size') else len(file.getvalue())
    return file_size <= MAX_FILE_SIZE


def get_unique_filename(original_filename: str) -> str:
    """
    Generate a unique filename using UUID and timestamp.
    
    Args:
        original_filename: Original name of the file
        
    Returns:
        str: Unique filename
    """
    file_extension = Path(original_filename).suffix.lower()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_id = str(uuid.uuid4())[:8]
    unique_filename = f"{timestamp}_{unique_id}{file_extension}"
    return unique_filename


def save_uploaded_file(uploaded_file) -> str:
    """
    Save the uploaded file to the uploads folder.
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        
    Returns:
        str: Path to the saved file
    """
    try:
        unique_filename = get_unique_filename(uploaded_file.name)
        file_path = UPLOAD_FOLDER / unique_filename
        
        # Save the file
        with open(file_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())
        
        return str(file_path)
    except Exception as e:
        raise Exception(f"Error saving file: {str(e)}")


def load_image(file_path: str) -> Image.Image:
    """
    Load and validate image file. Handles corrupted files.
    
    Args:
        file_path: Path to the image file
        
    Returns:
        Image.Image: PIL Image object
        
    Raises:
        Exception: If file is corrupted or cannot be opened
    """
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Image file not found: {file_path}")
        
        image = Image.open(file_path)
        # Verify the image is valid by loading it
        image.verify()
        # Note: After verify(), we need to reopen to use the image
        image = Image.open(file_path)
        return image
    except FileNotFoundError as e:
        raise Exception(f"File not found: {str(e)}")
    except Image.UnidentifiedImageError:
        raise Exception("Corrupted image file: Unable to identify the image format")
    except Exception as e:
        raise Exception(f"Error loading image: {str(e)}")


def get_image_metadata(file_path: str) -> dict:
    """
    Extract metadata from an image file.
    
    Args:
        file_path: Path to the image file
        
    Returns:
        dict: Dictionary containing image metadata
    """
    try:
        image = Image.open(file_path)
        file_size = os.path.getsize(file_path)
        
        metadata = {
            'dimensions': f"{image.width} × {image.height} px",
            'file_size': format_file_size(file_size),
            'format': image.format or 'Unknown'
        }
        return metadata
    except Exception as e:
        raise Exception(f"Error extracting metadata: {str(e)}")


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        str: Formatted file size
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} TB"


def delete_old_image(file_path: str) -> None:
    """
    Delete an old image file from the uploads folder.
    
    Args:
        file_path: Path to the file to delete
    """
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        st.warning(f"Could not delete previous image: {str(e)}")


def image_upload_page(key_prefix: str = ""):
    """
    Main image upload page component using Streamlit.
    Handles file upload, validation, saving, and metadata display.

    Args:
        key_prefix: optional prefix to namespace widget keys when the upload
            component is embedded multiple times on a page. Keeps Streamlit
            from raising duplicate-key errors.
    """
    st.header("📸 Image Upload")
    
    # Initialize session state for image path
    if 'uploaded_image_path' not in st.session_state:
        st.session_state.uploaded_image_path = None
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Upload Image")
        st.info(
            f"**Allowed formats:** JPG, JPEG, PNG, BMP\n\n"
            f"**Maximum size:** {format_file_size(MAX_FILE_SIZE)}"
        )
        
        uploaded_file = st.file_uploader(
            "Choose an image",
            type=['jpg', 'jpeg', 'png', 'bmp'],
            key=f'{key_prefix}image_uploader'
        )
        
        if uploaded_file is not None:
            # Validate file type
            if not validate_file_type(uploaded_file):
                st.error("❌ Invalid file type. Please upload a JPG, JPEG, PNG, or BMP file.")
            # Validate file size
            elif not validate_file_size(uploaded_file):
                st.error(f"❌ File size exceeds the maximum limit of {format_file_size(MAX_FILE_SIZE)}.")
            else:
                try:
                    # Delete old image if exists
                    if st.session_state.uploaded_image_path:
                        delete_old_image(st.session_state.uploaded_image_path)
                    
                    # Save the file
                    file_path = save_uploaded_file(uploaded_file)
                    st.session_state.uploaded_image_path = file_path
                    
                    st.success(f"✅ Image uploaded successfully!")
                    
                except Exception as e:
                    st.error(f"❌ Error uploading file: {str(e)}")
        
        # Option to clear uploaded image
        if st.session_state.uploaded_image_path:
            if st.button("🗑️ Clear Uploaded Image", key=f'{key_prefix}clear_image'):
                delete_old_image(st.session_state.uploaded_image_path)
                st.session_state.uploaded_image_path = None
                st.rerun()
    
    with col2:
        st.subheader("Preview")
        
        # Display uploaded image if exists
        if st.session_state.uploaded_image_path:
            try:
                image = load_image(st.session_state.uploaded_image_path)
                st.image(image, use_container_width=True)
                
                # Display metadata
                st.subheader("Image Information")
                try:
                    metadata = get_image_metadata(st.session_state.uploaded_image_path)
                    
                    # Display metadata in columns
                    col_dims, col_format, col_size = st.columns(3)
                    
                    with col_dims:
                        st.metric("Dimensions", metadata['dimensions'])
                    
                    with col_format:
                        st.metric("Format", metadata['format'])
                    
                    with col_size:
                        st.metric("File Size", metadata['file_size'])
                    
                    # Display file path
                    st.caption(f"📁 Saved to: `{st.session_state.uploaded_image_path}`")
                    
                    # Navigation button
                    if st.button("➜ Proceed to Style Selection →", use_container_width=True, type="primary"):
                        st.session_state.page = "StyleSelection"
                        st.rerun()
                    
                except Exception as e:
                    st.error(f"Could not extract image metadata: {str(e)}")
                    
            except Exception as e:
                st.error(f"❌ Error loading image: {str(e)}")
                st.info("The image file may be corrupted. Please upload a new image.")
                # Clear the corrupted image path
                st.session_state.uploaded_image_path = None
        else:
            st.info("📤 Upload an image to see preview and metadata here.")


if __name__ == "__main__":
    image_upload_page()
