"""
Download Manager Module for AI Cartoonization Platform
Handles image saving, watermarking, format conversion, and metadata storage
"""

import cv2
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import os
from typing import Optional, Dict, Tuple
import sqlite3
from PIL import Image, ImageDraw, ImageFont
import io
import secrets
import string


# Configuration
OUTPUTS_FOLDER = Path("outputs")
ALLOWED_FORMATS = {"png", "jpg", "jpeg", "pdf"}
MAX_FILE_AGE_HOURS = 24

# Create outputs folder if not exists
OUTPUTS_FOLDER.mkdir(exist_ok=True)


def get_db_connection():
    """
    Get database connection for metadata storage.
    
    Returns:
        sqlite3.Connection: Database connection
    """
    db_path = Path("database") / "app.db"
    return sqlite3.connect(str(db_path))


def create_image_history_table():
    """
    Create ImageHistory table if it doesn't exist.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ImageHistory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            original_path TEXT NOT NULL,
            processed_path TEXT NOT NULL,
            style_applied TEXT NOT NULL,
            processing_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            processing_time_seconds REAL,
            output_format TEXT,
            payment_status TEXT DEFAULT 'free',
            file_size_bytes INTEGER,
            intensity_level TEXT,
            FOREIGN KEY (user_id) REFERENCES Users(username)
        )
    """)
    
    conn.commit()
    conn.close()


def create_download_links_table():
    """
    Create DownloadLinks table for temporary download link tracking.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS DownloadLinks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE NOT NULL,
            user_id TEXT NOT NULL,
            file_path TEXT NOT NULL,
            filename TEXT NOT NULL,
            created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            expires_at DATETIME NOT NULL,
            is_used BOOLEAN DEFAULT 0,
            used_date DATETIME,
            FOREIGN KEY (user_id) REFERENCES Users(username)
        )
    """)
    
    conn.commit()
    conn.close()


def create_download_history_table():
    """
    Create DownloadHistory table for logging all downloads.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS DownloadHistory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            file_path TEXT NOT NULL,
            filename TEXT NOT NULL,
            file_size_bytes INTEGER,
            download_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            payment_status TEXT,
            order_id TEXT,
            ip_address TEXT,
            FOREIGN KEY (user_id) REFERENCES Users(username)
        )
    """)
    
    conn.commit()
    conn.close()


def add_watermark(
    image: np.ndarray,
    watermark_text: str = "FREE PREVIEW",
    opacity: float = 0.3
) -> np.ndarray:
    """
    Add watermark to image for free preview.
    
    Args:
        image: Input image (BGR format)
        watermark_text: Text to display as watermark
        opacity: Watermark opacity (0.0 to 1.0)
        
    Returns:
        np.ndarray: Image with watermark
    """
    # Create a copy to avoid modifying original
    watermarked = image.copy().astype(np.float32)
    
    # Create watermark layer
    watermark_layer = np.zeros_like(watermarked)
    
    # Font for watermark
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.2
    font_color = (255, 255, 255)  # White text
    font_thickness = 2
    
    # Get text size
    text_size = cv2.getTextSize(
        watermark_text,
        font,
        font_scale,
        font_thickness
    )[0]
    
    # Position watermark in center
    h, w = image.shape[:2]
    x = (w - text_size[0]) // 2
    y = (h + text_size[1]) // 2
    
    # Add text to watermark layer
    cv2.putText(
        watermark_layer,
        watermark_text,
        (x, y),
        font,
        font_scale,
        font_color,
        font_thickness
    )
    
    # Add semi-transparent rectangle background for better readability
    padding = 10
    cv2.rectangle(
        watermark_layer,
        (x - padding, y - text_size[1] - padding),
        (x + text_size[0] + padding, y + padding),
        (0, 0, 0),
        -1
    )
    
    # Blend watermark layer with original image
    watermarked = cv2.addWeighted(
        watermarked,
        1.0,
        watermark_layer,
        opacity,
        0
    )
    
    return np.uint8(np.clip(watermarked, 0, 255))


def generate_unique_filename(
    user_id: str,
    original_filename: str,
    format: str = "png"
) -> str:
    """
    Generate unique filename for processed image.
    
    Format: {user_id}_{timestamp}_{original_filename}
    
    Args:
        user_id: User identifier
        original_filename: Original file name
        format: Output format
        
    Returns:
        str: Unique filename
    """
    # Clean user_id (remove special characters)
    clean_user_id = "".join(c for c in user_id if c.isalnum() or c == "_")
    
    # Get original filename without extension
    original_base = Path(original_filename).stem
    
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S%f")[:-3]  # Include milliseconds
    
    # Combine into unique filename
    unique_filename = f"{clean_user_id}_{timestamp}_{original_base}.{format.lower()}"
    
    return unique_filename


def save_as_png(
    image: np.ndarray,
    file_path: Path
) -> bool:
    """
    Save image as PNG format (high quality, lossless).
    
    Args:
        image: Image to save (BGR format)
        file_path: Path where image will be saved
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        success = cv2.imwrite(str(file_path), image, [cv2.IMWRITE_PNG_COMPRESSION, 9])
        return bool(success)
    except Exception as e:
        print(f"Error saving PNG: {str(e)}")
        return False


def save_as_jpg(
    image: np.ndarray,
    file_path: Path,
    quality: int = 95
) -> bool:
    """
    Save image as JPEG format (compressed).
    
    Args:
        image: Image to save (BGR format)
        file_path: Path where image will be saved
        quality: JPEG quality (1-100, default: 95)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        success = cv2.imwrite(
            str(file_path),
            image,
            [cv2.IMWRITE_JPEG_QUALITY, quality]
        )
        return bool(success)
    except Exception as e:
        print(f"Error saving JPG: {str(e)}")
        return False


def save_as_pdf(
    image: np.ndarray,
    file_path: Path
) -> bool:
    """
    Save image as PDF format.
    
    Args:
        image: Image to save (BGR format)
        file_path: Path where image will be saved
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Convert BGR to RGB
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Convert to PIL
        pil_image = Image.fromarray(rgb_image)
        
        # Save as PDF
        pil_image.save(str(file_path), format='PDF')
        return True
    except Exception as e:
        print(f"Error saving PDF: {str(e)}")
        return False


def save_image_by_format(
    image: np.ndarray,
    file_path: Path,
    format: str
) -> bool:
    """
    Save image in specified format.
    
    Args:
        image: Image to save
        file_path: Path where image will be saved
        format: Output format (png, jpg, jpeg, pdf)
        
    Returns:
        bool: True if successful, False otherwise
    """
    format_lower = format.lower().strip()
    
    if format_lower == "png":
        return save_as_png(image, file_path)
    elif format_lower in {"jpg", "jpeg"}:
        return save_as_jpg(image, file_path)
    elif format_lower == "pdf":
        return save_as_pdf(image, file_path)
    else:
        raise ValueError(f"Unsupported format: {format}")


def store_image_metadata(
    user_id: str,
    original_filename: str,
    original_path: str,
    processed_path: str,
    style_applied: str,
    processing_time: float,
    output_format: str,
    payment_status: str = "free",
    intensity_level: str = "medium"
) -> bool:
    """
    Store image processing metadata in database.
    
    Args:
        user_id: User identifier
        original_filename: Original file name
        original_path: Path to original image
        processed_path: Path to processed image
        style_applied: Style that was applied
        processing_time: Time taken for processing (seconds)
        output_format: Output format (png, jpg, pdf)
        payment_status: Payment status (free or paid)
        intensity_level: Intensity level used (light, medium, strong)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        create_image_history_table()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get file size
        file_size = os.path.getsize(processed_path) if os.path.exists(processed_path) else 0
        
        # Insert metadata
        cursor.execute("""
            INSERT INTO ImageHistory (
                user_id,
                original_filename,
                original_path,
                processed_path,
                style_applied,
                processing_time_seconds,
                output_format,
                payment_status,
                file_size_bytes,
                intensity_level
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            original_filename,
            original_path,
            processed_path,
            style_applied,
            processing_time,
            output_format,
            payment_status,
            file_size,
            intensity_level
        ))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error storing metadata: {str(e)}")
        return False


def prepare_download(
    image: np.ndarray,
    user_id: str,
    original_filename: str,
    style: str,
    output_format: str = "png",
    watermark: bool = True,
    intensity: str = "medium",
    processing_time: float = 0.0,
    payment_status: str = "free"
) -> Dict:
    """
    Prepare image for download with metadata storage.
    
    Complete pipeline:
    1. Add watermark if free preview
    2. Save image in specified format
    3. Generate unique filename
    4. Store metadata in database
    5. Return download information
    
    Args:
        image: Processed image (BGR format)
        user_id: User identifier
        original_filename: Original file name
        style: Style that was applied
        output_format: Output format (png, jpg, pdf, default: png)
        watermark: Add watermark for free preview (default: True)
        intensity: Intensity level used
        processing_time: Processing time in seconds
        payment_status: Payment status (default: free)
        
    Returns:
        Dict: Download information with keys:
            - success: bool
            - file_path: str (path to saved file)
            - filename: str (filename only)
            - status: str (success message or error)
            - file_size: int (size in bytes)
            
    Raises:
        ValueError: If format is not supported
    """
    try:
        # Validate format
        if output_format.lower() not in ALLOWED_FORMATS:
            raise ValueError(f"Unsupported format: {output_format}")
        
        # Add watermark for free preview
        processed_image = image.copy()
        if watermark and payment_status == "free":
            processed_image = add_watermark(processed_image)
        
        # Generate unique filename
        filename = generate_unique_filename(user_id, original_filename, output_format)
        file_path = OUTPUTS_FOLDER / filename
        
        # Save image
        success = save_image_by_format(processed_image, file_path, output_format)
        
        if not success:
            return {
                "success": False,
                "status": "Failed to save image",
                "file_path": None,
                "filename": None,
                "file_size": 0
            }
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Store metadata
        original_path = ""  # Or pass from session if available
        metadata_stored = store_image_metadata(
            user_id=user_id,
            original_filename=original_filename,
            original_path=original_path,
            processed_path=str(file_path),
            style_applied=style,
            processing_time=processing_time,
            output_format=output_format,
            payment_status=payment_status,
            intensity_level=intensity
        )
        
        return {
            "success": True,
            "file_path": str(file_path),
            "filename": filename,
            "status": f"Image saved successfully ({output_format.upper()})",
            "file_size": file_size,
            "metadata_stored": metadata_stored,
            "watermark_applied": watermark and payment_status == "free"
        }
        
    except Exception as e:
        return {
            "success": False,
            "status": f"Error preparing download: {str(e)}",
            "file_path": None,
            "filename": None,
            "file_size": 0
        }


def cleanup_old_files(max_age_hours: int = MAX_FILE_AGE_HOURS) -> Dict:
    """
    Delete files older than specified hours from outputs folder.
    
    Useful for cleaning up temporary processed images.
    
    Args:
        max_age_hours: Maximum age of files in hours (default: 24)
        
    Returns:
        Dict: Cleanup statistics
            - deleted_count: number of files deleted
            - freed_space_mb: total space freed in MB
            - status: operation status
    """
    try:
        deleted_count = 0
        freed_space_bytes = 0
        
        # Current time
        now = datetime.now()
        cutoff_time = now - timedelta(hours=max_age_hours)
        
        # Iterate through files in outputs folder
        if OUTPUTS_FOLDER.exists():
            for file_path in OUTPUTS_FOLDER.iterdir():
                if file_path.is_file():
                    # Get file modification time
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    
                    # Check if file is older than cutoff
                    if file_mtime < cutoff_time:
                        try:
                            file_size = file_path.stat().st_size
                            os.remove(file_path)
                            deleted_count += 1
                            freed_space_bytes += file_size
                            print(f"Deleted: {file_path.name}")
                        except Exception as e:
                            print(f"Error deleting {file_path.name}: {str(e)}")
        
        freed_space_mb = freed_space_bytes / (1024 * 1024)
        
        return {
            "deleted_count": deleted_count,
            "freed_space_mb": round(freed_space_mb, 2),
            "status": f"Deleted {deleted_count} files, freed {freed_space_mb:.2f} MB"
        }
        
    except Exception as e:
        return {
            "deleted_count": 0,
            "freed_space_mb": 0,
            "status": f"Error during cleanup: {str(e)}"
        }


def generate_download_token(length: int = 32) -> str:
    """
    Generate a secure random token for download links.
    
    Args:
        length: Length of token
        
    Returns:
        str: Secure random token
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def create_download_link(
    user_id: str,
    file_path: str,
    filename: str,
    expiry_hours: int = 1
) -> Dict:
    """
    Create a temporary download link with expiry.
    
    Args:
        user_id: User identifier
        file_path: Path to file for download
        filename: Filename for download
        expiry_hours: Link expiry time in hours (default: 1)
        
    Returns:
        Dict: Download link details
            - success: bool
            - token: unique download token
            - link: Download URL (for reference)
            - expires_at: Expiry timestamp
            - status: Status message
    """
    try:
        create_download_links_table()
        
        # Generate token
        token = generate_download_token()
        
        # Calculate expiry time
        expires_at = datetime.now() + timedelta(hours=expiry_hours)
        
        # Store in database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO DownloadLinks (
                token,
                user_id,
                file_path,
                filename,
                expires_at
            ) VALUES (?, ?, ?, ?, ?)
        """, (token, user_id, file_path, filename, expires_at))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "token": token,
            "link": f"/download/{token}",
            "expires_at": expires_at.isoformat(),
            "status": f"Download link created, expires in {expiry_hours} hour(s)"
        }
        
    except Exception as e:
        return {
            "success": False,
            "token": None,
            "link": None,
            "expires_at": None,
            "status": f"Error creating download link: {str(e)}"
        }


def verify_and_get_download(token: str) -> Optional[Dict]:
    """
    Verify download token and get file information.
    
    Checks if token is valid, not expired, and not already used.
    
    Args:
        token: Download token
        
    Returns:
        Dict: File information if valid, None otherwise
            - file_path: Path to file
            - filename: Filename
            - user_id: User who can download
    """
    try:
        create_download_links_table()
        
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if token exists, is not expired, and not used
        cursor.execute("""
            SELECT * FROM DownloadLinks
            WHERE token = ?
            AND is_used = 0
            AND datetime(expires_at) > datetime('now')
        """, (token,))
        
        row = cursor.fetchone()
        
        if row:
            record = dict(row)
            conn.close()
            return {
                "file_path": record["file_path"],
                "filename": record["filename"],
                "user_id": record["user_id"]
            }
        
        conn.close()
        return None
        
    except Exception as e:
        print(f"Error verifying download token: {str(e)}")
        return None


def log_download(
    user_id: str,
    file_path: str,
    filename: str,
    payment_status: str = "free",
    order_id: Optional[str] = None,
    ip_address: Optional[str] = None
) -> bool:
    """
    Log a download in the DownloadHistory table.
    
    Args:
        user_id: User identifier
        file_path: Path to downloaded file
        filename: Downloaded filename
        payment_status: Payment status (free or paid)
        order_id: Associated order ID
        ip_address: IP address of downloader
        
    Returns:
        bool: True if logged successfully, False otherwise
    """
    try:
        create_download_history_table()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get file size
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        
        cursor.execute("""
            INSERT INTO DownloadHistory (
                user_id,
                file_path,
                filename,
                file_size_bytes,
                payment_status,
                order_id,
                ip_address
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, file_path, filename, file_size, payment_status, order_id, ip_address))
        
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Error logging download: {str(e)}")
        return False


def mark_download_link_used(token: str) -> bool:
    """
    Mark a download link as used.
    
    Args:
        token: Download token
        
    Returns:
        bool: True if updated successfully
    """
    try:
        create_download_links_table()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE DownloadLinks
            SET is_used = 1, used_date = ?
            WHERE token = ?
        """, (datetime.now(), token))
        
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Error marking download link as used: {str(e)}")
        return False


def get_download_history(user_id: str, limit: int = 10) -> list:
    """
    Get download history for a user.
    
    Args:
        user_id: User identifier
        limit: Maximum records to return
        
    Returns:
        list: List of download records
    """
    try:
        create_download_history_table()
        
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM DownloadHistory
            WHERE user_id = ?
            ORDER BY download_date DESC
            LIMIT ?
        """, (user_id, limit))
        
        records = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return records
        
    except Exception as e:
        print(f"Error retrieving download history: {str(e)}")
        return []


def get_user_download_history(user_id: str, limit: int = 10) -> list:
    """
    Get download history for a user.
    
    Args:
        user_id: User identifier
        limit: Maximum number of records to return
        
    Returns:
        list: List of ImageHistory records
    """
    try:
        create_image_history_table()
        
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM ImageHistory
            WHERE user_id = ?
            ORDER BY processing_date DESC
            LIMIT ?
        """, (user_id, limit))
        
        records = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return records
    except Exception as e:
        print(f"Error retrieving history: {str(e)}")
        return []


# Example usage and testing
if __name__ == "__main__":
    print("Download Manager Module")
    print("=" * 50)
    
    # Create test image
    test_image = np.random.randint(0, 256, (400, 400, 3), dtype=np.uint8)
    
    try:
        # Test prepare_download
        print("Testing prepare_download function...")
        result = prepare_download(
            image=test_image,
            user_id="test_user",
            original_filename="test_image.jpg",
            style="Classic Cartoon",
            output_format="png",
            watermark=True,
            intensity="medium",
            processing_time=2.5,
            payment_status="free"
        )
        
        print(f"✅ Download prepared:")
        for key, value in result.items():
            print(f"   {key}: {value}")
        
        # Test cleanup
        print("\nTesting cleanup function...")
        cleanup_result = cleanup_old_files(max_age_hours=24)
        print(f"✅ Cleanup complete:")
        for key, value in cleanup_result.items():
            print(f"   {key}: {value}")
        
        # Test history retrieval
        print("\nTesting history retrieval...")
        history = get_user_download_history("test_user")
        print(f"✅ Retrieved {len(history)} history records")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
