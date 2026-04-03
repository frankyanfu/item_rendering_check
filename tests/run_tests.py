"""
Run the screenshot diff tool against all generated test pairs.
Reports pass/fail for each scenario.
"""

import sys, os, traceback

# Add the parent of the package directory so we can import the package
pkg_dir = os.path.dirname(os.path.dirname(__file__))
parent_dir = os.path.dirname(pkg_dir)
sys.path.insert(0, parent_dir)

from item_rendering_check.comparator import compare

IMG = os.path.join(os.path.dirname(__file__), "test_images")


def p(name):
    return os.path.join(IMG, name)


TESTS = [
    # (label, before, after, expected_same, skip_eq, desc)
    ("S1-identical", "s1_text_before.png", "s1_text_after_same.png", True,
     "Text-only identical pair"),
    ("S1-different", "s1_text_before.png", "s1_text_after_diff.png", False,
     "Text-only with word changes"),
    ("S2-identical", "s2_eq_before.png", "s2_eq_after_same.png", True,
     "Text+equation identical pair"),
    ("S2-different", "s2_eq_before.png", "s2_eq_after_diff.png", False,
     "Text+equation with equation change"),
    ("S3-identical", "s3_table_before.png", "s3_table_after_same.png", True,
     "Text+eq+table identical pair"),
    ("S3-different", "s3_table_before.png", "s3_table_after_diff.png", False,
     "Text+eq+table with cell changes"),
    ("S4-identical", "s4_full_before.png", "s4_full_after_same.png", True,
     "Full scenario identical pair"),
    ("S4-different", "s4_full_before.png", "s4_full_after_diff.png", False,
     "Full scenario with table+chart changes"),
]


def run_all():
    print(f"{'='*70}")
    print(f"  SCREENSHOT DIFF — Integration Test Suite")
    print(f"{'='*70}\n")

    passed = 0
    failed = 0
    errors = 0
    details = []

    for label, before, after, expected_same, desc in TESTS:
        print(f"  [{label}] {desc}")
        print(f"    {before} vs {after}")
        try:
            result = compare(
                p(before), p(after),
                detect_equations=False,  # skip pix2tex for speed
                detect_tables=True,
                detect_graphs=True,
                detect_visual=True,
            )

            actual_same = result['same']
            verdict = result['verdict']
            vis = result.get('visual_result')
            ssim = vis.get('ssim_score', 'N/A') if vis else 'N/A'
            n_regions = vis.get('num_changed_regions', 0) if vis else 0
            text_sim = result['text_result'].get('similarity', 'N/A')

            ok = actual_same == expected_same
            icon = "PASS" if ok else "FAIL"
            color_code = "\033[92m" if ok else "\033[91m"
            reset = "\033[0m"

            print(f"    {color_code}{icon}{reset}  verdict={verdict}, same={actual_same} "
                  f"(expected={expected_same})")
            print(f"         SSIM={ssim:.4f}, regions={n_regions}, text_sim={text_sim:.3f}")

            if result.get('findings'):
                for f in result['findings']:
                    print(f"         → {f}")

            if ok:
                passed += 1
            else:
                failed += 1
                details.append((label, desc, expected_same, actual_same, verdict, result))

        except Exception as e:
            errors += 1
            print(f"    \033[91mERROR\033[0m  {type(e).__name__}: {e}")
            traceback.print_exc()
            details.append((label, desc, expected_same, None, "ERROR", str(e)))

        print()

    print(f"{'='*70}")
    print(f"  Results: {passed} passed, {failed} failed, {errors} errors")
    print(f"{'='*70}")

    if details:
        print(f"\n  FAILURES:")
        for label, desc, expected, actual, verdict, info in details:
            print(f"    [{label}] expected same={expected}, got same={actual}, verdict={verdict}")
            if isinstance(info, dict):
                # Print text diff details for debugging
                tr = info.get('text_result', {})
                if tr.get('has_text_changes'):
                    print(f"      Text added: {tr['diff']['num_added']}, removed: {tr['diff']['num_removed']}")
                    for op, line in tr['diff'].get('unified', [])[:10]:
                        if op in ('add', 'remove'):
                            print(f"        {'+' if op == 'add' else '-'} {line.rstrip()[:80]}")
                vis = info.get('visual_result')
                if vis:
                    print(f"      Visual: SSIM={vis.get('ssim_score', 'N/A')}, "
                          f"regions={vis.get('num_changed_regions', 0)}")

    return 1 if (failed + errors) > 0 else 0


if __name__ == "__main__":
    sys.exit(run_all())
