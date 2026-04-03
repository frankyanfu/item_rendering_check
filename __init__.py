"""
Screenshot Diff Tool
Compare screenshots by visual diff, text, equations (multiple), tables (multiple), and graphs.
Fully local — no LLM API required.
"""

__version__ = "0.7.0"

from .comparator import compare
from .text_diff import compare_text, extract_text
from .equation import extract_equation, detect_equations_multi, compare_equations_multi
from .table import compare_tables, detect_tables_multi, compare_tables_multi
from .visual_diff import visual_diff, compute_ssim, quick_similarity
from .region_detector import find_changed_regions, annotate_image
