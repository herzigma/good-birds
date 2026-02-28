import cv2
import numpy as np
from PIL import Image

from good_birds.scorer import calculate_sharpness, calculate_exposure

def _create_synthetic_image(sharp: bool) -> Image.Image:
    """Create a synthetic image (e.g. checkerboard) that is either sharp or blurry."""
    # 100x100 grayscale
    img_array = np.zeros((100, 100), dtype=np.uint8)
    
    # Create high contrast edge (like a sharp subject)
    img_array[25:75, 25:75] = 255
    
    if not sharp:
        # Blur the image significantly
        img_array = cv2.GaussianBlur(img_array, (15, 15), 0)
        
    return Image.fromarray(img_array)

def test_sharpness_calculation():
    sharp_img = _create_synthetic_image(sharp=True)
    blurry_img = _create_synthetic_image(sharp=False)
    
    sharp_score_whole = calculate_sharpness(sharp_img, center_weight=1.0)
    blurry_score_whole = calculate_sharpness(blurry_img, center_weight=1.0)
    
    # Sharp image should have much higher variance
    assert sharp_score_whole > blurry_score_whole * 2
    
def test_sharpness_center_weighting():
    # Image with sharp edges ONLY on the outside
    img_array = np.zeros((100, 100), dtype=np.uint8)
    img_array[0:10, 0:10] = 255 # Top left corner sharp
    img_array[90:100, 90:100] = 255 # Bottom right corner sharp
    
    img = Image.fromarray(img_array)
    
    score_unweighted = calculate_sharpness(img, center_weight=1.0)
    score_weighted = calculate_sharpness(img, center_weight=10.0) # heavily weight center
    
    # Since the center is completely blank (0 variance), weighting it heavily
    # should reduce the overall score compared to unweighted.
    assert score_weighted < score_unweighted

def test_exposure_calculation():
    # Perfect exposure (mostly midtones, some shadows, some highlights)
    img_perfect = np.random.randint(50, 200, (100, 100), dtype=np.uint8)
    # Give it some black and white for dynamic range
    img_perfect[0:5, 0:5] = 0
    img_perfect[95:100, 95:100] = 255
    score_perfect = calculate_exposure(Image.fromarray(img_perfect))
    
    # Blown highlights (lots of 255)
    img_blown = np.ones((100, 100), dtype=np.uint8) * 200
    img_blown[10:90, 10:90] = 255 # large clipped area
    score_blown = calculate_exposure(Image.fromarray(img_blown))
    
    # Crushed shadows (lots of 0)
    img_crushed = np.ones((100, 100), dtype=np.uint8) * 50
    img_crushed[10:90, 10:90] = 0 # large crushed area
    score_crushed = calculate_exposure(Image.fromarray(img_crushed))
    
    # Perfect should be higher than the flawed ones
    assert score_perfect > score_blown
    assert score_perfect > score_crushed
    
    # Blown highlights are penalized more than crushed shadows in our heuristic
    assert score_crushed >= score_blown
