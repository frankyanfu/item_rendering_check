"""Debug table and chart detection on test images."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from item_rendering_check.table import detect_tables_multi, _grid_bboxes_from_lines
from item_rendering_check.comparator import _find_all_chart_regions
from PIL import Image

BASE = os.path.join(os.path.dirname(__file__), 'test_images')

for name in ['text_eq_table_before.png', 'full_before.png']:
    print(f"\n=== {name} ===")
    img = Image.open(os.path.join(BASE, name))

    # Tables
    grids = _grid_bboxes_from_lines(img)
    print(f"  Raw grids: {len(grids)}")
    for i, g in enumerate(grids):
        print(f"    Grid {i}: bbox={g['bbox']} rows={g['num_rows']} cols={g['num_cols']}")
        h_lens = [abs(l[2]-l[0]) for l in g['horizontal_lines']]
        v_lens = [abs(l[3]-l[1]) for l in g['vertical_lines']]
        print(f"      h_lines({len(g['horizontal_lines'])}): lengths={sorted(h_lens, reverse=True)}")
        print(f"      v_lines({len(g['vertical_lines'])}): lengths={sorted(v_lens, reverse=True)}")

    tables = detect_tables_multi(img)
    print(f"  Tables after dedup: {len(tables)}")
    for i, t in enumerate(tables):
        print(f"    Table {i}: bbox={t['bbox']} rows={t['num_rows']} cols={t['num_cols']}")
        for ri, row in enumerate(t['cells']):
            print(f"      Row {ri}: {row}")

    # Charts
    charts = _find_all_chart_regions(img)
    print(f"  Charts: {len(charts)}")
    for i, c in enumerate(charts):
        print(f"    Chart {i}: x={c['x']} y={c['y']} w={c['width']} h={c['height']} type={c.get('chart_type')}")
