"""Quick test runner for all test pairs."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from item_rendering_check.comparator import compare

BASE = os.path.join(os.path.dirname(__file__), 'test_images')

tests = [
    ('text_only_before.png', 'text_only_after.png', 'diff', 'expect text_diff'),
    ('text_only_before.png', 'text_only_identical.png', 'identical', 'expect identical'),
    ('text_eq_before.png', 'text_eq_after.png', 'diff', 'expect eq+text_diff'),
    ('text_eq_before.png', 'text_eq_identical.png', 'identical', 'expect identical'),
    ('text_eq_table_before.png', 'text_eq_table_after.png', 'diff', 'expect table_diff'),
    ('text_eq_table_before.png', 'text_eq_table_identical.png', 'identical', 'expect identical'),
    ('full_before.png', 'full_after.png', 'diff', 'expect multi_diff'),
    ('full_before.png', 'full_identical.png', 'identical', 'expect identical'),
    ('identical_a.png', 'identical_b.png', 'identical', 'expect identical'),
]

for p1, p2, expect, desc in tests:
    r = compare(os.path.join(BASE, p1), os.path.join(BASE, p2))
    if expect == 'identical':
        ok = 'OK' if r['same'] else 'FAIL'
    else:
        ok = 'OK' if not r['same'] else 'FAIL'
    v = r['verdict']
    print(f"{ok} | {desc:25s} | {p1:35s} vs {p2:35s} | verdict={v}")
    for finding in r['findings']:
        print(f"     {finding}")
    # Show region detector info
    vis = r.get('visual_result')
    if vis:
        n = vis.get('num_changed_regions', 0)
        regions = vis.get('changed_regions', [])
        if regions:
            r0 = regions[0]
            print(f"     Visual regions: {n}, first: {r0['width']}x{r0['height']} area={r0['area']} intensity={r0['mean_intensity']}")
        else:
            print(f"     Visual regions: 0")
