"""
Generate synthetic screenshot pairs for testing the Screenshot Diff Tool.
Creates before/after image pairs with deliberate differences for each scenario.
"""

import os
from PIL import Image, ImageDraw, ImageFont

OUT_DIR = os.path.join(os.path.dirname(__file__), "test_images")

# Try to get a decent font, fall back to default
def get_font(size=16):
    for name in ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"]:
        try:
            return ImageFont.truetype(name, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()

FONT = get_font(18)
FONT_SM = get_font(14)
FONT_LG = get_font(24)
FONT_TITLE = get_font(28)


def new_canvas(w=800, h=600, bg="white"):
    img = Image.new("RGB", (w, h), bg)
    return img, ImageDraw.Draw(img)


def draw_text_block(draw, x, y, lines, font=None):
    font = font or FONT
    for line in lines:
        draw.text((x, y), line, fill="black", font=font)
        y += font.size + 6
    return y


def draw_equation_block(draw, x, y, latex_text, font=None):
    """Draw a box that looks like an equation region with LaTeX-ish text."""
    font = font or FONT_LG
    bbox = draw.textbbox((x, y), latex_text, font=font)
    pad = 8
    draw.rectangle([bbox[0]-pad, bbox[1]-pad, bbox[2]+pad, bbox[3]+pad],
                    outline="gray", width=1)
    draw.text((x, y), latex_text, fill="black", font=font)
    return bbox[3] + pad + 10


def draw_table(draw, x, y, rows, col_widths, row_height=30, font=None):
    """Draw a table grid with text in cells."""
    font = font or FONT_SM
    total_w = sum(col_widths)
    n_rows = len(rows)
    # Draw grid
    for r in range(n_rows + 1):
        draw.line([(x, y + r * row_height), (x + total_w, y + r * row_height)],
                  fill="black", width=2)
    cx = x
    for cw in col_widths:
        for r in range(n_rows + 1):
            pass  # vertical line at each column boundary
        draw.line([(cx, y), (cx, y + n_rows * row_height)], fill="black", width=2)
        cx += cw
    draw.line([(cx, y), (cx, y + n_rows * row_height)], fill="black", width=2)

    # Fill cells
    for ri, row in enumerate(rows):
        cx = x
        for ci, cell in enumerate(row):
            cw = col_widths[ci] if ci < len(col_widths) else col_widths[-1]
            draw.text((cx + 5, y + ri * row_height + 5), str(cell), fill="black", font=font)
            cx += cw

    return y + n_rows * row_height + 15


def draw_bar_chart(draw, x, y, values, labels, bar_width=40, max_height=120, chart_label="Chart"):
    """Draw a simple bar chart."""
    font = FONT_SM
    max_val = max(values) if values else 1
    spacing = 15
    chart_w = len(values) * (bar_width + spacing) + spacing
    # Chart outline
    draw.rectangle([x, y, x + chart_w, y + max_height + 40], outline="black", width=2)
    # Title
    draw.text((x + 5, y + 2), chart_label, fill="black", font=font)
    # Bars
    for i, (val, label) in enumerate(zip(values, labels)):
        bx = x + spacing + i * (bar_width + spacing)
        bar_h = int((val / max_val) * (max_height - 20))
        by = y + max_height + 20 - bar_h
        colors = ["#4472C4", "#ED7D31", "#A5A5A5", "#FFC000", "#5B9BD5"]
        draw.rectangle([bx, by, bx + bar_width, y + max_height + 20],
                        fill=colors[i % len(colors)], outline="black")
        draw.text((bx, y + max_height + 22), label, fill="black", font=FONT_SM)
    return y + max_height + 55


# ─── Scenario 1: Text Only ─────────────────────────────────────────────────


def gen_text_only():
    lines_before = [
        "Reading Comprehension - Passage 1",
        "",
        "The mitochondria is the powerhouse of the cell.",
        "It produces ATP through cellular respiration.",
        "This process involves the electron transport chain.",
        "",
        "Question 1: What is the primary function of mitochondria?",
        "(A) Protein synthesis",
        "(B) ATP production",
        "(C) DNA replication",
        "(D) Cell division",
    ]
    lines_after = [
        "Reading Comprehension - Passage 1",
        "",
        "The mitochondria is the powerhouse of the cell.",
        "It produces ATP through cellular respiration.",
        "This process involves the electron transport chain.",
        "",
        "Question 1: What is the primary function of mitochondria?",
        "(A) Protein synthesis",
        "(B) Energy production",     # Changed from "ATP production"
        "(C) DNA replication",
        "(D) Cell division",
    ]
    lines_identical = list(lines_before)

    for suffix, lines in [("before", lines_before), ("after", lines_after), ("identical", lines_identical)]:
        img, draw = new_canvas()
        draw_text_block(draw, 40, 40, lines)
        img.save(os.path.join(OUT_DIR, f"text_only_{suffix}.png"))


# ─── Scenario 2: Text + Equation ──────────────────────────────────────────


def gen_text_equation():
    text_lines = [
        "Mathematics - Problem Set 3",
        "",
        "Solve the following quadratic equation:",
    ]

    for suffix, eq_text in [
        ("before", "x = (-b ± √(b²-4ac)) / 2a"),
        ("after",  "x = (-b ± √(b²-4ac)) / (2a)"),   # subtle parentheses change
        ("identical", "x = (-b ± √(b²-4ac)) / 2a"),
    ]:
        img, draw = new_canvas()
        y = draw_text_block(draw, 40, 40, text_lines)
        y = draw_equation_block(draw, 60, y + 10, eq_text)
        draw_text_block(draw, 40, y + 10, ["where a=1, b=-5, c=6"])
        img.save(os.path.join(OUT_DIR, f"text_eq_{suffix}.png"))


# ─── Scenario 3: Text + Equation + Table ──────────────────────────────────


def gen_text_eq_table():
    text_lines = [
        "Data Analysis Section",
        "",
        "Given the formula: ",
    ]
    eq = "F = m × a"
    table_header = ["Object", "Mass (kg)", "Accel (m/s²)", "Force (N)"]
    table_before = [
        table_header,
        ["Ball", "0.5", "9.8", "4.9"],
        ["Car", "1000", "2.0", "2000"],
        ["Truck", "5000", "1.5", "7500"],
    ]
    table_after = [
        table_header,
        ["Ball", "0.5", "9.8", "4.9"],
        ["Car", "1000", "2.0", "2000"],
        ["Truck", "5000", "1.5", "7499"],   # 7500 -> 7499
    ]

    for suffix, tbl in [("before", table_before), ("after", table_after), ("identical", table_before)]:
        img, draw = new_canvas(w=800, h=500)
        y = draw_text_block(draw, 40, 30, text_lines)
        y = draw_equation_block(draw, 60, y + 5, eq)
        draw_text_block(draw, 40, y, ["Calculate the force for each object:"])
        y += 30
        draw_table(draw, 40, y, tbl, col_widths=[100, 100, 120, 100])
        img.save(os.path.join(OUT_DIR, f"text_eq_table_{suffix}.png"))


# ─── Scenario 4: Text + Equation + Table + Graph ──────────────────────────


def gen_full():
    text_lines = [
        "Quarterly Performance Summary",
        "",
        "Total revenue (in millions):",
    ]
    eq = "Revenue = Price × Quantity"

    table_header = ["Quarter", "Revenue", "Costs", "Profit"]
    table_before = [
        table_header,
        ["Q1", "$2.1M", "$1.5M", "$0.6M"],
        ["Q2", "$2.4M", "$1.6M", "$0.8M"],
        ["Q3", "$2.8M", "$1.7M", "$1.1M"],
        ["Q4", "$3.1M", "$1.8M", "$1.3M"],
    ]
    table_after = [
        table_header,
        ["Q1", "$2.1M", "$1.5M", "$0.6M"],
        ["Q2", "$2.4M", "$1.6M", "$0.8M"],
        ["Q3", "$2.8M", "$1.7M", "$1.1M"],
        ["Q4", "$3.2M", "$1.8M", "$1.4M"],   # revenue & profit changed
    ]

    chart_vals_before = [2.1, 2.4, 2.8, 3.1]
    chart_vals_after  = [2.1, 2.4, 2.8, 3.2]
    chart_labels = ["Q1", "Q2", "Q3", "Q4"]

    for suffix, tbl, vals in [
        ("before", table_before, chart_vals_before),
        ("after", table_after, chart_vals_after),
        ("identical", table_before, chart_vals_before),
    ]:
        img, draw = new_canvas(w=800, h=700)
        y = draw_text_block(draw, 40, 25, text_lines)
        y = draw_equation_block(draw, 60, y + 5, eq)
        y = draw_table(draw, 40, y + 5, tbl, col_widths=[90, 90, 90, 90])
        draw_bar_chart(draw, 40, y + 10, vals, chart_labels, chart_label="Revenue by Quarter")
        img.save(os.path.join(OUT_DIR, f"full_{suffix}.png"))


# ─── Scenario 5: Identical pair (no changes) ──────────────────────────────


def gen_no_changes():
    """A complex image pair that should be 100% identical."""
    text_lines = [
        "Science Assessment — Section 2",
        "",
        "The speed of light in a vacuum is approximately",
    ]
    eq = "c = 3.0 × 10⁸ m/s"

    for suffix in ("a", "b"):
        img, draw = new_canvas()
        y = draw_text_block(draw, 40, 40, text_lines)
        y = draw_equation_block(draw, 60, y + 10, eq)
        draw_text_block(draw, 40, y + 10, [
            "This constant is fundamental to Einstein's",
            "theory of special relativity: E = mc²",
        ])
        img.save(os.path.join(OUT_DIR, f"identical_{suffix}.png"))


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"Generating test images in {OUT_DIR} ...")

    gen_text_only()
    print("  ✓ text_only (before / after / identical)")

    gen_text_equation()
    print("  ✓ text_eq (before / after / identical)")

    gen_text_eq_table()
    print("  ✓ text_eq_table (before / after / identical)")

    gen_full()
    print("  ✓ full (before / after / identical)")

    gen_no_changes()
    print("  ✓ identical pair (a / b)")

    # Create a batch CSV
    csv_path = os.path.join(OUT_DIR, "batch_test.csv")
    with open(csv_path, "w", newline="") as f:
        f.write("path1,path2,label\n")
        pairs = [
            ("text_only_before.png", "text_only_after.png", "text_diff"),
            ("text_only_before.png", "text_only_identical.png", "identical"),
            ("text_eq_before.png", "text_eq_after.png", "eq_diff"),
            ("text_eq_before.png", "text_eq_identical.png", "identical"),
            ("text_eq_table_before.png", "text_eq_table_after.png", "table_diff"),
            ("text_eq_table_before.png", "text_eq_table_identical.png", "identical"),
            ("full_before.png", "full_after.png", "multi_diff"),
            ("full_before.png", "full_identical.png", "identical"),
            ("identical_a.png", "identical_b.png", "identical"),
        ]
        for p1, p2, label in pairs:
            f.write(f"{os.path.join(OUT_DIR, p1)},{os.path.join(OUT_DIR, p2)},{label}\n")
    print(f"  ✓ batch CSV: {csv_path}")
    print("Done!")


if __name__ == "__main__":
    main()
