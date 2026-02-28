import cv2
import numpy as np
from PIL import Image
from typing import Tuple

from .models import PhotoInfo

def calculate_sharpness(img: Image.Image, center_weight: float = 1.0) -> float:
    """
    Calculate the sharpness of an image using the Variance of Laplacian method.
    Higher variance indicates a sharper image with more high-frequency detail.
    
    If center_weight > 1.0, the central region of the image is weighted more
    heavily, which is useful for bird photography where the subject is often centered.
    """
    # Convert PIL Image to cv2 grayscale numpy array
    img_array = np.array(img.convert('L'))
    
    if center_weight <= 1.0:
        # Standard Laplacian variance for the whole image
        variance = cv2.Laplacian(img_array, cv2.CV_64F).var()
        return float(variance)
    else:
        # Calculate for whole image
        laplacian = cv2.Laplacian(img_array, cv2.CV_64F)
        
        # Create a center mask
        h, w = img_array.shape
        center_x, center_y = w // 2, h // 2
        
        # Define center region (e.g., 50% of width/height)
        cw, ch = w // 2, h // 2
        x1, y1 = center_x - cw // 2, center_y - ch // 2
        x2, y2 = center_x + cw // 2, center_y + ch // 2
        
        # Calculate variance of the center region
        center_roi = laplacian[y1:y2, x1:x2]
        center_variance = center_roi.var()
        
        # Calculate variance of the outer region (rough estimate by taking whole minus center)
        # A more precise way would be to mask it, but this is faster
        whole_variance = laplacian.var()
        
        # Combine them
        # Give the center region more weight
        weighted_variance = (center_variance * center_weight + whole_variance) / (center_weight + 1)
        return float(weighted_variance)

def calculate_exposure(img: Image.Image) -> float:
    """
    Score the exposure of an image based on its histogram.
    Penalizes blown highlights (clipping) and crushed shadows.
    Returns a score where higher is better.
    """
    img_array = np.array(img.convert('L'))
    
    # Calculate histogram (256 bins for 8-bit grayscale)
    hist, _ = np.histogram(img_array, bins=256, range=(0, 256))
    
    total_pixels = img_array.size
    
    # Check for clipping
    # Blown highlights (pixels near 255)
    highlights_clipped = np.sum(hist[250:256]) / total_pixels
    # Crushed shadows (pixels near 0)
    shadows_crushed = np.sum(hist[0:5]) / total_pixels
    
    # We want a healthy midtone distribution. 
    # Let's say a "perfect" exposure score is 1.0, and we penalize it.
    score = 1.0
    
    # Heavy penalty for blown highlights (very bad in bird photos)
    score -= (highlights_clipped * 5.0) 
    
    # Moderate penalty for crushed shadows
    score -= (shadows_crushed * 2.0)
    
    # Ensure score doesn't go below 0
    return max(0.0, float(score))

def score_photo(
    info: PhotoInfo, 
    preview_img: Image.Image,
    sharp_weight: float = 0.7, 
    exposure_weight: float = 0.3,
    center_weight: float = 1.5
) -> Tuple[float, float, float]:
    """
    Returns (sharpness_score, exposure_score, combined_score)
    """
    sharpness = calculate_sharpness(preview_img, center_weight)
    exposure = calculate_exposure(preview_img)
    
    # We can't immediately combine them because sharpness is unnormalized
    # We'll return the raw scores and normalize them at the burst level later.
    return sharpness, exposure, 0.0 # Placeholder for combined
