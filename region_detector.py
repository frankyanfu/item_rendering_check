"""
Region detection — find bounding boxes around changed areas in a diff map.
Uses OpenCV contour detection on a thresholded diff map.
"""

import cv2
import numpy as np
from PIL import Image


def find_changed_regions(
    diff_map: np.ndarray,
    blurred_diff: np.ndarray,
    min_area: int = 100,
    threshold: float = 0.1,
) -> list:
    """
    Find bounding boxes of changed regions in a diff map.

    Args:
        diff_map: raw float32 per-pixel diff (0-1), from skimage
        blurred_diff: gaussian-blurred version of diff_map
        min_area: ignore regions smaller than this many pixels
        threshold: binarization threshold for the diff map

    Returns:
        List of dicts with keys: x, y, width, height, area, mean_intensity
    """
    # Threshold the blurred diff to create binary mask
    _, binary = cv2.threshold(blurred_diff.astype(np.float32), threshold, 255, cv2.THRESH_BINARY)
    binary_uint8 = binary.astype(np.uint8)

    # Morphological close to merge nearby blobs
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    closed = cv2.morphologyEx(binary_uint8, cv2.MORPH_CLOSE, kernel)

    # Find contours
    contours, hierarchy = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    regions = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        # Mean intensity in the original diff map for this region
        roi = diff_map[y:y+h, x:x+w]
        mean_intensity = float(roi.mean())
        regions.append({
            'x': int(x),
            'y': int(y),
            'width': int(w),
            'height': int(h),
            'area': int(area),
            'mean_intensity': round(mean_intensity, 4),
        })

    # Sort by area descending
    regions.sort(key=lambda r: r['area'], reverse=True)
    return regions


def annotate_image(img: Image.Image, regions: list, label: str = "CHANGE") -> Image.Image:
    """
    Draw bounding boxes around changed regions on the image.

    Returns a copy of the image with rectangles drawn.
    """
    result = img.copy().convert('RGB')
    draw = np.array(result)
    draw = cv2.cvtColor(draw, cv2.COLOR_RGB2BGR)

    color = (0, 0, 255)  # red in BGR

    for i, region in enumerate(regions):
        x, y, w, h = region['x'], region['y'], region['width'], region['height']
        cv2.rectangle(draw, (x, y), (x + w, y + h), color, 2)
        # Label
        cv2.putText(draw, f"#{i+1}", (x + 4, y + 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        cv2.putText(draw, f"{w}x{h}", (x + 4, y + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

    draw = cv2.cvtColor(draw, cv2.COLOR_BGR2RGB)
    return Image.fromarray(draw)


def annotated_with_diff_overlay(img: Image.Image, diff_map: np.ndarray, regions: list) -> Image.Image:
    """
    Create an annotated image with diff heatmap overlay and bounding boxes.
    """
    result = img.copy().convert('RGB')
    arr = np.array(result)

    # Create heatmap from diff_map (0-1 → 0-255)
    heatmap = (diff_map * 255).astype(np.uint8)
    heatmap_color = cv2.applyColorMap(heatmap, cv2.COLOR_GRAY2BGR)

    # Blend: 50% original, 50% heatmap
    blended = cv2.addWeighted(arr, 0.5, heatmap_color, 0.5, 0)

    # Draw bounding boxes in bright green
    for i, region in enumerate(regions):
        x, y, w, h = region['x'], region['y'], region['width'], region['height']
        cv2.rectangle(blended, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(blended, f"#{i+1}", (x + 4, y + 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

    return Image.fromarray(blended.astype(np.uint8))