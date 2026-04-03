"""
Main screenshot comparison orchestrator.
Handles three content layers, each supporting multiple detections per image:
  1. Text (Tesseract OCR + difflib)
  2. Equations — LaTeX via pix2tex (multi, spatial matching)
  3. Tables — OpenCV grid + OCR (multi, IoU matching)
  4. Charts/Graphs — OpenCV + Tesseract axis label OCR (multi detection)

Asymmetry: detects when one image has N items and the other has M (N≠M).

All fully local — no LLM API required.
"""

from PIL import Image
from pathlib import Path
from typing import Optional, Literal, List

from .text_diff import compare_text, extract_text


def load_image(path: str) -> Image.Image:
    return Image.open(path)


def compare(
    path1: str,
    path2: str,
    ocr_lang: Optional[str] = None,
    detect_equations: bool = True,
    detect_tables: bool = True,
    detect_graphs: bool = True,
) -> dict:
    """
    Compare two screenshots across content layers.

    Returns dict with:
      - verdict: 'identical' | 'text_diff' | 'equation_diff' | 'table_diff' |
                 'graph_diff' | 'multiple_diff'
      - same: bool — True if nothing differs
      - text_result: OCR text comparison result
      - equation_result: multi-equation comparison result
      - table_result: multi-table comparison result
      - graph_result: multi-graph comparison result
      - summary: human-readable summary
      - findings: list of human-readable finding strings
    """
    img1 = load_image(path1)
    img2 = load_image(path2)

    findings: List[str] = []
    all_same = True

    # ── Layer 1: Plain text (OCR) ───────────────────────────────────────────
    text_result = compare_text(img1, img2, lang=ocr_lang)
    has_text_diff = text_result['has_text_changes']
    if has_text_diff:
        all_same = False
        findings.append(
            f"Text: {text_result.get('similarity', 0):.0%} similar, "
            f"{text_result['diff']['num_added']} line(s) added, "
            f"{text_result['diff']['num_removed']} removed"
        )

    # ── Layer 2: Equations (multi) ─────────────────────────────────────────
    equation_result: Optional[dict] = None
    if detect_equations:
        equation_result = _compare_equations_multi(img1, img2)
        if equation_result and not equation_result['same']:
            all_same = False
            eq = equation_result
            if eq['verdict'] == 'one_side_has_no_equations':
                findings.append(
                    f"Equations: {eq['count1']} vs {eq['count2']} "
                    f"({'missing in img2' if eq['count2'] == 0 else 'extra in img1'})"
                )
            elif eq['verdict'] == 'count_mismatch':
                findings.append(
                    f"Equations: count differs ({eq['count1']} vs {eq['count2']}), "
                    f"{len(eq['unpaired1'])} unpaired, {len(eq['unpaired2'])} extra"
                )
            elif eq['verdict'] == 'content_diff':
                n_same = sum(1 for p in eq['pairings'] if len(p) > 2 and p[2])
                n_diff = sum(1 for p in eq['pairings'] if not (len(p) > 2 and p[2]))
                unpaired = len(eq['unpaired1']) + len(eq['unpaired2'])
                if unpaired > 0:
                    findings.append(
                        f"Equations: {n_same} identical, {n_diff} differ, "
                        f"{unpaired} unpaired (img1={eq['count1']}, img2={eq['count2']})"
                    )
                else:
                    findings.append(f"Equations: {n_same} identical, {n_diff} differ")

    # ── Layer 3: Tables (multi) ───────────────────────────────────────────
    table_result: Optional[dict] = None
    if detect_tables:
        table_result = _compare_tables_multi(img1, img2, ocr_lang=ocr_lang)
        if table_result and not table_result['same']:
            all_same = False
            tr = table_result
            if tr['verdict'] == 'one_side_has_no_tables':
                findings.append(
                    f"Tables: {'present' if tr['count1'] > 0 else 'missing'} in img1, "
                    f"{'present' if tr['count2'] > 0 else 'missing'} in img2"
                )
            elif tr['verdict'] == 'count_mismatch':
                total_diffs = sum(p[3] for p in tr['pairings'])
                findings.append(
                    f"Tables: count differs ({tr['count1']} vs {tr['count2']}), "
                    f"cells differ: {total_diffs}"
                )
            elif tr['verdict'] == 'content_diff':
                n_same_tables = sum(1 for p in tr['pairings'] if p[2])
                n_diff_tables = sum(1 for p in tr['pairings'] if not p[2])
                n_unpaired = len(tr['unpaired1']) + len(tr['unpaired2'])
                total_cell_diffs = sum(p[3] for p in tr['pairings'])
                if n_unpaired > 0:
                    findings.append(
                        f"Tables: {n_same_tables} identical, {n_diff_tables} differ, "
                        f"{n_unpaired} unpaired, {total_cell_diffs} cell(s) different"
                    )
                else:
                    findings.append(
                        f"Tables: {n_diff_tables} differ, {total_cell_diffs} cell(s) different"
                        if n_diff_tables > 0 else
                        f"Tables: identical ({tr['count1']} table(s))"
                    )

    # ── Layer 4: Graphs (multi) ───────────────────────────────────────────
    graph_result: Optional[dict] = None
    if detect_graphs:
        graph_result = _compare_graphs_multi(img1, img2, ocr_lang=ocr_lang)
        if graph_result and not graph_result['same']:
            all_same = False
            gr = graph_result
            if gr['verdict'] == 'one_side_has_no_charts':
                findings.append(
                    f"Charts: {'present' if gr['count1'] > 0 else 'missing'} in img1, "
                    f"{'present' if gr['count2'] > 0 else 'missing'} in img2"
                )
            elif gr['verdict'] == 'count_mismatch':
                findings.append(
                    f"Charts: count differs ({gr['count1']} vs {gr['count2']}), "
                    f"{len(gr['unpaired1'])} unpaired"
                )
            elif gr['verdict'] == 'content_diff':
                n_same = sum(1 for p in gr['pairings'] if p[2])
                n_diff = sum(1 for p in gr['pairings'] if not p[2])
                n_unpaired = len(gr['unpaired1']) + len(gr['unpaired2'])
                if n_unpaired > 0:
                    findings.append(f"Charts: {n_same} identical, {n_diff} differ, {n_unpaired} extra")
                else:
                    findings.append(f"Charts: {n_same} identical, {n_diff} differ")

    # ── Determine verdict ──────────────────────────────────────────────────
    diff_types = []
    if has_text_diff:
        diff_types.append('text')
    eq_layer_diff = equation_result and not equation_result['same']
    tbl_layer_diff = table_result and not table_result['same']
    gr_layer_diff = graph_result and not graph_result['same']

    if eq_layer_diff:
        diff_types.append('equation')
    if tbl_layer_diff:
        diff_types.append('table')
    if gr_layer_diff:
        diff_types.append('graph')

    if not diff_types:
        verdict: Literal['identical', 'text_diff', 'equation_diff', 'table_diff',
                         'graph_diff', 'multiple_diff'] = 'identical'
    elif len(diff_types) == 1:
        verdict = f"{diff_types[0]}_diff"
    else:
        verdict = 'multiple_diff'

    summary = "All content layers are identical" if all_same else \
             f"Differences detected: {', '.join(diff_types)}"

    return {
        'same': all_same,
        'verdict': verdict,
        'text_result': text_result,
        'equation_result': equation_result,
        'table_result': table_result,
        'graph_result': graph_result,
        'summary': summary,
        'findings': findings,
        'img1_size': img1.size,
        'img2_size': img2.size,
    }


# ── Private multi-layer comparators ───────────────────────────────────────────

def _compare_equations_multi(img1: Image.Image, img2: Image.Image) -> Optional[dict]:
    """Multi-equation comparison using spatial matching."""
    try:
        from .equation import compare_equations_multi
    except ImportError:
        return None
    try:
        return compare_equations_multi(img1, img2)
    except Exception:
        return None


def _compare_tables_multi(img1: Image.Image, img2: Image.Image,
                          ocr_lang: Optional[str]) -> Optional[dict]:
    """Multi-table comparison using IoU bounding-box matching."""
    try:
        from .table import compare_tables_multi
    except ImportError:
        return None
    try:
        if ocr_lang:
            import pytesseract
            def ocr_fn(crop):
                return pytesseract.image_to_string(crop, lang=ocr_lang, config='--psm 7').strip()
        else:
            ocr_fn = None
        return compare_tables_multi(img1, img2, ocr_func=ocr_fn)
    except Exception:
        return None


def _compare_graphs_multi(img1: Image.Image, img2: Image.Image,
                          ocr_lang: Optional[str]) -> Optional[dict]:
    """Multi-chart comparison using spatial matching."""
    try:
        import cv2, numpy as np
    except ImportError:
        return None
    try:
        import pytesseract

        def ocr(img_crop):
            return pytesseract.image_to_string(img_crop, lang=ocr_lang or 'eng').strip()

        regions1 = _find_all_chart_regions(img1)
        regions2 = _find_all_chart_regions(img2)

        labels1 = [_extract_chart_labels(img1, r, ocr) for r in regions1]
        labels2 = [_extract_chart_labels(img2, r, ocr) for r in regions2]

        count1 = len(regions1)
        count2 = len(regions2)

        if count1 == 0 and count2 == 0:
            return None

        if count1 == 0 or count2 == 0:
            return {
                'count1': count1, 'count2': count2, 'count_same': False,
                'pairings': [], 'unpaired1': regions1, 'unpaired2': regions2,
                'same': False, 'verdict': 'one_side_has_no_charts',
            }

        # Match by IoU
        pairings = []
        used1 = set(); used2 = set()

        def _iou(r1, r2):
            x1, y1 = r1.get('x', 0), r1.get('y', 0)
            w1, h1 = r1.get('width', 0), r1.get('height', 0)
            x2, y2 = r2.get('x', 0), r2.get('y', 0)
            w2, h2 = r2.get('width', 0), r2.get('height', 0)
            ox1 = max(x1, x2); oy1 = max(y1, y2)
            ox2 = min(x1+w1, x2+w2); oy2 = min(y1+h1, y2+h2)
            if ox1 >= ox2 or oy1 >= oy2:
                return 0.0
            inter = (ox2-ox1)*(oy2-oy1)
            area1 = w1*h1; area2 = w2*h2
            return inter / (area1+area2-inter) if (area1+area2-inter) > 0 else 0.0

        order1 = sorted(enumerate(regions1),
                       key=lambda x: -((x[1].get('width',0))*(x[1].get('height',0))))
        order2 = sorted(enumerate(regions2),
                       key=lambda x: -((x[1].get('width',0))*(x[1].get('height',0))))

        for i1, r1 in order1:
            best_j, best_iou = None, 0.0
            for i2, r2 in order2:
                if i2 in used2:
                    continue
                iou = _iou(r1, r2)
                if iou > 0.3 and iou > best_iou:
                    best_iou = iou; best_j = i2
            if best_j is not None:
                used1.add(i1); used2.add(best_j)
                l1 = labels1[i1] or {}
                l2 = labels2[best_j] or {}
                same = (l1 == l2) if (l1 and l2) else False
                pairings.append((i1, best_j, same))

        unpaired1 = [r for i, r in enumerate(regions1) if i not in used1]
        unpaired2 = [r for i, r in enumerate(regions2) if i not in used2]

        all_same = len(unpaired1) == 0 and len(unpaired2) == 0 and all(p[2] for p in pairings)
        verdict = 'identical' if all_same else (
            'count_mismatch' if (count1 != count2 and len(pairings) == 0) else 'content_diff'
        )

        return {
            'count1': count1, 'count2': count2,
            'count_same': count1 == count2,
            'pairings': pairings,
            'unpaired1': unpaired1, 'unpaired2': unpaired2,
            'same': all_same, 'verdict': verdict,
        }
    except Exception:
        return None


def _find_all_chart_regions(img: Image.Image) -> List[dict]:
    """Find all chart/graph regions in an image using edge+line detection."""
    try:
        import cv2, numpy as np
    except Exception:
        return []

    arr = np.array(img.convert('RGB'))
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50,
                             minLineLength=30, maxLineGap=15)

    if lines is None:
        return []

    h_lines = []
    v_lines = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
        if angle < 10:
            h_lines.append((x1, y1, x2, y2))
        elif 80 < angle < 100:
            v_lines.append((x1, y1, x2, y2))

    if len(h_lines) < 2 or len(v_lines) < 2:
        return []

    h_lines.sort(key=lambda l: l[1])
    v_lines.sort(key=lambda l: l[0])

    y_axis_x = v_lines[0][0]
    x_axis_y = h_lines[-1][1]
    w = img.width - y_axis_x
    h = x_axis_y

    if w < 50 or h < 50:
        return []

    chart_type = _detect_chart_type(arr[y_axis_x:], y_axis_x, x_axis_y, w, h)

    return [{
        'x': int(y_axis_x), 'y': 0,
        'width': int(w), 'height': int(h),
        'chart_type': chart_type,
    }]


def _detect_chart_type(arr, x0, y0, w, h) -> str:
    """Detect chart type (bar vs line) by edge density analysis."""
    try:
        import cv2, numpy as np
    except Exception:
        return 'unknown'

    if h <= 0 or w <= 0:
        return 'unknown'
    region = arr[y0:y0+h, x0:x0+w]
    if region.size == 0:
        return 'unknown'
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY) if len(region.shape) == 3 else region
    edges = cv2.Canny(gray, 50, 150)
    v_k = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 5))
    h_k = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 1))
    vert = cv2.morphologyEx(edges, cv2.MORPH_OPEN, v_k).sum() / 255
    horiz = cv2.morphologyEx(edges, cv2.MORPH_OPEN, h_k).sum() / 255
    if vert > horiz * 2:
        return 'bar'
    elif horiz > vert * 2:
        return 'line'
    return 'unknown'


def _extract_chart_labels(img: Image.Image, region: dict, ocr_func) -> Optional[dict]:
    """Extract axis labels and title from a chart region."""
    try:
        x = region.get('x', 0)
        y = region.get('y', 0)
        w = region.get('width', 0)
        h = region.get('height', 0)
        if w <= 0 or h <= 0:
            return None
        labels = {}
        x_axis_h = min(30, h // 5)
        labels['x_axis'] = ocr_func(img.crop((x, y+h-x_axis_h, x+w, y+h)))
        y_axis_w = min(40, w // 5)
        labels['y_axis'] = ocr_func(img.crop((x, y, x+y_axis_w, y+h)))
        title_h = min(25, h // 6)
        labels['title'] = ocr_func(img.crop((x, y, x+w, y+title_h)))
        legend_crop = img.crop((x+w-60, y+10, x+w, y+h-10))
        labels['legend'] = ocr_func(legend_crop)
        return labels if any(labels.values()) else None
    except Exception:
        return None
