"""
Image processing module using OpenCV for AI Cartoonization Platform.
Provides functions for edge detection, adaptive thresholding, and filtering.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Union, Tuple


def load_image(image_source: Union[str, np.ndarray]) -> np.ndarray:
    """
    Load image from file path or accept numpy array.
    
    Args:
        image_source: File path (str) or numpy array of the image
        
    Returns:
        np.ndarray: Image array in BGR format
        
    Raises:
        FileNotFoundError: If file path doesn't exist
        ValueError: If image_source is invalid
    """
    if isinstance(image_source, np.ndarray):
        return image_source
    
    if isinstance(image_source, str):
        if not Path(image_source).exists():
            raise FileNotFoundError(f"Image file not found: {image_source}")
        
        image = cv2.imread(image_source)
        if image is None:
            raise ValueError(f"Failed to read image: {image_source}")
        
        return image
    
    raise ValueError(f"image_source must be file path (str) or numpy array, got {type(image_source)}")


def convert_to_grayscale(image: np.ndarray) -> np.ndarray:
    """
    Convert image to grayscale.
    
    Args:
        image: Input image (BGR format)
        
    Returns:
        np.ndarray: Grayscale image
    """
    if len(image.shape) == 2:  # Already grayscale
        return image
    
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def apply_canny_edge(
    image_source: Union[str, np.ndarray],
    threshold1: int = 100,
    threshold2: int = 200
) -> np.ndarray:
    """
    Apply Canny edge detection to image.
    
    Canny edge detection is a multi-stage algorithm that:
    1. Applies Gaussian blur to reduce noise
    2. Calculates gradient magnitude and direction
    3. Applies non-maximum suppression
    4. Applies double threshold and edge tracking
    
    Args:
        image_source: File path (str) or image array (np.ndarray)
        threshold1: Lower threshold for edge detection (default: 100)
        threshold2: Upper threshold for edge detection (default: 200)
                   Edges with intensity > threshold2 are kept
                   Edges with intensity < threshold1 are discarded
                   Edges between are kept only if connected to strong edges
        
    Returns:
        np.ndarray: Binary image with edges (white on black background)
    """
    # Load image
    image = load_image(image_source)
    
    # Convert to grayscale for edge detection
    gray = convert_to_grayscale(image)
    
    # Apply Gaussian blur to reduce noise (improves edge detection)
    blurred = cv2.GaussianBlur(gray, (5, 5), 1.5)
    
    # Apply Canny edge detection
    edges = cv2.Canny(blurred, threshold1, threshold2)
    
    return edges


def apply_adaptive_threshold(image_source: Union[str, np.ndarray]) -> np.ndarray:
    """
    Apply adaptive thresholding to image.
    
    Adaptive thresholding computes threshold for each pixel based on a small region
    around it. This is more robust to varying lighting conditions compared to global threshold.
    
    Args:
        image_source: File path (str) or image array (np.ndarray)
        
    Returns:
        np.ndarray: Binary image (black and white)
    """
    # Load image
    image = load_image(image_source)
    
    # Convert to grayscale
    gray = convert_to_grayscale(image)
    
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 1.5)
    
    # Apply adaptive thresholding
    # ADAPTIVE_THRESH_GAUSSIAN_C: Threshold is the weighted sum of neighborhood values
    # blockSize: Size of pixel neighborhood (must be odd number)
    # C: Constant subtracted from weighted mean
    adaptive_thresh = cv2.adaptiveThreshold(
        blurred,
        maxValue=255,
        adaptiveMethod=cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        thresholdType=cv2.THRESH_BINARY,
        blockSize=11,  # Neighborhood size
        C=2  # Constant subtracted from mean
    )
    
    return adaptive_thresh


def apply_median_blur(
    image_source: Union[str, np.ndarray],
    kernel_size: int = 5
) -> np.ndarray:
    """
    Apply median blur filter to image.
    
    Median blur is effective for removing salt-and-pepper noise while preserving edges.
    The kernel size must be an odd number.
    
    Args:
        image_source: File path (str) or image array (np.ndarray)
        kernel_size: Size of the median filter kernel (must be odd, default: 5)
                    Larger values remove more noise but also blur more
        
    Returns:
        np.ndarray: Filtered image
        
    Raises:
        ValueError: If kernel_size is even number
    """
    # Validate kernel size
    if kernel_size % 2 == 0:
        raise ValueError(f"kernel_size must be odd number, got {kernel_size}")
    
    if kernel_size < 3:
        raise ValueError(f"kernel_size must be at least 3, got {kernel_size}")
    
    # Load image
    image = load_image(image_source)
    
    # Apply median blur
    filtered = cv2.medianBlur(image, kernel_size)
    
    return filtered


def compare_images(
    original_image: Union[str, np.ndarray],
    processed_image: np.ndarray,
    title: str = "Comparison"
) -> np.ndarray:
    """
    Create a side-by-side comparison of original and processed images.
    
    Args:
        original_image: File path (str) or original image array
        processed_image: Processed image array
        title: Title for the comparison (for display purposes)
        
    Returns:
        np.ndarray: Combined image with original on left, processed on right
    """
    # Load original image
    original = load_image(original_image)
    
    # Ensure both images have the same height
    h_original = original.shape[0]
    h_processed = processed_image.shape[0]
    
    if h_original != h_processed:
        # Resize processed image to match original height
        scale = h_original / h_processed
        new_width = int(processed_image.shape[1] * scale)
        processed_image = cv2.resize(processed_image, (new_width, h_original))
    
    # If processed image is grayscale, convert to BGR for concatenation
    if len(processed_image.shape) == 2:
        processed_image = cv2.cvtColor(processed_image, cv2.COLOR_GRAY2BGR)
    
    # Ensure original is in BGR format
    if len(original.shape) == 2:
        original = cv2.cvtColor(original, cv2.COLOR_GRAY2BGR)
    
    # Concatenate images horizontally
    comparison = np.hstack([original, processed_image])
    
    return comparison


def save_image(image: np.ndarray, output_path: Union[str, Path]) -> bool:
    """
    Save image to file.
    
    Args:
        image: Image array to save
        output_path: Path where image will be saved
        
    Returns:
        bool: True if saved successfully, False otherwise
    """
    try:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        success = cv2.imwrite(str(output_path), image)
        return success
    except Exception as e:
        print(f"Error saving image: {str(e)}")
        return False


def get_image_info(image_source: Union[str, np.ndarray]) -> dict:
    """
    Get information about an image.
    
    Args:
        image_source: File path (str) or image array
        
    Returns:
        dict: Dictionary containing image metadata
    """
    image = load_image(image_source)
    
    info = {
        'shape': image.shape,
        'height': image.shape[0],
        'width': image.shape[1],
        'channels': image.shape[2] if len(image.shape) == 3 else 1,
        'dtype': str(image.dtype),
        'size_mb': (image.nbytes / (1024 * 1024))
    }
    
    return info


def apply_bilateral_filter(
    image_source: Union[str, np.ndarray],
    diameter: int = 9,
    sigma_color: float = 75.0,
    sigma_space: float = 75.0
) -> np.ndarray:
    """
    Apply bilateral filter to image for edge-preserving smoothing.
    
    Bilateral filtering is highly effective at edge-preserving smoothing. It smooths
    similar pixels while preserving edges by considering both spatial distance and
    intensity difference.
    
    Args:
        image_source: File path (str) or image array (np.ndarray)
        diameter: Diameter of pixel neighborhood (default: 9)
                 Larger values = more processing time but more smoothing
                 Should be odd and typically between 3-25
        sigma_color: Filter sigma in the color space (default: 75.0)
                    Range: 0-255. Larger values = more color blending
        sigma_space: Filter sigma in the coordinate space (default: 75.0)
                    Larger values = pixels far apart influence each other
        
    Returns:
        np.ndarray: Filtered image with preserved edges
    """
    # Load image
    image = load_image(image_source)
    
    # Ensure diameter is odd
    if diameter % 2 == 0:
        diameter += 1
    
    # Apply bilateral filter (very effective for cartoon-like effect)
    filtered = cv2.bilateralFilter(
        image,
        d=diameter,
        sigmaColor=sigma_color,
        sigmaSpace=sigma_space
    )
    
    return filtered


def color_quantization(
    image_source: Union[str, np.ndarray],
    k: int = 8
) -> np.ndarray:
    """
    Apply K-means clustering for color quantization.
    
    Reduces the number of colors in an image using K-means clustering.
    This creates a poster/cartoon-like effect by grouping similar colors.
    
    Optimized to process images in under 5 seconds.
    
    Args:
        image_source: File path (str) or image array (np.ndarray)
        k: Number of colors to quantize to (default: 8)
           Valid range: 2-16. Typical values: 8, 10, 12, 16
           Lower values = more posterization, faster processing
           Higher values = more color detail, slower processing
        
    Returns:
        np.ndarray: Quantized image with reduced color palette
        
    Raises:
        ValueError: If k is not in valid range (2-16)
    """
    # Validate k parameter
    if not isinstance(k, int) or k < 2 or k > 16:
        raise ValueError(f"k must be integer between 2 and 16, got {k}")
    
    # Load image
    image = load_image(image_source)
    
    # Get image dimensions
    height, width = image.shape[:2]
    
    # Reshape image to 2D array of pixels (height*width, 3)
    # This is required for K-means clustering
    pixels = image.reshape(-1, 3).astype(np.float32)
    
    # Define stopping criteria for K-means
    # (type, max_iterations, epsilon)
    # Stops when accuracy reaches epsilon or max_iterations is reached
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
    
    # Apply K-means clustering
    # Flags: cv2.KMEANS_RANDOM_CENTERS for random initialization
    # Returns: compactness, labels, centers
    _, labels, centers = cv2.kmeans(
        pixels,
        k,
        None,
        criteria,
        10,
        cv2.KMEANS_RANDOM_CENTERS
    )
    
    # Convert centers to 8-bit unsigned integer (uint8)
    centers = np.uint8(centers)
    
    # Map each pixel to its nearest cluster center
    quantized_pixels = centers[labels.flatten()]
    
    # Reshape back to image format
    quantized_image = quantized_pixels.reshape(height, width, 3)
    
    return quantized_image


def apply_cartoon_effect(
    image_source: Union[str, np.ndarray],
    bilateral_passes: int = 2,
    num_colors: int = 8,
    edge_threshold1: int = 150,
    edge_threshold2: int = 250
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Apply complete cartoon effect using bilateral filtering and color quantization.
    
    Combines multiple techniques to create a cartoon-like effect:
    1. Bilateral filtering (preserves edges, smooths colors)
    2. Color quantization (reduces color palette)
    3. Edge detection (for cartoon outline)
    
    Args:
        image_source: File path (str) or image array (np.ndarray)
        bilateral_passes: Number of times to apply bilateral filter (default: 2)
                         More passes = more cartoon-like, slower processing
        num_colors: Number of colors after quantization (default: 8)
        edge_threshold1: Lower threshold for Canny edge detection (default: 150)
        edge_threshold2: Upper threshold for Canny edge detection (default: 250)
        
    Returns:
        Tuple[np.ndarray, np.ndarray]: (cartoon_image, edge_image)
    """
    # Load image
    image = load_image(image_source)
    
    # Step 1: Apply bilateral filtering multiple times
    filtered = image.copy()
    for _ in range(bilateral_passes):
        filtered = cv2.bilateralFilter(filtered, d=9, sigmaColor=75, sigmaSpace=75)
    
    # Step 2: Apply color quantization
    cartoon = color_quantization(filtered, k=num_colors)
    
    # Step 3: Detect edges
    edges = apply_canny_edge(filtered, threshold1=edge_threshold1, threshold2=edge_threshold2)
    
    # Convert edge image to 3-channel for potential overlay
    edges_bgr = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    
    return cartoon, edges


def apply_classic_cartoon(
    image_source: Union[str, np.ndarray],
    intensity: str = "medium"
) -> np.ndarray:
    """
    Apply classic cartoon effect with different intensity levels.
    
    Complete cartoon transformation pipeline:
    1. Resize large images for optimal processing
    2. Apply bilateral filtering (color smoothing)
    3. Apply color quantization (reduce colors)
    4. Apply edge detection (cartoon outlines)
    5. Combine edges with quantized image
    
    Args:
        image_source: File path (str) or image array (np.ndarray)
        intensity: Cartoon effect intensity level (default: "medium")
                  - "light": Subtle cartoon effect, fewer color reductions
                  - "medium": Balanced cartoon effect
                  - "strong": Heavy cartoon effect, more posterization
        
    Returns:
        np.ndarray: Final cartoonized image with cartoon outlines
        
    Raises:
        ValueError: If intensity is not a valid option
    """
    # Validate intensity parameter
    intensity_lower = intensity.lower()
    valid_intensities = {"light", "medium", "strong"}
    
    if intensity_lower not in valid_intensities:
        raise ValueError(
            f"intensity must be one of {valid_intensities}, got '{intensity}'"
        )
    
    # Load image
    image = load_image(image_source)
    
    # Get original dimensions for reference
    original_height, original_width = image.shape[:2]
    
    # Step 1: Resize large images for performance
    # Limit max dimension to 1000 pixels for fast processing
    max_dimension = 1000
    if max(original_height, original_width) > max_dimension:
        scale = max_dimension / max(original_height, original_width)
        new_width = int(original_width * scale)
        new_height = int(original_height * scale)
        image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
    
    # Define parameters based on intensity level
    intensity_params = {
        "light": {
            "bilateral_passes": 1,
            "num_colors": 12,
            "edge_threshold1": 100,
            "edge_threshold2": 200,
            "edge_strength": 0.4
        },
        "medium": {
            "bilateral_passes": 2,
            "num_colors": 8,
            "edge_threshold1": 120,
            "edge_threshold2": 240,
            "edge_strength": 0.6
        },
        "strong": {
            "bilateral_passes": 3,
            "num_colors": 5,
            "edge_threshold1": 150,
            "edge_threshold2": 250,
            "edge_strength": 0.8
        }
    }
    
    params = intensity_params[intensity_lower]
    
    # Step 2: Apply bilateral filtering for edge-preserving smoothing
    filtered = image.copy()
    for _ in range(params["bilateral_passes"]):
        filtered = cv2.bilateralFilter(
            filtered,
            d=9,
            sigmaColor=75,
            sigmaSpace=75
        )
    
    # Step 3: Apply color quantization to reduce colors
    quantized = color_quantization(filtered, k=params["num_colors"])
    
    # Step 4: Apply Canny edge detection
    edges = apply_canny_edge(
        filtered,
        threshold1=params["edge_threshold1"],
        threshold2=params["edge_threshold2"]
    )
    
    # Step 5: Combine edges with quantized image
    # Create 3-channel edge mask (invert for black edges on colored background)
    edges_inv = cv2.bitwise_not(edges)
    edges_3channel = cv2.cvtColor(edges_inv, cv2.COLOR_GRAY2BGR)
    
    # Blend quantized image with edges using weighted combination
    # This creates the cartoon outline effect
    edge_weight = params["edge_strength"]
    cartoon_final = cv2.addWeighted(
        quantized,
        1.0,
        edges_3channel,
        -edge_weight,  # Negative to darken where edges are
        0
    )
    
    # Optional: Apply morphological operations to enhance edges
    # Create kernel for edge enhancement
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    cartoon_final = cv2.morphologyEx(cartoon_final, cv2.MORPH_CLOSE, kernel)
    
    # Resize back to original dimensions if we resized earlier
    if (original_height, original_width) != (image.shape[0], image.shape[1]):
        cartoon_final = cv2.resize(
            cartoon_final,
            (original_width, original_height),
            interpolation=cv2.INTER_LINEAR
        )
    
    return cartoon_final


def apply_sketch_effect(
    image_source: Union[str, np.ndarray],
    intensity: str = "medium"
) -> np.ndarray:
    """
    Apply pencil sketch effect to image.
    
    Creates a pencil sketch appearance using:
    1. Convert to grayscale
    2. Invert the grayscale image
    3. Apply Gaussian blur
    4. Color dodge blend (inverted + blurred)
    5. Adjust contrast based on intensity
    
    Args:
        image_source: File path (str) or image array (np.ndarray)
        intensity: Sketch intensity level (default: "medium")
                  - "light": Subtle sketch, less detail
                  - "medium": Balanced sketch effect
                  - "strong": Heavy sketch with high contrast
        
    Returns:
        np.ndarray: Sketch effect image (grayscale)
        
    Raises:
        ValueError: If intensity is not valid
    """
    # Validate intensity parameter
    intensity_lower = intensity.lower()
    valid_intensities = {"light", "medium", "strong"}
    
    if intensity_lower not in valid_intensities:
        raise ValueError(
            f"intensity must be one of {valid_intensities}, got '{intensity}'"
        )
    
    # Load image
    image = load_image(image_source)
    
    # Define parameters based on intensity
    sketch_params = {
        "light": {
            "blur_kernel": 5,
            "contrast_factor": 1.2,
            "brightness_offset": 10
        },
        "medium": {
            "blur_kernel": 7,
            "contrast_factor": 1.5,
            "brightness_offset": 0
        },
        "strong": {
            "blur_kernel": 9,
            "contrast_factor": 1.8,
            "brightness_offset": -10
        }
    }
    
    params = sketch_params[intensity_lower]
    
    # Step 1: Convert to grayscale
    gray = convert_to_grayscale(image)
    
    # Step 2: Invert grayscale image
    inverted = cv2.bitwise_not(gray)
    
    # Step 3: Apply Gaussian blur to inverted image
    blurred = cv2.GaussianBlur(
        inverted,
        (params["blur_kernel"], params["blur_kernel"]),
        0
    )
    
    # Step 4: Color dodge blend mode
    # Formula (safe float implementation): sketch = (gray * 255) / (255 - blurred)
    # Use float computations to avoid OpenCV arithm type-mismatch errors
    gray_f = gray.astype(np.float32)
    blurred_f = blurred.astype(np.float32)
    denom = 255.0 - blurred_f
    # Prevent division by zero
    denom[denom == 0] = 1.0
    sketch_f = (gray_f * 255.0) / denom
    sketch = np.uint8(np.clip(sketch_f, 0, 255))
    
    # Step 5: Adjust contrast
    # Use CLAHE (Contrast Limited Adaptive Histogram Equalization) for smooth contrast adjustment
    clahe = cv2.createCLAHE(
        clipLimit=params["contrast_factor"] * 2,
        tileGridSize=(8, 8)
    )
    sketch = clahe.apply(sketch)
    
    # Adjust brightness
    if params["brightness_offset"] != 0:
        sketch = cv2.convertScaleAbs(
            sketch.astype(np.float32) + params["brightness_offset"],
            alpha=1.0,
            beta=0
        )
        sketch = np.uint8(np.clip(sketch, 0, 255))
    
    return sketch


def reduce_color_saturation(
    image_source: Union[str, np.ndarray],
    saturation_factor: float = 0.4
) -> np.ndarray:
    """
    Reduce color saturation of an image.
    
    Converts image to HSV, reduces saturation, then converts back to BGR.
    
    Args:
        image_source: File path (str) or image array (np.ndarray)
        saturation_factor: Factor to reduce saturation (default: 0.4)
                          Range: 0.0 (grayscale) to 1.0 (original colors)
        
    Returns:
        np.ndarray: Image with reduced saturation
    """
    # Load image
    image = load_image(image_source)
    
    # Convert BGR to HSV color space
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
    
    # Reduce saturation (S channel is at index 1)
    hsv[:, :, 1] = hsv[:, :, 1] * saturation_factor
    
    # Clip values to valid range
    hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)
    
    # Convert back to BGR
    hsv = np.uint8(hsv)
    desaturated = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    
    return desaturated


def apply_pencil_color(
    image_source: Union[str, np.ndarray],
    intensity: str = "medium"
) -> np.ndarray:
    """
    Apply colored pencil effect to image.
    
    Creates a colored pencil sketch appearance by:
    1. Generating pencil sketch from image
    2. Reducing color saturation of original
    3. Blending sketch with desaturated colors
    
    Args:
        image_source: File path (str) or image array (np.ndarray)
        intensity: Effect intensity level (default: "medium")
                  - "light": Subtle colored pencil effect
                  - "medium": Balanced colored pencil
                  - "strong": Strong sketch with muted colors
        
    Returns:
        np.ndarray: Colored pencil effect image (BGR format)
    """
    # Load image
    image = load_image(image_source)
    
    # Define parameters based on intensity
    pencil_params = {
        "light": {
            "sketch_intensity": "light",
            "saturation_factor": 0.6,
            "sketch_blend_weight": 0.3
        },
        "medium": {
            "sketch_intensity": "medium",
            "saturation_factor": 0.5,
            "sketch_blend_weight": 0.5
        },
        "strong": {
            "sketch_intensity": "strong",
            "saturation_factor": 0.3,
            "sketch_blend_weight": 0.7
        }
    }
    
    params = pencil_params[intensity.lower()]
    
    # Step 1: Generate pencil sketch
    sketch = apply_sketch_effect(image, intensity=params["sketch_intensity"])
    
    # Convert sketch to 3-channel for blending
    sketch_3channel = cv2.cvtColor(sketch, cv2.COLOR_GRAY2BGR)
    
    # Step 2: Reduce color saturation
    desaturated = reduce_color_saturation(
        image,
        saturation_factor=params["saturation_factor"]
    )
    
    # Step 3: Blend sketch with desaturated colors
    # Use weighted blend: combine colored image with sketch overlay
    sketch_weight = params["sketch_blend_weight"]
    color_weight = 1.0 - sketch_weight
    
    pencil_color = cv2.addWeighted(
        desaturated,
        color_weight,
        sketch_3channel,
        sketch_weight,
        0
    )
    
    return pencil_color
    print("Image Processing Module")
    print("=" * 50)
    
    # Example: Create a sample image for testing
    sample_image = np.random.randint(0, 256, (400, 400, 3), dtype=np.uint8)
    
    # Apply different filters
    try:
        # Canny edge detection
        edges = apply_canny_edge(sample_image, threshold1=100, threshold2=200)
        print("✅ Canny edge detection applied successfully")
        print(f"   Edge image shape: {edges.shape}")
        
        # Adaptive threshold
        adaptive = apply_adaptive_threshold(sample_image)
        print("✅ Adaptive thresholding applied successfully")
        print(f"   Adaptive image shape: {adaptive.shape}")
        
        # Median blur
        blurred = apply_median_blur(sample_image, kernel_size=5)
        print("✅ Median blur applied successfully")
        print(f"   Blurred image shape: {blurred.shape}")
        
        # Bilateral filter
        bilateral = apply_bilateral_filter(sample_image, diameter=9, sigma_color=75, sigma_space=75)
        print("✅ Bilateral filter applied successfully")
        print(f"   Bilateral image shape: {bilateral.shape}")
        
        # Color quantization
        quantized = color_quantization(sample_image, k=8)
        print("✅ Color quantization applied successfully")
        print(f"   Quantized image shape: {quantized.shape}")
        
        # Cartoon effect
        cartoon, cartoon_edges = apply_cartoon_effect(sample_image, bilateral_passes=2, num_colors=8)
        print("✅ Cartoon effect applied successfully")
        print(f"   Cartoon image shape: {cartoon.shape}")
        print(f"   Cartoon edges shape: {cartoon_edges.shape}")
        
        # Classic cartoon with different intensities
        print("\n📊 Testing Classic Cartoon Effects:")
        for intensity in ["light", "medium", "strong"]:
            classic_cartoon = apply_classic_cartoon(sample_image, intensity=intensity)
            print(f"✅ Classic cartoon ({intensity}) applied successfully")
            print(f"   Output shape: {classic_cartoon.shape}")
        
        # Sketch effect with different intensities
        print("\n✏️ Testing Sketch Effects:")
        for intensity in ["light", "medium", "strong"]:
            sketch = apply_sketch_effect(sample_image, intensity=intensity)
            print(f"✅ Sketch effect ({intensity}) applied successfully")
            print(f"   Output shape: {sketch.shape}")
        
        # Pencil color effect with different intensities
        print("\n🎨 Testing Pencil Color Effects:")
        for intensity in ["light", "medium", "strong"]:
            pencil = apply_pencil_color(sample_image, intensity=intensity)
            print(f"✅ Pencil color ({intensity}) applied successfully")
            print(f"   Output shape: {pencil.shape}")
        
        # Get image info
        info = get_image_info(sample_image)
        print("\n✅ Image information retrieved:")
        for key, value in info.items():
            print(f"   {key}: {value}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
