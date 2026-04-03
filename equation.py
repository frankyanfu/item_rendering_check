"""
Multi-equation detection from screenshots using pix2tex (LatexOCR).
Splits image into regions to detect multiple equations per screenshot.

Key insight: pix2tex processes the whole image but gives one LaTeX output.
We detect candidate regions (math-like areas) via contour heuristics, then
validate each with pix2tex. Valid regions are spatially matched between images.

No LLM API required — fully local.
"""

from PIL import Image
from typing import Optional, List
import logging
import numpy as np

logging.getLogger('pix2tex').setLevel(logging.FATAL)


# ── Equation Extractor (single-equation, validated) ─────────────────────────

class SingleEquationExtractor:
    """Wraps pix2tex for single-equation validation within a region crop."""

    _instance: Optional['SingleEquationExtractor'] = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._model is None:
            self._model = self._load_model()

    def _load_model(self):
        try:
            import warnings
            warnings.filterwarnings('ignore')
            from pix2tex.cli import LatexOCR
            return LatexOCR()
        except Exception as e:
            raise RuntimeError(f"Failed to load pix2tex: {e}")

    def extract(self, img: Image.Image, timeout: float = 25.0) -> Optional[str]:
        try:
            import signal
            def _run():
                return self._model(img)
            def _handler(signum, frame):
                raise TimeoutError()
            old = signal.signal(signal.SIGALRM, _handler)
            signal.alarm(int(timeout))
            result = _run()
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)
            if result and self._is_valid(result):
                return result
            return None
        except Exception:
            return None

    def _is_valid(self, latex: str) -> bool:
        """Validate pix2tex output as genuine equation."""
        if not latex or len(latex.strip()) < 4:
            return False
        if self._is_garbage(latex):
            return False

        import re
        STRONG = [r'\frac', r'\sqrt', r'\sum', r'\int', r'\prod', r'\partial',
                  r'\nabla', r'\begin{bmatrix}', r'\begin{pmatrix}', r'\begin{cases}',
                  r'\begin{align}', r'\begin{array}', r'\mathbb', r'\mathbf', r'\mathrm',
                  r'\displaystyle', r'\textstyle', r'\lim', r'\sin', r'\cos', r'\tan',
                  r'\log', r'\alpha', r'\beta', r'\gamma', r'\theta', r'\pi', r'\sigma',
                  r'\lambda', r'\omega', r'\infty', r'\to', r'\rightarrow', r'\leq',
                  r'\geq', r'\neq', r'\approx', r'\equiv', r'\in', r'\forall', r'\exists',
                  r'\hat', r'\bar', r'\vec', r'\dot', r'\ddot', r'\underline', r'\overline',
                  r'\langle', r'\rangle', r'\mid', r'\Re', r'\Im',
                  r'\boldsymbol', r'\cal', r'\mathcal', r'\mathfrak']
        MATH = [r'\alpha', r'\beta', r'\gamma', r'\delta', r'\epsilon', r'\theta',
                r'\pi', r'\sigma', r'\mu', r'\nu', r'\rho', r'\lambda', r'\omega',
                r'\Gamma', r'\Delta', r'\Sigma', r'\sin', r'\cos', r'\tan', r'\log',
                r'\ln', r'\lim', r'\infty', r'\to', r'\rightarrow', r'\leftarrow',
                r'\cdot', r'\times', r'\div', r'\pm', r'\mp', r'\leq', r'\geq',
                r'\neq', r'\approx', r'\equiv', r'\subset', r'\supset', r'\in',
                r'\notin', r'\forall', r'\exists', r'\cup', r'\cap', r'\emptyset',
                r'\hat', r'\bar', r'\vec', r'\dot', r'\ddot', r'\underline',
                r'\overline', r'\langle', r'\rangle', r'\lfloor', r'\rfloor',
                r'\lceil', r'\rceil', r'\mid', r'\Re', r'\Im', r'\arg', r'\deg',
                r'\boldsymbol', r'\cal', r'\mathcal', r'\mathfrak']

        # Commands that indicate genuine math structure (not just formatting)
        OPERATORS = [r'\frac', r'\sqrt', r'\sum', r'\int', r'\prod',
                     r'\partial', r'\nabla', r'\lim', r'\sin', r'\cos',
                     r'\tan', r'\log', r'\ln', r'\to', r'\rightarrow',
                     r'\begin{bmatrix}', r'\begin{pmatrix}', r'\begin{cases}',
                     r'\begin{align}', r'\begin{array}']
        # Accent-only commands (these modify but don't replace the character)
        ACCENTS_ONLY = [r'\hat', r'\bar', r'\vec', r'\dot', r'\ddot']
        # Greek letters (upper and lower)
        GREEK = [r'\alpha', r'\beta', r'\gamma', r'\delta', r'\epsilon', r'\theta',
                 r'\pi', r'\sigma', r'\mu', r'\nu', r'\rho', r'\lambda', r'\omega',
                 r'\Gamma', r'\Delta', r'\Sigma', r'\Omega', r'\Theta', r'\Pi']
        # Wrappers that change character style to math font — ACCEPT if present
        WRAPPERS = [r'\boldsymbol', r'\mathcal', r'\mathfrak', r'\mathrm',
                    r'\displaystyle', r'\textstyle', r'\underline', r'\overline', r'\cal']
        # Formatting that wraps plain text (NOT math font) — reject
        TEXT_WRAPPERS = [r'\mathbf', r'\mathbb']

        has_operator = any(m in latex for m in OPERATORS)
        strong_count = sum(1 for m in STRONG if m in latex)
        wrapper_count = sum(1 for m in WRAPPERS if m in latex)
        text_wrapper_count = sum(1 for m in TEXT_WRAPPERS if m in latex)
        accent_only_count = sum(1 for m in ACCENTS_ONLY if m in latex)
        greek_count = sum(1 for m in GREEK if m in latex)
        braces_ok = abs(latex.count('{') - latex.count('}')) <= 3

        if strong_count >= 1 and braces_ok:
            if has_operator:
                return True  # Has real operator → accept
            if strong_count >= 2:
                return True  # 2+ strong commands → accept
            # Accent-only or text-wrapper → REJECT (formatting, not math)
            if accent_only_count >= 1 or text_wrapper_count >= 1:
                return False
            if wrapper_count >= 1:
                return True  # Math wrappers → accept
            return False
        return False

    def _is_garbage(self, latex: str) -> bool:
        """Detect hallucinated output on non-math images."""
        import re
        vdots = latex.count('\\vdots')
        ast = (latex.count('\\ast') + latex.count('{\\ast}') +
               latex.count('{{\\ast}}') + latex.count('^{*}') + latex.count('_{*}'))
        empty_cells = latex.count('{{}}')
        long_runs = re.findall(r'[a-zA-Z]{15,}', latex)

        repeat_count = 0
        for length in [4, 5, 6]:
            for i in range(len(latex) - length + 1):
                sub = latex[i:i+length]
                if latex.count(sub) >= 4:
                    repeat_count += 1

        clean = re.sub(r'[\{\}\\]', '', latex)
        unique = len(set(clean)) if clean else 0

        # Detect excessive repetition of the same Greek letter — hallmark of
        # pix2tex hallucination on non-math images (e.g. a chart with numbers)
        greek = re.findall(
            r'\\(alpha|beta|gamma|delta|epsilon|theta|pi|sigma|'
            r'mu|lambda|omega|rho|tau|phi|psi|zeta|eta|kappa|'
            r'Gamma|Delta|Sigma|Omega|Theta|Pi)(?![a-zA-Z])', latex)
        greek_repeat = len(greek) >= 4 and len(set(greek)) <= 2

        # Character frequency for keyboard-smash detection
        from collections import Counter
        freq = Counter(clean)
        max_freq_pct = max(freq.values()) / max(len(clean), 1) if clean else 0

        garbage_signals = [
            (vdots >= 2, "vdots"),
            (ast >= 5, "ast"),
            (empty_cells >= 5, "empty"),
            (len(long_runs) >= 3, "long_runs"),
            (repeat_count >= 3, "repeat"),
            (0 < len(clean) < 500 and len(set(clean)) / len(clean) < 0.08, "low_diversity"),
            (len(re.findall(r'\\[a-zA-Z]+', latex)) > 20, "too_many_cmds"),
            (greek_repeat, "greek_repeat"),
            # Check for \mathrm{text} with long pure-alphabetic content (hallucination)
            # Check for \mathrm{...} containing 8+ consecutive lowercase letters → hallucination
            (bool(re.findall(r'[\\]m' + r'athrm\{([^}]+)\}', latex)) and
             any(len(re.findall(r'[a-z]{8,}', m)) >= 1
                 for m in re.findall(r'[\\]m' + r'athrm\{([^}]+)\}', latex)),
             "mathrm_hallucination"),
        ]
        triggered = [d for c, d in garbage_signals if c]
        if len(triggered) >= 2:
            return True
        # Single strong signal: \mathrm hallucination alone is enough
        if 'mathrm_hallucination' in triggered:
            return True
        # Single signal with very dominant character (>20% same char) → keyboard smash
        if len(triggered) == 1 and max_freq_pct > 0.20:
            return True
        if vdots >= 3 or empty_cells >= 8 or (unique < 4 and len(latex) > 20):
            return True

        # Reject \begin{array} without real math commands
        REAL = [r'\\frac', r'\\sqrt', r'\\sum', r'\\int', r'\\prod', r'\\partial',
                r'\\alpha', r'\\beta', r'\\gamma', r'\\theta', r'\\pi', r'\\sigma',
                r'\\mu', r'\\lambda', r'\\omega', r'\\sin', r'\\cos', r'\\tan',
                r'\\log', r'\\lim', r'\\infty', r'\\to', r'\\rightarrow', r'\\langle',
                r'\\hat', r'\\bar', r'\\vec', r'\\dot', r'\\overline', r'\\underline']
        has_real = any(c in latex for c in REAL)
        if r'\begin{array}' in latex and not has_real:
            return True

        return False


# ── Multi-equation detection ──────────────────────────────────────────────────

def _find_equation_candidates(img: Image.Image) -> List[dict]:
    """
    Find candidate math equation regions in an image using contour detection.
    Returns list of {'bbox': (x1, y1, x2, y2), 'crop': PIL.Image} for each candidate.
    """
    import cv2

    arr = np.array(img.convert('RGB'))
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

    # Method 1: Detect italic-style text (common in rendered equations)
    # Look for regions with many slanted strokes using morphological operations
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))

    # Method 2: Try to find bordered equation boxes (highlighted/colored backgrounds)
    # Detect rectangles with contrasting backgrounds
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    candidates = []
    h, w = img.height, img.width

    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        area = cw * ch
        aspect = cw / max(ch, 1)

        # Filter by size and shape
        if area < 500 or area > w * h * 0.7:
            continue
        if cw < 30 or ch < 15:
            continue
        # Equations are usually wider than tall or roughly square
        if aspect < 0.3 or aspect > 12:
            continue

        # Check if region has a colored/boxed background (equation highlight)
        roi = arr[y:y+ch, x:x+cw]
        roi_gray = gray[y:y+ch, x:x+cw]
        roi_std = roi_gray.std()
        roi_mean = roi_gray.mean()

        # Candidate if: bordered region (std > threshold) OR tall enough
        if roi_std > 20 or ch > 30:
            crop = img.crop((x, y, x+cw, y+ch))
            candidates.append({
                'bbox': (x, y, x+cw, y+ch),
                'crop': crop,
                'cx': x + cw // 2,
                'cy': y + ch // 2,
            })

    # If no contour candidates, try grid-based fallback for full-width equation bands
    if not candidates:
        # Scan horizontal strips for math-like content (font changes, etc.)
        strip_h = max(30, h // 20)
        for y in range(0, h - strip_h, strip_h // 2):
            strip = img.crop((0, y, w, y + strip_h))
            strip_arr = np.array(strip.convert('L'))
            if strip_arr.std() > 25 and strip_arr.mean() < 230:
                candidates.append({
                    'bbox': (0, y, w, y + strip_h),
                    'crop': strip,
                    'cx': w // 2,
                    'cy': y + strip_h // 2,
                })

    # Deduplicate overlapping regions (NMS-style)
    candidates = _deduplicate_candidates(candidates, iou_thresh=0.4)
    return candidates


def _deduplicate_candidates(candidates: List[dict], iou_thresh: float = 0.4) -> List[dict]:
    """Remove highly overlapping candidate regions."""
    if not candidates:
        return []
    kept = []
    for cand in candidates:
        x1, y1, x2, y2 = cand['bbox']
        area = (x2 - x1) * (y2 - y1)
        overlap_found = False
        for k in kept:
            kx1, ky1, kx2, ky2 = k['bbox']
            ox1 = max(x1, kx1); oy1 = max(y1, ky1)
            ox2 = min(x2, kx2); oy2 = min(y2, ky2)
            if ox1 < ox2 and oy1 < oy2:
                overlap_area = (ox2 - ox1) * (oy2 - oy1)
                smaller = min(area, (kx2-kx1)*(ky2-ky1))
                if overlap_area / smaller > iou_thresh:
                    overlap_found = True
                    break
        if not overlap_found:
            kept.append(cand)
    return kept


def detect_equations_multi(img: Image.Image, timeout: float = 25.0) -> List[dict]:
    """
    Detect multiple equations in a single image.

    Returns list of dicts:
      [{'latex': str, 'bbox': (x1,y1,x2,y2), 'cx': int, 'cy': int}, ...]
    Empty list if no equations found.
    """
    extractor = SingleEquationExtractor()
    candidates = _find_equation_candidates(img)

    results = []
    for cand in candidates:
        latex = extractor.extract(cand['crop'], timeout=timeout)
        if latex:
            results.append({
                'latex': latex,
                'bbox': cand['bbox'],
                'cx': cand['cx'],
                'cy': cand['cy'],
            })

    # Sort by position (top-to-bottom, left-to-right)
    results.sort(key=lambda r: (r['cy'], r['cx']))
    return results


def compare_equations_multi(img1: Image.Image, img2: Image.Image,
                             timeout: float = 25.0) -> dict:
    """
    Detect and compare multiple equations between two images.

    Returns dict with:
      - eqs1: list of detected equations from img1
      - eqs2: list of detected equations from img2
      - count1, count2: number of equations detected
      - pairings: list of (eq1_idx, eq2_idx, same) — matched by position
      - unpaired1: equations in img1 with no match in img2
      - unpaired2: equations in img2 with no match in img1
      - same: bool — True if all pairings match and no unpaired
      - verdict: 'identical' | 'count_mismatch' | 'content_diff' | 'one_missing'
    """
    eqs1 = detect_equations_multi(img1, timeout=timeout)
    eqs2 = detect_equations_multi(img2, timeout=timeout)

    count1 = len(eqs1)
    count2 = len(eqs2)

    if count1 == 0 and count2 == 0:
        return {
            'eqs1': [], 'eqs2': [], 'count1': 0, 'count2': 0,
            'pairings': [], 'unpaired1': [], 'unpaired2': [],
            'same': True, 'verdict': 'identical',
            'count_same': True, 'latex_list1': [], 'latex_list2': [],
        }

    if count1 == 0 or count2 == 0:
        return {
            'eqs1': eqs1, 'eqs2': eqs2,
            'count1': count1, 'count2': count2,
            'pairings': [], 'unpaired1': eqs1, 'unpaired2': eqs2,
            'same': False,
            'verdict': 'one_side_has_no_equations',
            'count_same': count1 == count2,
            'latex_list1': [e['latex'] for e in eqs1],
            'latex_list2': [e['latex'] for e in eqs2],
        }

    # Match equations by position: greedy nearest-match by centroid distance
    pairings = []
    used1 = set()
    used2 = set()

    # Sort by position for consistent matching
    sorted1 = sorted(enumerate(eqs1), key=lambda x: (x[1]['cy'], x[1]['cx']))
    sorted2 = sorted(enumerate(eqs2), key=lambda x: (x[1]['cy'], x[1]['cx']))

    # Greedy matching: pair each eq1 to nearest unmatched eq2 within row tolerance
    row_tolerance = max(img1.height, img2.height) * 0.15  # 15% row tolerance

    for i1, e1 in sorted1:
        best_j = None
        best_dist = float('inf')
        for i2, e2 in sorted2:
            if i2 in used2:
                continue
            row_dist = abs(e1['cy'] - e2['cy'])
            if row_dist > row_tolerance:
                continue
            dist = abs(e1['cx'] - e2['cx']) + row_dist * 3  # weighted distance
            if dist < best_dist:
                best_dist = dist
                best_j = i2
        if best_j is not None:
            used1.add(i1)
            used2.add(best_j)
            same = eqs1[i1]['latex'].strip() == eqs2[best_j]['latex'].strip()
            pairings.append((i1, best_j, same))

    unpaired1 = [eqs1[i] for i in range(count1) if i not in used1]
    unpaired2 = [eqs2[i] for i in range(count2) if i not in used2]

    all_same = (
        len(unpaired1) == 0 and
        len(unpaired2) == 0 and
        all(p[2] for p in pairings)
    )

    verdict = 'identical' if all_same else (
        'count_mismatch' if (count1 != count2 and len(pairings) == 0) else 'content_diff'
    )

    return {
        'eqs1': eqs1, 'eqs2': eqs2,
        'count1': count1, 'count2': count2,
        'pairings': pairings,
        'unpaired1': unpaired1, 'unpaired2': unpaired2,
        'same': all_same,
        'verdict': verdict,
        'count_same': count1 == count2,
        'latex_list1': [e['latex'] for e in eqs1],
        'latex_list2': [e['latex'] for e in eqs2],
    }


# ── Single-image convenience wrapper ─────────────────────────────────────────

def extract_equation(img: Image.Image) -> Optional[str]:
    """Legacy: extract first equation found (or None). For backward compat."""
    results = detect_equations_multi(img)
    return results[0]['latex'] if results else None
