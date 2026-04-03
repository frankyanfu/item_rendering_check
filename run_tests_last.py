"""Check last two test pairs."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from item_rendering_check.comparator import compare

BASE = os.path.join(os.path.dirname(__file__), 'test_images')

tests = [
    ('full_before.png', 'full_identical.png', 'identical'),
    ('identical_a.png', 'identical_b.png', 'identical'),
]

for p1, p2, expect in tests:
    r = compare(os.path.join(BASE, p1), os.path.join(BASE, p2))
    ok = 'OK' if r['same'] else 'FAIL'
    v = r['verdict']
    print(f"{ok} | {p1} vs {p2} | verdict={v}")
    for f in r['findings']:
        print(f"     {f}")
    eq = r.get('equation_result')
    if eq and eq.get('latex_list1'):
        print(f"     eq1: {eq['latex_list1']}")
        print(f"     eq2: {eq['latex_list2']}")
