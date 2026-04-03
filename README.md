# Screenshot Diff Tool

Compare screenshots by **text**, **equations (LaTeX)**, **tables**, and **charts/graphs** — fully local, no LLM API required.

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Commands](#cli-commands)
- [Batch Mode (CSV)](#batch-mode-csv)
- [Python Library API](#python-library-api)
- [Output CSV Column Reference](#output-csv-column-reference)
- [Troubleshooting](#troubleshooting)

---

## Features

| Feature | Technology | Description |
|---------|-----------|-------------|
| **Text Extraction** | Tesseract OCR | Line-by-line text comparison using difflib |
| **Equation → LaTeX** | pix2tex (LatexOCR) | Detects math equations and converts to LaTeX code |
| **Table Comparison** | OpenCV grid detection + Tesseract | Detects table grids, extracts cell text, compares cell-by-cell |
| **Chart/Graph Comparison** | OpenCV edge detection + Tesseract | Detects chart regions, extracts axis labels and title |
| **Batch Mode** | CSV input/output | Process many image pairs from a CSV file |

All layers are fully local — no internet, no LLM API calls needed.

---

## Requirements

| Requirement | Version | Install (Windows) | Install (macOS) | Install (Linux) |
|-------------|---------|-------------------|-----------------|-----------------|
| Python | ≥ 3.9 | [python.org](https://www.python.org/downloads/) | `brew install python3` | `sudo apt install python3` |
| Tesseract OCR | any recent | [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki) | `brew install tesseract` | `sudo apt install tesseract-ocr` |

> **On Windows:** During Python install, check "Add Python to PATH". After installing Tesseract, set `TESSDATA_PREFIX=C:\Program Files\Tesseract-OCR\tessdata`.

---

## Installation

### 1. Install Tesseract OCR

**Windows:** Download from [UB Mannheim releases](https://github.com/UB-Mannheim/tesseract/wiki) and run the installer. Add `C:\Program Files\Tesseract-OCR` to your PATH.

**macOS:**
```bash
brew install tesseract
```

**Ubuntu/Debian:**
```bash
sudo apt install tesseract-ocr
```

### 2. Install Python dependencies

```bash
cd screenshot_diff
python -m pip install -r requirements.txt
```

Or install as a package:
```bash
python -m pip install .
```

**requirements.txt:**
```
Pillow>=10.0.0
pytesseract>=0.3.10
click>=8.1.0
opencv-python>=4.9.0.0
pix2tex>=0.1.4
numpy>=1.26.0
```

> **Note:** `pix2tex` downloads a ~97 MB model file (LaTeX OCR weights) on first use. No internet is needed after that — the model is cached locally.

---

## Quick Start

### Compare two screenshots

```bash
python -m screenshot_diff.cli compare-cmd before.png after.png
```

Skip specific content types:
```bash
python -m screenshot_diff.cli compare-cmd a.png b.png --no-equations --no-tables --no-graphs
```

### Batch compare from CSV

```bash
python -m screenshot_diff.cli batch pairs.csv -o results.csv
```

### Extract content from one screenshot

```bash
python -m screenshot_diff.cli extract screenshot.png
```

---

## CLI Commands

### `compare-cmd` — Compare two screenshots

```bash
python -m screenshot_diff.cli compare-cmd PATH1 PATH2 [OPTIONS]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--ocr-lang` | `eng` | Tesseract language code. Common: `eng`, `chi_sim`, `jpn`, `fra`, `deu` |
| `--no-equations` | False | Skip equation (LaTeX) detection and comparison |
| `--no-tables` | False | Skip table detection and comparison |
| `--no-graphs` | False | Skip chart/graph detection and comparison |
| `--json` | False | Output results as JSON |

**Example:**
```bash
python -m screenshot_diff.cli compare-cmd a.png b.png --ocr-lang chi_sim
```

---

### `batch` — Batch compare from CSV

```bash
python -m screenshot_diff.cli batch INPUT_CSV [OPTIONS]
```

| Flag | Default | Description |
|------|---------|-------------|
| `-o, --output-csv` | `INPUT_stem_results.csv` | Output CSV path |
| `--ocr-lang` | `eng` | Tesseract language code |
| `--no-equations` | False | Skip equation comparison |
| `--no-tables` | False | Skip table comparison |
| `--no-graphs` | False | Skip chart/graph comparison |

**Input CSV:** Auto-detects columns named `before` / `after` (and variants: `before_path`, `image1`, `path1`, etc.)

```csv
before,after
img/page1_before.png,img/page1_after.png
img/page2_before.png,img/page2_after.png
```

**Example:**
```bash
python -m screenshot_diff.cli batch pairs.csv -o results.csv --no-graphs
```

---

### `extract` — Extract content from one image

```bash
python -m screenshot_diff.cli extract PATH [--ocr-lang LANG]
```

Shows all detected content: plain text, equations (LaTeX), and tables.

---

## Python Library API

```python
from screenshot_diff import compare

result = compare("before.png", "after.png")

# Overall verdict
print(result['verdict'])   # 'identical' | 'text_diff' | 'equation_diff' | 'table_diff' | 'graph_diff' | 'multiple_diff'
print(result['same'])      # True or False

# Text layer
tr = result['text_result']
print(tr['similarity'])     # 0.0 – 1.0
print(tr['text1'])          # raw text from image 1
print(tr['text2'])          # raw text from image 2

# Equation layer (LaTeX)
er = result['equation_result']
if er:
    print(er['latex1'])     # LaTeX from image 1 (or None)
    print(er['latex2'])     # LaTeX from image 2 (or None)
    print(er['same'])       # True/False

# Table layer
tbl = result['table_result']
if tbl:
    print(tbl['table1'])    # list of rows: [["Name", "Age"], ["Alice", "30"]]
    print(tbl['same'])       # True/False
    print(tbl['differences']) # list of (row, col, val1, val2) tuples

# Chart layer
gr = result['graph_result']
if gr:
    print(gr['axis_labels_1'])  # {'title': '...', 'x_axis': '...', 'y_axis': '...'}
    print(gr['same'])

# Summary
print(result['summary'])   # one-liner
print(result['findings'])  # list of human-readable findings
```

**Function signature:**
```python
compare(
    path1: str,
    path2: str,
    ocr_lang: str = None,           # Tesseract language code
    detect_equations: bool = True,  # Enable equation detection
    detect_tables: bool = True,     # Enable table detection
    detect_graphs: bool = True,    # Enable chart/graph detection
) -> dict
```

---

## Output CSV Column Reference

When using `batch` mode, the output CSV contains these columns:

### Identity Columns

| Column | Description |
|--------|-------------|
| `before_path` | File path to the "before" screenshot |
| `after_path` | File path to the "after" screenshot |
| `verdict` | Overall result: `identical`, `text_diff`, `equation_diff`, `table_diff`, `graph_diff`, `multiple_diff`, or `ERROR` |
| `same` | `True` if all layers identical, `False` if any difference found, empty if ERROR |

### Text Layer

| Column | Description |
|--------|-------------|
| `text_similarity` | 0.0–1.0 similarity score from OCR text comparison. `1.0` = identical |
| `text_num_added` | Number of text lines in "after" image not present in "before" |
| `text_num_removed` | Number of text lines in "before" image not present in "after" |
| `text1` | Full text extracted from the "before" image via Tesseract OCR |
| `text2` | Full text extracted from the "after" image via Tesseract OCR |

### Equation Layer (LaTeX)

| Column | Description |
|--------|-------------|
| `equation1` | LaTeX code extracted from "before" image (empty if no equation detected) |
| `equation2` | LaTeX code extracted from "after" image (empty if no equation detected) |
| `equations_same` | `True` if both have LaTeX and they match, `False` if they differ. Empty if neither has equations |

### Table Layer

| Column | Description |
|--------|-------------|
| `table1_detected` | `True` if a table/grid was detected in the "before" image |
| `table2_detected` | `True` if a table/grid was detected in the "after" image |
| `tables_same` | `True` if both have tables and all cells match, `False` if cells differ |
| `table_num_diffs` | Number of cells that differ between the two tables |
| `table1_csv` | CSV-formatted representation of table from "before" image |
| `table2_csv` | CSV-formatted representation of table from "after" image |

### Chart / Graph Layer

| Column | Description |
|--------|-------------|
| `graph1_detected` | `True` if a chart/graph region was detected in the "before" image |
| `graph2_detected` | `True` if a chart/graph region was detected in the "after" image |
| `graphs_same` | `True` if chart regions and axis labels match, `False` otherwise |
| `graph_x_label_1` | X-axis label text extracted from chart in "before" image |
| `graph_x_label_2` | X-axis label text extracted from chart in "after" image |
| `graph_y_label_1` | Y-axis label text extracted from chart in "before" image |
| `graph_y_label_2` | Y-axis label text extracted from chart in "after" image |

### Summary Columns

| Column | Description |
|--------|-------------|
| `summary` | Human-readable one-liner describing the overall result |
| `findings` | Pipe-separated (`\|`) list of per-layer findings, e.g. `Text: 84% similar, 4 line(s) added | Tables differ: 2 cell(s) different` |

**Example output row:**
```csv
before_path,after_path,verdict,same,text_similarity,text_num_added,text_num_removed,equation1,equation2,equations_same,table1_detected,table2_detected,tables_same,table_num_diffs,graph1_detected,graph2_detected,graphs_same,summary,findings
img/v1.png,img/v2.png,text_diff,False,0.84,4,4,,,,False,False,,0,False,False,,Text differs: 4 line(s) added, 4 removed|Equations: not detected in either|Tables: not detected in either|Graphs: not detected in either,Text: 84% similar, 4 line(s) added, 4 removed
```

---

## How Each Layer Works

### Text (Tesseract OCR + difflib)
1. Run Tesseract OCR on both images to extract all text
2. Compare line-by-line using Python's `difflib.unified_diff`
3. `text_similarity` = `difflib.SequenceMatcher` ratio
4. `text_num_added` / `text_num_removed` = count of differing lines

### Equations (pix2tex LatexOCR)
1. Run pix2tex on both images (deep learning model, runs fully offline after first download)
2. Filter output with heuristics — only accept if it looks like genuine LaTeX math (has `\frac`, `\sqrt`, `^{`, `_{`, etc.)
3. If one image has LaTeX and the other doesn't → `equations_same = False`
4. If both have LaTeX → compare strings exactly
5. Note: pix2tex may hallucinate on non-math images. The heuristic filter catches most false positives.

### Tables (OpenCV + Tesseract)
1. Run Canny edge detection on both images
2. Hough line detection to find horizontal and vertical lines
3. Filter to lines near corners (table border detection)
4. Use line intersections to define cell boundaries
5. Crop each cell and run Tesseract OCR on it
6. Compare cell-by-cell; report which cells differ and what the values are

### Charts / Graphs (OpenCV + Tesseract)
1. Detect chart region by finding strong axes (vertical line on left, horizontal line at bottom)
2. Crop chart region and classify type (bar vs line vs unknown) by edge orientation
3. OCR the axis label strips: x-axis (bottom), y-axis (left), title (top), legend (right)
4. Compare axis labels between two images

---

## Troubleshooting

### pix2tex model download on first run

The first time you run equation extraction, pix2tex downloads ~97 MB of model weights. This is cached locally and only happens once.

```
download weights v0.0.1 to path .../pix2tex/model/checkpoints
weights.pth: 100% | 97.4MB
```

If download fails, check your internet connection and retry.

### pix2tex not installed

```bash
python -m pip install pix2tex
```

### Tesseract not found (Windows)

```python
import os
os.environ['PATH'] = r'C:\Program Files\Tesseract-OCR;' + os.environ['PATH']
os.environ['TESSDATA_PREFIX'] = r'C:\Program Files\Tesseract-OCR\tessdata'
```

Or on command line:
```cmd
set PATH=%PATH%;C:\Program Files\Tesseract-OCR
python -m screenshot_diff.cli compare-cmd a.png b.png
```

### False positive table/chart detection

The table and graph detectors use heuristics (line detection, region detection). In images that contain UI boxes, borders, or structured layouts, they may incorrectly identify "tables" or "charts."

To disable these layers:
```bash
python -m screenshot_diff.cli compare-cmd a.png b.png --no-tables --no-graphs
```

### Equation extraction returns wrong results

pix2tex is an OCR model trained on math equations. It works best on:
- Clean, high-contrast equation images
- Equations rendered as text (not handwritten)
- Images where math is the main content (not a small part of a busy screenshot)

For full-page screenshots, equation detection may be unreliable. Consider using `--no-equations` for non-math content.

---

## Project Structure

```
screenshot_diff/
├── __init__.py       # Package exports
├── comparator.py      # Main compare() — orchestrates all layers
├── text_diff.py       # Tesseract OCR + difflib text comparison
├── equation.py        # pix2tex LatexOCR → LaTeX conversion
├── table.py           # OpenCV table detection + OCR cell extraction
├── cli.py             # Click-based CLI
├── requirements.txt   # Python dependencies
├── setup.py           # Package setup
└── README.md          # This file
```