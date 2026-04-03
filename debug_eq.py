"""Debug equation candidates in identical_a.png"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from item_rendering_check.equation import detect_equations_multi, _find_equation_candidates, SingleEquationExtractor
from PIL import Image

BASE = os.path.join(os.path.dirname(__file__), 'test_images')
img = Image.open(os.path.join(BASE, 'identical_a.png'))

cands = _find_equation_candidates(img)
print(f"Candidates: {len(cands)}")
extractor = SingleEquationExtractor()
for c in cands:
    bbox = c['bbox']
    area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
    latex = extractor.extract(c['crop'])
    is_valid = latex is not None
    cmd_count = latex.count('\\') if latex else 0
    would_reject = area < 2000 and cmd_count > 5
    print(f"  bbox={bbox} area={area} latex={latex!r} cmds={cmd_count} reject={would_reject}")
