"""
Generate synthetic screenshot pairs for testing the screenshot-diff tool.
Creates before/after pairs for 4 scenarios:
  1. Text only
  2. Text + equation
  3. Text + equation + table
  4. Text + equation + table + graph

Each scenario has an "identical" pair and a "different" pair.
"""

import os
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(__file__), "test_images")
os.makedirs(OUT, exist_ok=True)

W, H = 800, 600
BG = (255, 255, 255)
FG = (0, 0, 0)
GRAY = (180, 180, 180)

try:
    FONT = ImageFont.truetype("arial.ttf", 20)
    FONT_SM = ImageFont.truetype("arial.ttf", 14)
    FONT_LG = ImageFont.truetype("arial.ttf", 28)
    FONT_ITAL = ImageFont.truetype("ariali.ttf", 22)
except OSError:
    FONT = ImageFont.load_default()
    FONT_SM = FONT
    FONT_LG = FONT
    FONT_ITAL = FONT


def new_img():
    img = Image.new("RGB", (W, H), BG)
    return img, ImageDraw.Draw(img)


# ── Helpers ──────────────────────────────────────────────────────────────────

def draw_text_block(draw, x, y, lines, font=None):
    """Draw multiple lines of text, return y after last line."""
    font = font or FONT
    for line in lines:
        draw.text((x, y), line, fill=FG, font=font)
        y += 28
    return y


def draw_equation_box(draw, x, y, eq_text, w=350, h=50):
    """Draw a bordered box with equation-like text inside."""
    draw.rectangle([x, y, x + w, y + h], outline=FG, width=2)
    # Slight gray background to look like a render box
    draw.rectangle([x + 2, y + 2, x + w - 2, y + h - 2], fill=(245, 245, 255))
    draw.text((x + 15, y + 12), eq_text, fill=FG, font=FONT_ITAL)
    return y + h + 10


def draw_table(draw, x, y, headers, rows, col_w=120, row_h=30):
    """Draw a simple table grid with text."""
    n_cols = len(headers)
    n_rows = len(rows) + 1  # +1 for header
    # Draw header
    for j, hdr in enumerate(headers):
        cx = x + j * col_w
        draw.rectangle([cx, y, cx + col_w, y + row_h], outline=FG, width=2)
        draw.rectangle([cx + 1, y + 1, cx + col_w - 1, y + row_h - 1], fill=(220, 220, 240))
        draw.text((cx + 8, y + 6), hdr, fill=FG, font=FONT_SM)
    y += row_h
    # Draw data rows
    for row in rows:
        for j, cell in enumerate(row):
            cx = x + j * col_w
            draw.rectangle([cx, y, cx + col_w, y + row_h], outline=FG, width=1)
            draw.text((cx + 8, y + 6), str(cell), fill=FG, font=FONT_SM)
        y += row_h
    return y + 10


def draw_bar_chart(draw, x, y, title, labels, values, w=300, h=200):
    """Draw a simple bar chart with axes."""
    # Title
    draw.text((x + w // 4, y), title, fill=FG, font=FONT_SM)
    y += 22
    chart_y = y
    chart_h = h - 40
    chart_w = w - 60
    ax_x = x + 50
    ax_y = y + chart_h

    # Y axis
    draw.line([(ax_x, y), (ax_x, ax_y)], fill=FG, width=2)
    # X axis
    draw.line([(ax_x, ax_y), (ax_x + chart_w, ax_y)], fill=FG, width=2)

    # Y-axis label
    draw.text((x + 2, y + chart_h // 2), "Value", fill=FG, font=FONT_SM)

    max_val = max(values) if values else 1
    bar_w = chart_w // (len(values) * 2) if values else 20
    for i, (label, val) in enumerate(zip(labels, values)):
        bx = ax_x + 10 + i * (bar_w * 2)
        bar_h = int((val / max_val) * (chart_h - 10))
        by = ax_y - bar_h
        color = [(70, 130, 180), (60, 179, 113), (255, 165, 0), (220, 20, 60)][i % 4]
        draw.rectangle([bx, by, bx + bar_w, ax_y], fill=color, outline=FG)
        draw.text((bx, ax_y + 4), label, fill=FG, font=FONT_SM)

    # X-axis label
    draw.text((ax_x + chart_w // 3, ax_y + 22), "Category", fill=FG, font=FONT_SM)
    return y + h


# ═══════════════════════════════════════════════════════════════════════════════
# Scenario 1: Text Only
# ═══════════════════════════════════════════════════════════════════════════════

TEXT_LINES = [
    "Question 12: Reading Comprehension",
    "",
    "The mitochondria are often referred to as the",
    "powerhouse of the cell. They generate most of",
    "the cell's supply of adenosine triphosphate (ATP),",
    "used as a source of chemical energy.",
    "",
    "Which of the following best describes the primary",
    "function of mitochondria?",
    "",
    "A) Protein synthesis",
    "B) Energy production",
    "C) Cell division",
    "D) Waste removal",
]

TEXT_LINES_DIFF = [
    "Question 12: Reading Comprehension",
    "",
    "The mitochondria are often referred to as the",
    "powerhouses of the cell. They generate most of",  # changed: powerhouse -> powerhouses
    "the cell's supply of adenosine triphosphate (ATP),",
    "used as a source of chemical energy.",
    "",
    "Which of the following best describes the primary",
    "role of mitochondria?",  # changed: function -> role
    "",
    "A) Protein synthesis",
    "B) Energy generation",  # changed: production -> generation
    "C) Cell division",
    "D) Waste removal",
]

def make_text_only(lines):
    img, draw = new_img()
    draw.text((30, 15), "NMAT Practice Test — Section 2", fill=GRAY, font=FONT_SM)
    draw.line([(30, 35), (W - 30, 35)], fill=GRAY, width=1)
    draw_text_block(draw, 40, 50, lines)
    return img


# ═══════════════════════════════════════════════════════════════════════════════
# Scenario 2: Text + Equation
# ═══════════════════════════════════════════════════════════════════════════════

EQ_TEXT_LINES = [
    "Question 7: Quantitative Reasoning",
    "",
    "Solve the following equation for x:",
]

EQ_TEXT_LINES2 = [
    "",
    "A) x = 3",
    "B) x = -2",
    "C) x = 5",
    "D) x = -3",
]

def make_text_eq(eq_str, answer_lines=None):
    img, draw = new_img()
    draw.text((30, 15), "NMAT Practice Test — Section 1", fill=GRAY, font=FONT_SM)
    draw.line([(30, 35), (W - 30, 35)], fill=GRAY, width=1)
    y = draw_text_block(draw, 40, 50, EQ_TEXT_LINES)
    y = draw_equation_box(draw, 60, y + 5, eq_str, w=400, h=55)
    lines2 = answer_lines or EQ_TEXT_LINES2
    draw_text_block(draw, 40, y + 5, lines2)
    return img


# ═══════════════════════════════════════════════════════════════════════════════
# Scenario 3: Text + Equation + Table
# ═══════════════════════════════════════════════════════════════════════════════

TBL_TEXT = [
    "Question 15: Data Interpretation",
    "",
    "The table below shows test scores for 4 students.",
    "Use the data to answer the following question.",
]

TBL_POST = [
    "",
    "What is the average score across all students?",
    "A) 82.5    B) 85.0    C) 87.5    D) 90.0",
]

def make_text_eq_table(eq_str, headers, rows, tbl_post=None):
    img, draw = new_img()
    draw.text((30, 15), "NMAT Practice Test — Section 3", fill=GRAY, font=FONT_SM)
    draw.line([(30, 35), (W - 30, 35)], fill=GRAY, width=1)
    y = draw_text_block(draw, 40, 50, TBL_TEXT)
    y = draw_equation_box(draw, 60, y + 5, eq_str, w=300, h=45)
    y = draw_table(draw, 60, y + 5, headers, rows)
    draw_text_block(draw, 40, y + 5, tbl_post or TBL_POST)
    return img


# ═══════════════════════════════════════════════════════════════════════════════
# Scenario 4: Text + Equation + Table + Graph
# ═══════════════════════════════════════════════════════════════════════════════

FULL_TEXT = [
    "Question 22: Integrated Reasoning",
    "",
    "Review the data below and answer.",
]

FULL_POST = [
    "Based on the chart and table data,",
    "which region shows the highest growth?",
    "A) North    B) South    C) East    D) West",
]

def make_full(eq_str, headers, rows, chart_title, chart_labels, chart_vals, post=None):
    img, draw = new_img()
    draw.text((30, 15), "NMAT Practice Test — Section 4", fill=GRAY, font=FONT_SM)
    draw.line([(30, 35), (W - 30, 35)], fill=GRAY, width=1)
    y = draw_text_block(draw, 40, 50, FULL_TEXT)
    y = draw_equation_box(draw, 60, y + 2, eq_str, w=280, h=42)
    # Table on the left, chart on the right
    tbl_y = y + 5
    draw_table(draw, 40, tbl_y, headers, rows, col_w=100, row_h=28)
    draw_bar_chart(draw, 440, tbl_y - 10, chart_title, chart_labels, chart_vals, w=320, h=200)
    draw_text_block(draw, 40, tbl_y + 160, post or FULL_POST)
    return img


# ═══════════════════════════════════════════════════════════════════════════════
# Generate all pairs
# ═══════════════════════════════════════════════════════════════════════════════

def save(img, name):
    path = os.path.join(OUT, name)
    img.save(path)
    print(f"  Saved: {path}")
    return path


def generate_all():
    print("Generating test screenshots...\n")
    pairs = []

    # ── Scenario 1: Text only ──────────────────────────────────────────────
    print("Scenario 1: Text Only")
    a = make_text_only(TEXT_LINES)
    b_same = make_text_only(TEXT_LINES)
    b_diff = make_text_only(TEXT_LINES_DIFF)
    save(a, "s1_text_before.png")
    save(b_same, "s1_text_after_same.png")
    save(b_diff, "s1_text_after_diff.png")
    pairs.append(("s1_identical", "s1_text_before.png", "s1_text_after_same.png"))
    pairs.append(("s1_different", "s1_text_before.png", "s1_text_after_diff.png"))

    # ── Scenario 2: Text + Equation ────────────────────────────────────────
    print("Scenario 2: Text + Equation")
    a = make_text_eq("2x^2 + 3x - 5 = 0")
    b_same = make_text_eq("2x^2 + 3x - 5 = 0")
    b_diff = make_text_eq("2x^2 - 3x + 5 = 0")  # changed signs
    save(a, "s2_eq_before.png")
    save(b_same, "s2_eq_after_same.png")
    save(b_diff, "s2_eq_after_diff.png")
    pairs.append(("s2_identical", "s2_eq_before.png", "s2_eq_after_same.png"))
    pairs.append(("s2_different", "s2_eq_before.png", "s2_eq_after_diff.png"))

    # ── Scenario 3: Text + Equation + Table ────────────────────────────────
    print("Scenario 3: Text + Equation + Table")
    hdrs = ["Student", "Math", "Science", "English"]
    rows = [
        ["Alice", "92", "88", "95"],
        ["Bob", "78", "85", "82"],
        ["Carol", "88", "90", "86"],
        ["David", "85", "79", "91"],
    ]
    rows_diff = [
        ["Alice", "92", "88", "95"],
        ["Bob", "78", "85", "82"],
        ["Carol", "88", "91", "86"],  # Science: 90 -> 91
        ["David", "85", "79", "93"],  # English: 91 -> 93
    ]
    a = make_text_eq_table("avg = sum(x_i) / n", hdrs, rows)
    b_same = make_text_eq_table("avg = sum(x_i) / n", hdrs, rows)
    b_diff = make_text_eq_table("avg = sum(x_i) / n", hdrs, rows_diff)
    save(a, "s3_table_before.png")
    save(b_same, "s3_table_after_same.png")
    save(b_diff, "s3_table_after_diff.png")
    pairs.append(("s3_identical", "s3_table_before.png", "s3_table_after_same.png"))
    pairs.append(("s3_different", "s3_table_before.png", "s3_table_after_diff.png"))

    # ── Scenario 4: Full (text + eq + table + chart) ───────────────────────
    print("Scenario 4: Full (text + equation + table + graph)")
    hdrs4 = ["Region", "Q1", "Q2"]
    rows4 = [["North", "120", "145"], ["South", "95", "110"], ["East", "80", "130"]]
    rows4_diff = [["North", "120", "145"], ["South", "95", "115"], ["East", "80", "130"]]  # Q2 South: 110->115
    labels = ["North", "South", "East"]
    vals = [145, 110, 130]
    vals_diff = [145, 115, 130]

    a = make_full("growth = (Q2-Q1)/Q1", hdrs4, rows4, "Q2 Performance", labels, vals)
    b_same = make_full("growth = (Q2-Q1)/Q1", hdrs4, rows4, "Q2 Performance", labels, vals)
    b_diff = make_full("growth = (Q2-Q1)/Q1", hdrs4, rows4_diff, "Q2 Performance", labels, vals_diff)
    save(a, "s4_full_before.png")
    save(b_same, "s4_full_after_same.png")
    save(b_diff, "s4_full_after_diff.png")
    pairs.append(("s4_identical", "s4_full_before.png", "s4_full_after_same.png"))
    pairs.append(("s4_different", "s4_full_before.png", "s4_full_after_diff.png"))

    # ── Write CSV for batch mode ───────────────────────────────────────────
    import csv
    csv_path = os.path.join(OUT, "test_pairs.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "before", "after"])
        for name, bf, af in pairs:
            w.writerow([name, os.path.join(OUT, bf), os.path.join(OUT, af)])
    print(f"\n  CSV: {csv_path}")
    print(f"\nDone — {len(pairs)} pairs generated.")


if __name__ == "__main__":
    generate_all()
