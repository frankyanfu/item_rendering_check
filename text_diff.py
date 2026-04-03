"""
OCR-based text extraction and comparison.
Uses Tesseract (local) — no API required.
"""

import pytesseract
from PIL import Image
import difflib
from typing import Optional


def extract_text(img: Image.Image, lang: Optional[str] = None) -> str:
    """
    Extract text from an image using Tesseract OCR.

    Args:
        img: PIL Image
        lang: Optional tesseract language code, e.g. 'eng', 'chi_sim', 'jpn'
    Returns:
        Extracted text as string (may be empty if nothing detected)
    """
    config = ''
    if lang:
        config = f'-l {lang}'
    text = pytesseract.image_to_string(img, config=config)
    return text.strip()


def lines_diff(text1: str, text2: str) -> dict:
    """
    Compare two texts using difflib unified diff on lines.

    Returns dict with:
      - unified_diff: list of (op, line) tuples where op is '+', '-', ' ', '?'
      - added_lines: text lines present in text2 but not text1
      - removed_lines: text lines present in text1 but not text2
      - changed_lines: number of changed line groups
    """
    lines1 = text1.splitlines(keepends=True)
    lines2 = text2.splitlines(keepends=True)

    differ = difflib.unified_diff(lines1, lines2, lineterm='')
    diff_lines = list(differ)

    # Parse into structured format
    unified = []
    added = []
    removed = []
    for line in diff_lines:
        if line.startswith('+++') or line.startswith('---') or line.startswith('@@'):
            unified.append(('header', line))
        elif line.startswith('+'):
            unified.append(('add', line[1:]))
            added.append(line[1:])
        elif line.startswith('-'):
            unified.append(('remove', line[1:]))
            removed.append(line[1:])
        else:
            unified.append(('unchanged', line[1:]))

    return {
        'unified': unified,
        'added_lines': added,
        'removed_lines': removed,
        'num_added': len(added),
        'num_removed': len(removed),
    }


def text_similarity(text1: str, text2: str) -> float:
    """
    Compute a 0-1 similarity score between two texts using difflib SequenceMatcher.
    """
    return difflib.SequenceMatcher(None, text1, text2).ratio()


def compare_text(img1: Image.Image, img2: Image.Image, lang: Optional[str] = None) -> dict:
    """
    Full OCR-based text comparison pipeline.

    Returns dict with:
      - text1: extracted text from img1
      - text2: extracted text from img2
      - diff: structured diff result (see lines_diff)
      - similarity: 0-1 text similarity score
      - has_text_changes: bool (text differs between images)
    """
    text1 = extract_text(img1, lang=lang)
    text2 = extract_text(img2, lang=lang)
    diff = lines_diff(text1, text2)
    similarity = text_similarity(text1, text2)

    return {
        'text1': text1,
        'text2': text2,
        'diff': diff,
        'similarity': similarity,
        'has_text_changes': diff['num_added'] > 0 or diff['num_removed'] > 0,
    }