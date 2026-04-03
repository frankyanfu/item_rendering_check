"""
Perceptual hashing + SSIM-based visual difference detection.
"""

import imagehash
from PIL import Image
import numpy as np
from skimage.metrics import structural_similarity
from skimage import color
import cv2


def compute_phash(img: Image.Image) -> str:
    """Compute perceptual hash of an image."""
    return str(imagehash.phash(img))


def compute_average_hash(img: Image.Image) -> str:
    return str(imagehash.average_hash(img))


def compute_dhash(img: Image.Image) -> str:
    return str(imagehash.dhash(img))


def hamming_distance(hash1: str, hash2: str) -> int:
    """Compute hamming distance between two hash strings."""
    if len(hash1) != len(hash2):
        return abs(len(hash1) - len(hash2)) * 4
    return sum(c1 != c2 for c1, c2 in zip(hash1, hash2))


def quick_similarity(img1: Image.Image, img2: Image.Image) -> dict:
    """
    Fast pre-check using perceptual hashing.
    Returns hash-based similarity metrics.
    """
    hashes1 = {
        'phash': compute_phash(img1),
        'ahash': compute_average_hash(img1),
        'dhash': compute_dhash(img1),
    }
    hashes2 = {
        'phash': compute_phash(img2),
        'ahash': compute_average_hash(img2),
        'dhash': compute_dhash(img2),
    }

    distances = {k: hamming_distance(hashes1[k], hashes2[k]) for k in hashes1}
    max_bits = len(hashes1['phash']) * 4  # each hex char = 4 bits

    similarity = {k: 1 - (distances[k] / max_bits) for k in distances}

    return {
        'hashes1': hashes1,
        'hashes2': hashes2,
        'distances': distances,
        'similarity': similarity,
        'overall_hash_similarity': sum(similarity.values()) / len(similarity),
    }


def compute_ssim(img1: Image.Image, img2: Image.Image) -> tuple:
    """
    Compute SSIM between two images.
    Resizes img2 to match img1 if needed.

    Returns: (ssim_score, diff_map)
    """
    # Convert to same size
    if img1.size != img2.size:
        img2 = img2.resize(img1.size, Image.LANCZOS)

    # Convert to grayscale numpy arrays
    arr1 = np.array(img1.convert('L'))
    arr2 = np.array(img2.convert('L'))

    # Compute SSIM
    score, diff = structural_similarity(arr1, arr2, full=True)

    # diff is float64 0-1 per pixel
    return score, diff


def blur_diff_map(diff_map: np.ndarray, kernel_size: int = 5) -> np.ndarray:
    """Apply gaussian blur to diff map to reduce noise."""
    blurred = cv2.GaussianBlur(diff_map, (kernel_size, kernel_size), 0)
    return blurred


def threshold_diff(diff_map: np.ndarray, threshold: float = 0.1) -> np.ndarray:
    """Binarize the diff map at given threshold."""
    _, thresh = cv2.threshold(diff_map, threshold, 255, cv2.THRESH_BINARY)
    return thresh.astype(np.uint8)


def visual_diff(img1: Image.Image, img2: Image.Image, ssim_threshold: float = 0.95) -> dict:
    """
    Full visual diff pipeline.

    Returns dict with:
      - quick_result: perceptual hash comparison
      - ssim_score: 0-1 structural similarity
      - diff_map: raw float32 per-pixel diff (0-1)
      - blurred_diff: gaussian-blurred diff for region detection
      - is_different: bool based on ssim_threshold
    """
    quick = quick_similarity(img1, img2)
    ssim_score, diff_map = compute_ssim(img1, img2)
    blurred = blur_diff_map(diff_map)

    return {
        'quick_result': quick,
        'ssim_score': float(ssim_score),
        'diff_map': diff_map,
        'blurred_diff': blurred,
        'is_different': ssim_score < ssim_threshold,
    }