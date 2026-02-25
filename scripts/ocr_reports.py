#!/usr/bin/env python3
"""
OCR utility for nsfc-final-report

Usage:
  python scripts/ocr_reports.py /path/to/project_dir --out combined.txt

Requires tesseract binary available in PATH. This script will:
- find image files in the project directory named like page_###.png/jpg
- run tesseract on each page and collect text
- save combined text to the output file (UTF-8)
"""

import argparse
import os
import subprocess
import sys
from typing import List

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".tif", ".tiff")


def find_pages(project_dir: str) -> List[str]:
    files = os.listdir(project_dir)
    pages = [
        f for f in files if f.lower().endswith(IMAGE_EXTS) and f.startswith("page_")
    ]
    pages_sorted = sorted(pages)
    return [os.path.join(project_dir, p) for p in pages_sorted]


def ocr_image_to_text(image_path: str, lang: str = None) -> str:
    # use tesseract to stdout
    cmd = ["tesseract", image_path, "stdout"]
    if lang:
        cmd.insert(2, "-l")
        cmd.insert(3, lang)
    try:
        proc = subprocess.run(cmd, capture_output=True, check=True)
        text = proc.stdout.decode("utf-8", errors="replace")
        return text
    except subprocess.CalledProcessError as e:
        # return empty or error message
        err = e.stderr.decode("utf-8", errors="replace") if e.stderr else repr(e)
        return f"""[TESSERACT_ERROR on {image_path}]: {err}\n"""
    except FileNotFoundError:
        raise RuntimeError("tesseract not found in PATH; please install tesseract-ocr")


def ocr_dir(
    project_dir: str, out_path: str, header: str = None, lang: str = None
) -> None:
    pages = find_pages(project_dir)
    if not pages:
        raise ValueError(f"No page images found in {project_dir}")
    parts: List[str] = []
    if header:
        parts.append(header)
    for p in pages:
        parts.append(f"\n\n----- PAGE: {os.path.basename(p)} -----\n\n")
        txt = ocr_image_to_text(p, lang=lang)
        parts.append(txt)
    combined = "".join(parts)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(combined)


def main():
    parser = argparse.ArgumentParser(
        description="OCR NSFC report images in a project directory and combine to text"
    )
    parser.add_argument(
        "project_dir", help="path to project directory containing page_###.png/jpg"
    )
    parser.add_argument(
        "--out",
        "-o",
        default=None,
        help="output text file (default: <project_dir>/report.txt)",
    )
    parser.add_argument(
        "--header", "-H", default=None, help="optional header text to prepend"
    )
    parser.add_argument(
        "--lang",
        "-l",
        default=None,
        help="tesseract language code to pass as -l (e.g. chi_sim)",
    )
    args = parser.parse_args()
    lang = args.lang
    project_dir = args.project_dir
    if not os.path.isdir(project_dir):
        print("project_dir not found:", project_dir, file=sys.stderr)
        sys.exit(2)
    out_path = args.out or os.path.join(project_dir, "report.txt")
    try:
        ocr_dir(project_dir, out_path, header=args.header, lang=lang)
        print("Wrote combined OCR text to", out_path)
    except Exception as e:
        print("Error:", e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
