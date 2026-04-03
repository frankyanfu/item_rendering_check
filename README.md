# Screenshot Diff Tool

Compare screenshots by **visual diff**, **text**, **equations (LaTeX)**, **tables**, and **charts/graphs** — fully local, no LLM API required.

## Table of Contents

- [Features](#features)
- [What's New in v0.7.0](#whats-new-in-v070)
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
| **Visual Diff** | SSIM + perceptual hashing | Pixel-level structural comparison with changed-region detection |
| **Text Extraction** | Tesseract OCR | Line-by-line text comparison using difflib |
| **Equation → LaTeX** | pix2tex (LatexOCR) | Detects multiple math equations and converts to LaTeX code |
| **Table Comparison** | OpenCV morphological grid detection + Tesseract | Detects multiple table grids, extracts cell text, compares cell-by-cell |
| **Chart/Graph Comparison** | OpenCV edge detection + Tesseract | Detects chart regions, extracts axis labels and title |
| **Confidence Scoring** | Weighted multi-layer | Per-layer and overall confidence scores (0–100%) |
| **Batch Mode** | CSV input/output | Process many image pairs with resume and parallel support |

All layers are fully local — no internet, no LLM API calls needed.

---

## What's New in v0.7.0

- **Visual diff layer** — SSIM + perceptual hash comparison with changed-region bounding boxes
- **Confidence scoring** — per-layer confidence (visual, text, equation, table, graph) and weighted overall score
- **Logging & `--verbose` flag** — structured logging across all modules; use `-v` for debug output
- **Performance optimizations** — visual gate skips semantic layers when images are pixel-identical; per-layer timing in results
- **Batch improvements** — `--resume` to skip already-processed pairs, `--workers N` for parallel execution, progress bar
- **Bug fixes** — inverted SSIM diff map, false positive equations/charts, table grid detection rewrite (morphological approach), pix2tex non-determinism guard

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
cd item_rendering_check
python -m pip install -r requirements.txt
```

Or install as a package:
```bash
python -m pip install .
```

Or use Pipenv:
```bash
pipenv install
pipenv shell
```

**Key dependencies:**
```
Pillow>=10.0.0
pytesseract>=0.3.10
click>=8.1.0
opencv-python>=4.9.0.0
pix2tex>=0.1.4
numpy>=1.26.0
imagehash
scikit-image
```

> **Note:** `pix2tex` downloads a ~97 MB model file (LaTeX OCR weights) on first use. No internet is needed after that — the model is cached locally.

---

## Quick Start

### Compare two screenshots

```bash
python -m item_rendering_check.cli compare before.png after.png
```

Skip specific content types:
```bash
python -m item_rendering_check.cli compare a.png b.png --no-tables --no-graphs
```

Enable debug logging:
```bash
python -m item_rendering_check.cli -v compare a.png b.png
```

### Batch compare from CSV

```bash
python -m item_rendering_check.cli batch pairs.csv -o results.csv
```

Resume an interrupted batch run:
```bash
python -m item_rendering_check.cli batch pairs.csv -o results.csv --resume
```

Parallel batch (4 workers):
```bash
python -m item_rendering_check.cli batch pairs.csv -o results.csv --workers 4
```

### Extract content from one screenshot

```bash
python -m item_rendering_check.cli extract screenshot.png
```

---

## CLI Commands

### `compare` — Compare two screenshots

```bash
python -m item_rendering_check.cli compare PATH1 PATH2 [OPTIONS]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--ocr-lang` | `eng` | Tesseract language code. Common: `eng`, `chi_sim`, `jpn`, `fra`, `deu` |
| `--no-visual` | False | Skip pixel-level visual diff (SSIM + hash) |
| `--no-tables` | False | Skip table detection and comparison |
| `--no-graphs` | False | Skip chart/graph detection and comparison |
| `--json` | False | Output results as JSON (includes confidence, timings) |

**Example:**
```bash
python -m item_rendering_check.cli compare a.png b.png --ocr-lang chi_sim
```

**Output includes:**
- Per-layer results (visual, text, equations, tables, graphs)
- Confidence score: overall and per-layer (e.g. `Confidence: 82% (visual=98%, text=98%, equation=50%, table=50%)`)
- Per-layer timing when using `--json`

---

### `batch` — Batch compare from CSV

```bash
python -m item_rendering_check.cli batch INPUT_CSV [OPTIONS]
```

| Flag | Default | Description |
|------|---------|-------------|
| `-o, --output-csv` | `INPUT_stem_results.csv` | Output CSV path |
| `--ocr-lang` | `eng` | Tesseract language code |
| `--no-visual` | False | Skip visual diff |
| `--no-tables` | False | Skip table comparison |
| `--no-graphs` | False | Skip chart/graph comparison |
| `--resume` | False | Skip rows already present in output CSV |
| `--workers N` | 1 | Number of parallel workers |

**Input CSV:** Auto-detects columns named `before` / `after` (and variants: `before_path`, `image1`, `path1`, etc.)

```csv
before,after
img/page1_before.png,img/page1_after.png
img/page2_before.png,img/page2_after.png
```

**Example:**
```bash
python -m item_rendering_check.cli batch pairs.csv -o results.csv --no-graphs --workers 4 --resume
```

---

### `extract` — Extract content from one image

```bash
python -m item_rendering_check.cli extract PATH [--ocr-lang LANG]
```

Shows all detected content: plain text, equations (LaTeX), and tables.

---

## Python Library API

```python
from item_rendering_check import compare

result = compare("before.png", "after.png")

# Overall verdict
print(result['verdict'])   # 'identical' | 'visual_diff' | 'text_diff' | 'equation_diff' | 'table_diff' | 'graph_diff' | 'multiple_diff'
print(result['same'])      # True or False

# Confidence scoring (new in v0.7.0)
print(result['confidence'])        # 0.0 – 1.0 weighted overall
print(result['layer_confidence'])  # {'visual': 0.98, 'text': 0.95, 'equation': 0.5, ...}
print(result['timings'])           # {'visual': 0.07, 'text': 0.5, ...} seconds per layer

# Visual diff layer (new in v0.7.0)
vis = result['visual_result']
if vis:
    print(vis['ssim_score'])          # 0.0 – 1.0 structural similarity
    print(vis['is_different'])        # True/False
    print(vis['num_changed_regions']) # count of changed bounding boxes
    print(vis['changed_regions'])     # list of {x, y, width, height, mean_intensity}

# Text layer
tr = result['text_result']
print(tr['similarity'])     # 0.0 – 1.0
print(tr['text1'])          # raw text from image 1
print(tr['text2'])          # raw text from image 2

# Equation layer (LaTeX) — supports multiple equations per image
er = result['equation_result']
if er:
    print(er['count1'], er['count2'])  # equation counts per image
    print(er['latex_list1'])           # list of LaTeX strings from image 1
    print(er['latex_list2'])           # list of LaTeX strings from image 2
    print(er['verdict'])               # 'identical' | 'content_diff' | 'count_mismatch' | ...

# Table layer — supports multiple tables per image
tbl = result['table_result']
if tbl:
    print(tbl['count1'], tbl['count2'])  # table counts per image
    print(tbl['verdict'])                 # 'identical' | 'content_diff' | ...
    print(tbl['pairings'])                # matched table pairs with diff counts

# Chart layer — supports multiple charts per image
gr = result['graph_result']
if gr:
    print(gr['count1'], gr['count2'])
    print(gr['verdict'])

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
    detect_equations: bool = True,   # Enable equation detection
    detect_tables: bool = True,      # Enable table detection
    detect_graphs: bool = True,      # Enable chart/graph detection
    detect_visual: bool = True,      # Enable pixel-level visual diff
) -> dict
```

---

## Output CSV Column Reference

When using `batch` mode, the output CSV contains these columns:

| Column | Description |
|--------|-------------|
| `before_path` | File path to the "before" screenshot |
| `after_path` | File path to the "after" screenshot |
| `verdict` | Overall result: `identical`, `visual_diff`, `text_diff`, `equation_diff`, `table_diff`, `graph_diff`, `multiple_diff`, or `ERROR` |
| `same` | `True` if all layers identical, `False` if any difference found, empty if ERROR |
| `confidence` | 0.0–1.0 weighted overall confidence score |
| `visual_ssim` | 0.0–1.0 SSIM structural similarity score |
| `text_similarity` | 0.0–1.0 similarity score from OCR text comparison |
| `table_similarity` | Table similarity score (empty if no tables detected) |
| `graph_similarity` | Graph similarity score (empty if no graphs detected) |
| `eq_count` | Equation counts as `N/M` (image 1 / image 2) |
| `table_count` | Table counts as `N/M` (image 1 / image 2) |
| `graph_count` | Graph counts as `N/M` (image 1 / image 2) |
| `summary` | Human-readable one-liner describing the overall result |

**Example output row:**
```csv
before_path,after_path,verdict,same,confidence,visual_ssim,text_similarity,table_similarity,graph_similarity,eq_count,table_count,graph_count,summary
img/v1.png,img/v2.png,text_diff,False,0.82,0.95,0.84,,,0/0,0/0,0/0,Text differs: 4 line(s) added and 4 removed
```

---

## How Each Layer Works

### Text (Tesseract OCR + difflib)
1. Run Tesseract OCR on both images to extract all text
2. Compare line-by-line using Python's `difflib.unified_diff`
3. `text_similarity` = `difflib.SequenceMatcher` ratio
4. `text_num_added` / `text_num_removed` = count of differing lines

### Visual Diff (SSIM + Perceptual Hash)
1. Quick check with perceptual hash (average, difference, wavelet) for fast screening
2. Compute SSIM (Structural Similarity Index) between images
3. Threshold the SSIM diff map to find changed regions
4. Return bounding boxes, sizes, and intensities of each changed region
5. Acts as a **visual gate**: if no visual changes detected, semantic layers (equations, tables, graphs) are skipped for performance

### Equations (pix2tex LatexOCR)
1. Detect equation candidates via contour analysis (minimum area 1500px, minimum width 50px)
2. Run pix2tex on each candidate crop (deep learning model, runs fully offline after first download)
3. Validate with `_is_valid()` — requires genuine LaTeX math tokens (`\frac`, `\sqrt`, `^{`, `_{`, etc.) and a minimum `real_math_count`
4. Normalize LaTeX with `_normalize_latex()` to strip whitespace variations
5. Match equations between images by spatial position and compare LaTeX strings
6. Visual gate: skip entirely when SSIM shows no changed regions (avoids pix2tex non-determinism)

### Tables (OpenCV Morphological Detection + Tesseract)
1. Adaptive threshold to get binary image
2. Morphological open with directional kernels to isolate horizontal and vertical lines
3. Combine line masks and use connected components to separate distinct table structures
4. For each component: projection profiles to find grid line positions
5. Filter: require ≥3 horizontal and ≥3 vertical lines, each ≥50% of longest line
6. Extract cells between adjacent grid lines, OCR each cell with Tesseract
7. Compare tables cell-by-cell; report which cells differ

### Charts / Graphs (OpenCV + Tesseract)
1. Detect chart region by finding strong axes (vertical line on left, horizontal line at bottom)
2. Color saturation check to reject false positives (tables/borders with <2% colored pixels)
3. Crop chart region and classify type (bar vs line vs unknown) by edge orientation
4. OCR the axis label strips: x-axis (bottom), y-axis (left), title (top), legend (right)
5. Compare axis labels between two images

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
python -m item_rendering_check.cli compare a.png b.png
```

### False positive table/chart detection

The table and graph detectors use heuristics (line detection, region detection). In images that contain UI boxes, borders, or structured layouts, they may incorrectly identify "tables" or "charts."

To disable these layers:
```bash
python -m item_rendering_check.cli compare a.png b.png --no-tables --no-graphs
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
item_rendering_check/
├── __init__.py          # Package exports (v0.7.0)
├── comparator.py        # Main compare() — orchestrates all layers, confidence scoring, timing
├── visual_diff.py       # SSIM + perceptual hash visual comparison
├── region_detector.py   # Changed-region detection from SSIM diff maps
├── text_diff.py         # Tesseract OCR + difflib text comparison
├── equation.py          # pix2tex LatexOCR — multi-equation detection + LaTeX normalization
├── table.py             # OpenCV morphological table detection + OCR cell extraction
├── cli.py               # Click CLI (compare, batch, extract) with --verbose, --resume, --workers
├── Pipfile              # Pipenv dependencies
├── requirements.txt     # pip dependencies
├── setup.py             # Package setup
├── generate_test_images.py  # Synthetic test image generator
├── run_tests.py         # Test runner (9 test pairs)
└── README.md            # This file
```