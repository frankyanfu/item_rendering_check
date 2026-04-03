"""
Screenshot Diff CLI — compare screenshots by text, equations, tables, and graphs.
Each layer supports multiple items per image and detects asymmetry
(one has X items, other has Y).

Fully local — no LLM API required.
"""

import click, csv
from pathlib import Path
from screenshot_diff.comparator import compare
from screenshot_diff.text_diff import extract_text
from screenshot_diff.equation import detect_equations_multi


@click.group()
def cli():
    """Screenshot diff — compare screenshots by text, equations, tables, and graphs."""
    pass


@cli.command()
@click.argument('path1', type=click.Path(exists=True))
@click.argument('path2', type=click.Path(exists=True))
@click.option('--ocr-lang', default=None, type=str)
@click.option('--no-tables', is_flag=True, help='Skip table detection')
@click.option('--no-graphs', is_flag=True, help='Skip chart/graph detection')
@click.option('--json', 'as_json', is_flag=True, help='Output results as JSON')
def compare_cmd(path1, path2, ocr_lang, no_tables, no_graphs, as_json):
    """Compare two screenshots across all content layers."""
    result = compare(
        path1, path2,
        ocr_lang=ocr_lang,
        detect_equations=True,
        detect_tables=not no_tables,
        detect_graphs=not no_graphs,
    )

    if as_json:
        import json
        def _safe(v):
            if hasattr(v, 'item'):
                return v.item()
            return v
        def _to_serializable(obj):
            if isinstance(obj, (str, int, float, bool, type(None))):
                return obj
            if isinstance(obj, (list, tuple)):
                return [_safe(x) for x in obj]
            if isinstance(obj, dict):
                return {k: _safe(v) for k, v in obj.items()}
            return str(obj)
        click.echo(json.dumps({k: _to_serializable(v) for k, v in result.items()}, indent=2, default=str))
        return

    verdict_colors = {
        'identical': 'green', 'text_diff': 'yellow', 'equation_diff': 'yellow',
        'table_diff': 'yellow', 'graph_diff': 'yellow', 'multiple_diff': 'red'
    }
    color = verdict_colors.get(result['verdict'], 'white')
    icon = '✓' if result['same'] else '✗'

    tr = result.get('text_result') or {}
    eq = result.get('equation_result')
    tbl = result.get('table_result')
    gr = result.get('graph_result')

    click.echo(f"\n{'='*60}")
    click.echo(f"  SCREENSHOT DIFF")
    click.echo(f"{'='*60}")
    click.echo(f"  Image 1: {path1}  ({result['img1_size'][0]}x{result['img1_size'][1]})")
    click.echo(f"  Image 2: {path2}  ({result['img2_size'][0]}x{result['img2_size'][1]})")
    click.echo(f"{'-'*60}")
    click.secho(f"  {icon} Verdict: {result['verdict'].upper()}", fg=color, bold=True)
    click.echo(f"  {result['summary']}")
    click.echo()

    # ── Text ───────────────────────────────────────────────────────────────
    click.echo(f"  --- Text (OCR) ---")
    text_sim = tr.get('similarity', 0)
    click.echo(f"  Similarity: {text_sim:.1%}")
    if tr.get('has_text_changes'):
        click.secho(f"  ✗ {tr['diff']['num_added']} line(s) added, {tr['diff']['num_removed']} removed", fg='yellow')
    else:
        click.secho(f"  ✓ Identical", fg='green')

    # ── Equations ───────────────────────────────────────────────────────────
    if eq:
        click.echo(f"\n  --- Equations (LaTeX via pix2tex) ---")
        click.echo(f"  Count: img1={eq['count1']}, img2={eq['count2']}")
        if eq['count1'] == 0 and eq['count2'] == 0:
            click.secho(f"  ✓ No equations in either image", fg='green')
        elif eq['verdict'] == 'one_side_has_no_equations':
            side = 'img1' if eq['count1'] > 0 else 'img2'
            click.secho(f"  ✗ {side} has equation(s), other doesn't", fg='yellow')
            for i, latex in enumerate(eq.get('latex_list1', []) or eq.get('latex_list2', [])):
                click.echo(f"    [{i}] {latex[:80]}")
        elif eq['verdict'] == 'count_mismatch':
            click.secho(f"  ✗ Count differs: {eq['count1']} vs {eq['count2']}", fg='yellow')
            for e in eq.get('unpaired1', []):
                click.echo(f"    Extra in img1: {e.get('latex', '')[:80]}")
            for e in eq.get('unpaired2', []):
                click.echo(f"    Extra in img2: {e.get('latex', '')[:80]}")
        elif eq['verdict'] == 'content_diff':
            n_same = sum(1 for p in eq.get('pairings', []) if (p[3] if len(p) > 3 else False))
            n_diff = sum(1 for p in eq.get('pairings', []) if not (p[3] if len(p) > 3 else True))
            n_diff = len(eq.get('pairings', [])) - n_same
            click.secho(f"  ✗ {n_diff} differ, {n_same} identical", fg='yellow')
            for idx, p in enumerate(eq.get('pairings', [])):
                if len(p) < 4 or not (p[3] if len(p) > 3 else True):  # same is p[3]
                    same = p[2] if len(p) > 2 else False
                    if not same:
                        l1 = eq['latex_list1'][p[0]] if p[0] < len(eq.get('latex_list1', [])) else ''
                        l2 = eq['latex_list2'][p[1]] if p[1] < len(eq.get('latex_list2', [])) else ''
                        click.echo(f"    Eq {idx}: '{l1[:50]}' ≠ '{l2[:50]}'")
            if eq.get('unpaired1'):
                click.echo(f"    Unpaired in img1: {len(eq['unpaired1'])}")
            if eq.get('unpaired2'):
                click.echo(f"    Unpaired in img2: {len(eq['unpaired2'])}")
        else:
            click.secho(f"  ✓ All equations identical", fg='green')
    else:
        click.echo(f"\n  --- Equations ---  (detection disabled)")

    # ── Tables ─────────────────────────────────────────────────────────────
    if tbl:
        click.echo(f"\n  --- Tables (OpenCV grid + OCR) ---")
        click.echo(f"  Count: img1={tbl['count1']}, img2={tbl['count2']}")
        if tbl['count1'] == 0 and tbl['count2'] == 0:
            click.secho(f"  ✓ No tables detected in either image", fg='green')
        elif tbl['verdict'] == 'one_side_has_no_tables':
            side = 'img1' if tbl['count1'] > 0 else 'img2'
            click.secho(f"  ✗ {side} has table(s), other doesn't", fg='yellow')
        elif tbl['verdict'] == 'count_mismatch':
            total_diffs = sum(p[3] for p in tbl.get('pairings', []) if len(p) > 3)
            click.secho(f"  ✗ Count differs: {tbl['count1']} vs {tbl['count2']}, "
                        f"{total_diffs} cell(s) different", fg='yellow')
        elif tbl['verdict'] == 'content_diff':
            n_same = sum(1 for p in tbl.get('pairings', []) if len(p) > 2 and p[2])
            n_diff = sum(1 for p in tbl.get('pairings', []) if len(p) > 2 and not p[2])
            n_unpaired = len(tbl.get('unpaired1', [])) + len(tbl.get('unpaired2', []))
            total_cells = sum(p[3] for p in tbl.get('pairings', []) if len(p) > 3)
            if n_diff > 0:
                click.secho(f"  ✗ {n_diff} table(s) differ, {total_cells} cell(s) different", fg='yellow')
            else:
                click.secho(f"  ✗ {n_unpaired} unpaired table(s)", fg='yellow')
            for idx, p in enumerate(tbl.get('pairings', [])):
                if len(p) > 3 and not p[2]:
                    click.echo(f"    Table {idx+1}: {p[3]} cell(s) different")
        else:
            click.secho(f"  ✓ All tables identical", fg='green')
    else:
        click.echo(f"\n  --- Tables ---  (detection disabled)")

    # ── Graphs ─────────────────────────────────────────────────────────────
    if gr:
        click.echo(f"\n  --- Charts/Graphs (axis label OCR) ---")
        click.echo(f"  Count: img1={gr['count1']}, img2={gr['count2']}")
        if gr['count1'] == 0 and gr['count2'] == 0:
            click.secho(f"  ✓ No charts detected in either image", fg='green')
        elif gr['verdict'] == 'one_side_has_no_charts':
            side = 'img1' if gr['count1'] > 0 else 'img2'
            click.secho(f"  ✗ {side} has chart(s), other doesn't", fg='yellow')
        elif gr['verdict'] == 'count_mismatch':
            click.secho(f"  ✗ Count differs: {gr['count1']} vs {gr['count2']}", fg='yellow')
        elif gr['verdict'] == 'content_diff':
            n_same = sum(1 for p in gr.get('pairings', []) if len(p) > 2 and p[2])
            n_diff = sum(1 for p in gr.get('pairings', []) if len(p) > 2 and not p[2])
            n_unpaired = len(gr.get('unpaired1', [])) + len(gr.get('unpaired2', []))
            click.secho(f"  ✗ {n_diff} differ, {n_same} identical" +
                        (f", {n_unpaired} unpaired" if n_unpaired else ""), fg='yellow')
        else:
            click.secho(f"  ✓ All charts identical", fg='green')
    else:
        click.echo(f"\n  --- Charts/Graphs ---  (detection disabled)")

    click.echo(f"{'='*60}\n")


@cli.command()
@click.argument('input_csv', type=click.Path(exists=True))
@click.option('--output-csv', '-o', type=click.Path())
@click.option('--ocr-lang', default=None, type=str)
@click.option('--no-tables', is_flag=True)
@click.option('--no-graphs', is_flag=True)
def batch(input_csv, output_csv, ocr_lang, no_tables, no_graphs):
    """Batch compare image pairs from CSV. Output: verdict + 3 similarity columns."""
    input_path = Path(input_csv)
    output_path = Path(output_csv) if output_csv else input_path.parent / f"{input_path.stem}_results.csv"

    with open(input_csv, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    col_before, col_after = _detect_columns(fieldnames)
    if not col_before or not col_after:
        click.secho(f"✗ Could not detect before/after columns. Found: {fieldnames}", fg='red')
        raise click.Abort()

    click.echo(f"Processing {len(rows)} image pair(s)...")
    results = []

    for i, row in enumerate(rows):
        bp = row[col_before].strip()
        ap = row[col_after].strip()
        if not Path(bp).exists():
            click.secho(f"  [{i+1}/{len(rows)}] ✗ Not found: {bp}", fg='red')
            results.append(_error_row(bp, ap, f"File not found: {bp}"))
            continue
        if not Path(ap).exists():
            click.secho(f"  [{i+1}/{len(rows)}] ✗ Not found: {ap}", fg='red')
            results.append(_error_row(bp, ap, f"File not found: {ap}"))
            continue

        try:
            r = compare(bp, ap, ocr_lang=ocr_lang,
                        detect_equations=True,
                        detect_tables=not no_tables,
                        detect_graphs=not no_graphs)

            tr = r.get('text_result') or {}
            eq = r.get('equation_result')
            tbl = r.get('table_result')
            gr = r.get('graph_result')

            # Text similarity
            text_sim = tr.get('similarity', '')

            # Table similarity
            tbl_sim = _table_similarity(tbl)

            # Graph similarity
            gr_sim = _graph_similarity(gr)

            verdict_icon = '✓' if r['same'] else '✗'
            color = 'green' if r['same'] else 'yellow'
            ts = f'{text_sim:.0%}' if isinstance(text_sim, float) else str(text_sim or 'N/A')
            t_str = f'{tbl_sim:.0%}' if isinstance(tbl_sim, float) else str(tbl_sim or 'N/A')
            g_str = f'{gr_sim:.0%}' if isinstance(gr_sim, float) else str(gr_sim or 'N/A')
            eq_str = "eq:{}/{}".format(eq.get("count1",0), eq.get("count2",0)) if eq else ""

            click.secho(
                f"  [{i+1}/{len(rows)}] {verdict_icon} {Path(bp).name} → {r['verdict']}  "
                f"(text={ts}, table={t_str}, graph={g_str}{', '+eq_str if eq_str else ''})",
                fg=color
            )

            results.append({
                'before_path': bp, 'after_path': ap,
                'verdict': r['verdict'], 'same': r['same'],
                'text_similarity': text_sim,
                'table_similarity': tbl_sim,
                'graph_similarity': gr_sim,
                'eq_count': '{}/{}'.format(eq.get('count1',0), eq.get('count2',0)) if eq else '0/0',
                'table_count': '{}/{}'.format(tbl.get('count1',0), tbl.get('count2',0)) if tbl else '0/0',
                'graph_count': '{}/{}'.format(gr.get('count1',0), gr.get('count2',0)) if gr else '0/0',
                'summary': r['summary'],
            })
        except Exception as e:
            click.secho(f"  [{i+1}/{len(rows)}] ✗ Error: {e}", fg='red')
            results.append(_error_row(bp, ap, str(e)))

    fieldnames_out = [
        'before_path', 'after_path', 'verdict', 'same',
        'text_similarity', 'table_similarity', 'graph_similarity',
        'eq_count', 'table_count', 'graph_count', 'summary'
    ]
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames_out)
        writer.writeheader()
        writer.writerows(results)

    same_count = sum(1 for r in results if r.get('same') is True)
    click.echo(f"\n✓ Complete. {same_count}/{len(results)} identical, {len(results)-same_count} different.")
    click.echo(f"  Results → {output_path}")


@cli.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--ocr-lang', default=None, type=str)
def extract(path, ocr_lang):
    """Extract all content from a single screenshot."""
    from PIL import Image
    import pytesseract
    img = Image.open(path)

    click.echo(f"\n{'='*50}\n  CONTENT EXTRACTION\n{'='*50}")

    click.echo(f"\n  --- Text (OCR) ---")
    text = extract_text(img, lang=ocr_lang)
    if text:
        for line in text.splitlines():
            click.echo(f"    {line}")
    else:
        click.secho("  (none)", fg='yellow')

    click.echo(f"\n  --- Equations ---")
    eqs = detect_equations_multi(img)
    if eqs:
        for i, eq in enumerate(eqs):
            click.echo(f"  [{i+1}] bbox={eq['bbox']}")
            click.echo(f"      LaTeX: {eq['latex']}")
    else:
        click.secho("  (none detected)", fg='yellow')

    click.echo(f"\n  --- Tables ---")
    try:
        from screenshot_diff.table import detect_tables_multi
        def ocr_fn(crop):
            return pytesseract.image_to_string(crop, lang=ocr_lang or 'eng', config='--psm 7').strip()
        tables = detect_tables_multi(img, ocr_func=ocr_fn)
        if tables:
            for i, t in enumerate(tables):
                click.echo(f"  [{i+1}] {t['num_rows']} rows × {t['num_cols']} cols, bbox={t['bbox']}")
                for row in t['cells'][:5]:
                    click.echo(f"    {' | '.join(row[:5])}")
                if t['num_rows'] > 5:
                    click.echo(f"    ... ({t['num_rows']-5} more rows)")
        else:
            click.secho("  (none detected)", fg='yellow')
    except Exception as e:
        click.secho(f"  (error: {e})", fg='yellow')

    click.echo(f"\n{'='*50}\n")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _detect_columns(fieldnames):
    col_before = col_after = None
    for col in fieldnames:
        cl = col.lower().strip()
        if col_before is None and cl in ('before', 'before_path', 'image1', 'path1'):
            col_before = col
        elif col_after is None and cl in ('after', 'after_path', 'image2', 'path2'):
            col_after = col
    return col_before, col_after


def _error_row(bp, ap, error_msg):
    return {
        'before_path': bp, 'after_path': ap,
        'verdict': 'ERROR', 'same': '',
        'text_similarity': '', 'table_similarity': '', 'graph_similarity': '',
        'eq_count': '', 'table_count': '', 'graph_count': '', 'summary': error_msg,
    }


def _table_similarity(tbl) -> str:
    """Compute table similarity string. Returns '' if no tables detected."""
    if not tbl:
        return ''
    if tbl['count1'] == 0 and tbl['count2'] == 0:
        return 1.0
    if tbl.get('same') is True:
        return 1.0
    if tbl['count1'] == 0 or tbl['count2'] == 0:
        return 0.0
    if tbl.get('pairings'):
        n_diff = sum(1 for p in tbl.get('pairings', []) if len(p) > 2 and not p[2])
        return round(1 - n_diff / max(len(tbl['pairings']), 1), 3)
    return 0.0


def _graph_similarity(gr) -> str:
    """Compute graph similarity string. Returns '' if no graphs detected."""
    if not gr:
        return ''
    if gr['count1'] == 0 and gr['count2'] == 0:
        return 1.0
    if gr.get('same') is True:
        return 1.0
    if gr['count1'] == 0 or gr['count2'] == 0:
        return 0.0
    if gr.get('pairings'):
        n_diff = sum(1 for p in gr.get('pairings', []) if len(p) > 2 and not p[2])
        return round(1 - n_diff / max(len(gr['pairings']), 1), 3)
    return 0.0


if __name__ == '__main__':
    cli()
