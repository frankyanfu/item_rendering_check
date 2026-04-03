"""
Multi-table detection from screenshots using OpenCV grid detection + Tesseract OCR.
Detects multiple tables per image by clustering grid line regions spatially.

No LLM required — fully local.
"""

import logging
import cv2
import numpy as np
from PIL import Image
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)


def detect_table_grid(img: Image.Image, min_line_length: int = 50) -> Optional[dict]:
    """
    Detect if an image region contains a table (grid of horizontal/vertical lines).
    Returns grid dict or None.
    """
    arr = np.array(img.convert('L'))
    blurred = cv2.GaussianBlur(arr, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150, apertureSize=3)

    lines = cv2.HoughLinesP(
        edges, rho=1, theta=np.pi / 180, threshold=30,
        minLineLength=min_line_length, maxLineGap=10,
    )
    if lines is None:
        return None

    horizontal = []
    vertical = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
        if angle < 5:
            horizontal.append((x1, y2, x2, y2))  # y1==y2 for horizontal
        elif 85 < angle < 95:
            vertical.append((x1, y1, x2, y2))

    if not horizontal or not vertical:
        return None

    horizontal = sorted(horizontal, key=lambda l: l[1])
    vertical = sorted(vertical, key=lambda l: l[0])

    v_x1 = min((l[0] for l in vertical), default=0)
    v_x2 = max((l[2] for l in vertical), default=img.width)
    h_y1 = min((l[1] for l in horizontal), default=0)
    h_y2 = max((l[3] for l in horizontal), default=img.height)

    return {
        'horizontal_lines': horizontal,
        'vertical_lines': vertical,
        'num_rows': len(horizontal) + 1,
        'num_cols': len(vertical) + 1,
        'bbox': {'x1': v_x1, 'y1': h_y1, 'x2': v_x2, 'y2': h_y2},
    }


def extract_table_cells(img: Image.Image, grid: dict, ocr_func=None) -> List[List[str]]:
    """Extract text from each cell of a detected table."""
    if ocr_func is None:
        import pytesseract
        def ocr_func(crop):
            return pytesseract.image_to_string(crop, config='--psm 7').strip()

    h_lines = grid['horizontal_lines']
    v_lines = grid['vertical_lines']
    rows = []

    # Only extract cells between adjacent grid lines (not above/below/left/right of borders)
    for i in range(len(h_lines) - 1):
        y_top = h_lines[i][1]
        y_bot = h_lines[i + 1][1]
        row_cells = []
        for j in range(len(v_lines) - 1):
            x_left = v_lines[j][0]
            x_right = v_lines[j + 1][0]
            pad = 3
            x_left = max(0, x_left + pad)
            y_top = max(0, y_top + pad)
            x_right = min(img.width, x_right - pad)
            y_bot = min(img.height, y_bot - pad)
            if x_right <= x_left or y_bot <= y_top:
                row_cells.append('')
                continue
            cell_crop = img.crop((x_left, y_top, x_right, y_bot))
            row_cells.append(ocr_func(cell_crop))
        rows.append(row_cells)

    return rows


def _table_to_csv(rows: List[List[str]]) -> str:
    import io, csv
    output = io.StringIO()
    csv.writer(output).writerows(rows)
    return output.getvalue()


def _grid_bboxes_from_lines(img: Image.Image) -> List[dict]:
    """
    Find all grid clusters in the image using morphological line extraction
    and connected component analysis.

    Uses directional erosion/dilation to isolate long horizontal and vertical
    lines, then groups them into separate grid structures using connected
    components. This separates table grids from equation/chart box borders.
    """
    arr = np.array(img.convert('L'))
    binary = cv2.adaptiveThreshold(
        arr, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 5
    )

    # --- Extract horizontal lines using a long horizontal kernel ---
    h_kernel_len = max(80, img.width // 5)
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (h_kernel_len, 1))
    h_mask = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel, iterations=1)

    # --- Extract vertical lines using a long vertical kernel ---
    v_kernel_len = max(40, img.height // 8)
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_kernel_len))
    v_mask = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_kernel, iterations=1)

    # --- Combine and find connected grid structures ---
    # Dilate slightly so lines that touch at corners connect into one component
    dilate_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    combined = cv2.bitwise_or(h_mask, v_mask)
    combined_dilated = cv2.dilate(combined, dilate_kernel, iterations=1)

    num_labels, labels = cv2.connectedComponents(combined_dilated)

    grids = []
    for label_id in range(1, num_labels):
        component_mask = (labels == label_id).astype(np.uint8) * 255

        # Extract h/v lines that belong to this component
        h_component = cv2.bitwise_and(h_mask, h_mask, mask=component_mask)
        v_component = cv2.bitwise_and(v_mask, v_mask, mask=component_mask)

        # Find line positions via projection within this component
        h_proj = np.sum(h_component, axis=1)
        v_proj = np.sum(v_component, axis=0)

        h_threshold = img.width * 0.08
        v_threshold = img.height * 0.03

        h_positions = _find_line_positions(h_proj, h_threshold, tolerance=5)
        v_positions = _find_line_positions(v_proj, v_threshold, tolerance=5)

        # A table needs at least 3 horizontal and 3 vertical lines
        # (2 borders + at least 1 internal separator in each direction)
        if len(h_positions) < 3 or len(v_positions) < 3:
            continue

        # Determine actual line extents from the component masks
        horizontal = []
        for y_pos in h_positions:
            row = h_component[y_pos, :]
            nonzero = np.where(row > 0)[0]
            if len(nonzero) > 0:
                horizontal.append((int(nonzero[0]), y_pos, int(nonzero[-1]), y_pos))

        vertical = []
        for x_pos in v_positions:
            col = v_component[:, x_pos]
            nonzero = np.where(col > 0)[0]
            if len(nonzero) > 0:
                vertical.append((x_pos, int(nonzero[0]), x_pos, int(nonzero[-1])))

        if len(horizontal) < 3 or len(vertical) < 3:
            continue

        # Length filter: keep lines >=50% of the longest in this component
        max_h_len = max(abs(l[2] - l[0]) for l in horizontal)
        horizontal = [l for l in horizontal if abs(l[2] - l[0]) >= max_h_len * 0.5]
        max_v_len = max(abs(l[3] - l[1]) for l in vertical)
        vertical = [l for l in vertical if abs(l[3] - l[1]) >= max_v_len * 0.5]

        if len(horizontal) < 3 or len(vertical) < 3:
            continue

        horizontal = sorted(horizontal, key=lambda l: l[1])
        vertical = sorted(vertical, key=lambda l: l[0])

        y_top = min(l[1] for l in horizontal)
        y_bot = max(l[3] for l in horizontal)
        x_left = min(l[0] for l in vertical)
        x_right = max(l[2] for l in vertical)

        if (x_right - x_left) < 80 or (y_bot - y_top) < 40:
            continue

        grids.append({
            'horizontal_lines': horizontal,
            'vertical_lines': vertical,
            'num_rows': max(1, len(horizontal) - 1),
            'num_cols': max(1, len(vertical) - 1),
            'bbox': {'x1': int(x_left), 'y1': int(y_top),
                     'x2': int(x_right), 'y2': int(y_bot)},
        })

    return grids


def _find_line_positions(projection: np.ndarray, threshold: float,
                         tolerance: int = 5) -> List[int]:
    """Find line positions from a projection profile.
    Groups nearby high-value positions and returns one position per group."""
    above = np.where(projection > threshold)[0]
    if len(above) == 0:
        return []
    groups: List[List[int]] = []
    current_group = [above[0]]
    for pos in above[1:]:
        if pos - current_group[-1] <= tolerance:
            current_group.append(pos)
        else:
            groups.append(current_group)
            current_group = [pos]
    groups.append(current_group)
    # Return the midpoint of each group
    return [int(np.mean(g)) for g in groups]


def detect_tables_multi(img: Image.Image, ocr_func=None) -> List[dict]:
    """
    Detect all tables in a single image.

    Returns list of dicts:
      [{'cells': [[...], ...], 'bbox': {x1,y1,x2,y2}, 'num_rows', 'num_cols'}, ...]
    """
    grids = _grid_bboxes_from_lines(img)
    results = []
    seen = set()

    for g in grids:
        bbox = g['bbox']
        key = (bbox['x1'] // 20, bbox['y1'] // 20, bbox['x2'] // 20, bbox['y2'] // 20)
        if key in seen:
            continue
        seen.add(key)

        cells = extract_table_cells(img, g, ocr_func)
        # Skip if too row-heavy (text lines detected as table)
        num_rows = len(cells)
        num_cols = max((len(r) for r in cells), default=0)
        if num_rows == 0 or num_cols == 0:
            continue
        if num_rows / num_cols > 15:
            continue  # likely text lines, not a table

        results.append({
            'cells': cells,
            'bbox': bbox,
            'num_rows': num_rows,
            'num_cols': num_cols,
            'csv': _table_to_csv(cells),
        })

    return results


def compare_tables_multi(img1: Image.Image, img2: Image.Image,
                         ocr_func=None) -> dict:
    """
    Detect and compare multiple tables between two images.

    Returns dict with:
      - tables1, tables2: list of detected tables from each image
      - count1, count2: number of tables detected
      - count_same: bool
      - pairings: [(t1_idx, t2_idx, same, num_diffs, differences)], matched by IoU
      - unpaired1, unpaired2: unmatched tables
      - same: True if all pairings match and no unpaired
      - verdict: 'identical' | 'count_mismatch' | 'content_diff' | 'one_missing'
    """
    tables1 = detect_tables_multi(img1, ocr_func)
    tables2 = detect_tables_multi(img2, ocr_func)

    count1 = len(tables1)
    count2 = len(tables2)

    if count1 == 0 and count2 == 0:
        return {
            'tables1': [], 'tables2': [], 'count1': 0, 'count2': 0,
            'count_same': True, 'pairings': [], 'unpaired1': [], 'unpaired2': [],
            'same': True, 'verdict': 'identical', 'all_cells1': [], 'all_cells2': [],
        }

    if count1 == 0 or count2 == 0:
        return {
            'tables1': tables1, 'tables2': tables2,
            'count1': count1, 'count2': count2,
            'count_same': False,
            'pairings': [],
            'unpaired1': tables1, 'unpaired2': tables2,
            'same': False, 'verdict': 'one_side_has_no_tables',
            'all_cells1': [c for t in tables1 for row in t['cells'] for c in row],
            'all_cells2': [c for t in tables2 for row in t['cells'] for c in row],
        }

    # Match tables by bounding box IoU (greedy)
    pairings = []
    used1 = set()
    used2 = set()

    def _iou(b1, b2):
        ox1 = max(b1['x1'], b2['x1']); oy1 = max(b1['y1'], b2['y1'])
        ox2 = min(b1['x2'], b2['x2']); oy2 = min(b1['y2'], b2['y2'])
        if ox1 >= ox2 or oy1 >= oy2:
            return 0.0
        inter = (ox2 - ox1) * (oy2 - oy1)
        area1 = (b1['x2'] - b1['x1']) * (b1['y2'] - b1['y1'])
        area2 = (b2['x2'] - b2['x1']) * (b2['y2'] - b2['y1'])
        union = area1 + area2 - inter
        return inter / union if union > 0 else 0.0

    # Sort by area (largest first) for consistent matching
    order1 = sorted(enumerate(tables1), key=lambda x: -((x[1]['bbox']['x2']-x[1]['bbox']['x1'])*(x[1]['bbox']['y2']-x[1]['bbox']['y1'])))
    order2 = sorted(enumerate(tables2), key=lambda x: -((x[1]['bbox']['x2']-x[1]['bbox']['x1'])*(x[1]['bbox']['y2']-x[1]['bbox']['y1'])))

    for i1, t1 in order1:
        best_j = None
        best_iou = 0.0
        for i2, t2 in order2:
            if i2 in used2:
                continue
            iou = _iou(t1['bbox'], t2['bbox'])
            if iou > 0.3 and iou > best_iou:
                best_iou = iou
                best_j = i2
        if best_j is not None:
            used1.add(i1)
            used2.add(best_j)
            # Compare cells
            cells1 = tables1[i1]['cells']
            cells2 = tables2[best_j]['cells']
            diffs = _cell_diffs(cells1, cells2)
            same = len(diffs) == 0
            pairings.append((i1, best_j, same, len(diffs), diffs))

    unpaired1 = [tables1[i] for i in range(count1) if i not in used1]
    unpaired2 = [tables2[i] for i in range(count2) if i not in used2]

    all_same = (
        len(unpaired1) == 0 and len(unpaired2) == 0 and all(p[2] for p in pairings)
    )

    verdict = 'identical' if all_same else (
        'count_mismatch' if (count1 != count2 and len(pairings) == 0) else 'content_diff'
    )

    return {
        'tables1': tables1, 'tables2': tables2,
        'count1': count1, 'count2': count2,
        'count_same': count1 == count2,
        'pairings': pairings,
        'unpaired1': unpaired1, 'unpaired2': unpaired2,
        'same': all_same, 'verdict': verdict,
        'all_cells1': [c for t in tables1 for row in t['cells'] for c in row],
        'all_cells2': [c for t in tables2 for row in t['cells'] for c in row],
    }


def _cell_diffs(cells1: List[List[str]], cells2: List[List[str]]) -> List[Tuple]:
    diffs = []
    max_r = max(len(cells1), len(cells2))
    max_c = max((len(r) for r in cells1 + cells2), default=0)
    for r in range(max_r):
        for c in range(max_c):
            v1 = cells1[r][c] if r < len(cells1) and c < len(cells1[r]) else ''
            v2 = cells2[r][c] if r < len(cells2) and c < len(cells2[r]) else ''
            if v1 != v2:
                diffs.append((r, c, v1, v2))
    return diffs


# ── Legacy single-table API ────────────────────────────────────────────────────

def compare_tables(img1, img2, ocr_func=None):
    """Legacy single-table comparator. Wraps multi-table for backward compat."""
    result = compare_tables_multi(img1, img2, ocr_func)

    # Flatten for legacy callers
    if result['count1'] == 0 and result['count2'] == 0:
        flat = {**result, 'table1': [], 'table2': [], 'table1_csv': '', 'table2_csv': ''}
    elif result['count1'] == 0 or result['count2'] == 0:
        t1 = result['tables1'][0]['cells'] if result['tables1'] else []
        t2 = result['tables2'][0]['cells'] if result['tables2'] else []
        flat = {
            **result,
            'table1': t1, 'table2': t2,
            'table1_csv': result['tables1'][0]['csv'] if result['tables1'] else '',
            'table2_csv': result['tables2'][0]['csv'] if result['tables2'] else '',
        }
    else:
        # Find best pairing
        if result['pairings']:
            i1, i2, same, nd, diffs = result['pairings'][0]
            t1 = result['tables1'][i1]['cells']
            t2 = result['tables2'][i2]['cells']
        else:
            t1 = result['tables1'][0]['cells'] if result['tables1'] else []
            t2 = result['tables2'][0]['cells'] if result['tables2'] else []
            same = False
            nd = sum(1 for p in result['pairings'] if not p[2])
            diffs = []
        flat = {
            **result,
            'table1': t1, 'table2': t2,
            'table1_csv': _table_to_csv(t1),
            'table2_csv': _table_to_csv(t2),
            'same': same,
            'num_differences': nd,
            'differences': diffs,
            'verdict': 'identical' if same else 'table_differs',
        }
    return flat
