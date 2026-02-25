#!/usr/bin/env python3
"""
Batch OCR utility for nsfc-final-report

Given a root directory, find project subdirectories (immediate children by default) and run OCR on any project
that contains page_### image files. If a report.txt already exists in a project directory, it will be skipped
unless --force is provided.

Usage:
  python scripts/batch_ocr.py /path/to/root_dir
  python scripts/batch_ocr.py /path/to/root_dir --recursive --force --lang chi_sim

Options:
  --recursive    Walk the directory tree recursively and process any subdirectory containing page_ images.
  --force        Re-run OCR even if report.txt already exists.
  --lang         tesseract language code (default: leave unspecified). Example for Chinese: chi_sim
"""
import os
import sys
import argparse
import subprocess
from typing import List

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OCR_SCRIPT = os.path.join(SCRIPT_DIR, 'ocr_reports.py')

IMAGE_PREFIX = 'page_'
DEFAULT_OUT_NAME = 'report.txt'


def is_project_dir(path: str) -> bool:
    try:
        for fn in os.listdir(path):
            if fn.lower().startswith(IMAGE_PREFIX) and fn.lower().endswith(('.png', '.jpg', '.jpeg', '.tif', '.tiff')):
                return True
    except Exception:
        return False
    return False


def find_project_dirs(root: str, recursive: bool = False) -> List[str]:
    projects = []
    if recursive:
        for dirpath, dirnames, filenames in os.walk(root):
            if is_project_dir(dirpath):
                projects.append(dirpath)
    else:
        for name in os.listdir(root):
            full = os.path.join(root, name)
            if os.path.isdir(full) and is_project_dir(full):
                projects.append(full)
    return sorted(projects)


def run_ocr(project_dir: str, out_path: str = None, lang: str = None) -> int:
    out_path = out_path or os.path.join(project_dir, DEFAULT_OUT_NAME)
    cmd = [sys.executable, OCR_SCRIPT, project_dir, '--out', out_path]
    if lang:
        cmd.extend(['--lang', lang])
    try:
        proc = subprocess.run(cmd, check=True, capture_output=True)
        return 0
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode('utf-8', errors='replace') if e.stderr else ''
        print(f"OCR failed for {project_dir}: {stderr}", file=sys.stderr)
        return e.returncode


def main():
    parser = argparse.ArgumentParser(description='Batch OCR NSFC project report images')
    parser.add_argument('root', help='root directory containing project subdirectories')
    parser.add_argument('--recursive', action='store_true', help='search recursively')
    parser.add_argument('--force', action='store_true', help='re-run OCR even if report.txt exists')
    parser.add_argument('--lang', default=None, help='tesseract language code (e.g. chi_sim)')
    args = parser.parse_args()

    root = args.root
    if not os.path.isdir(root):
        print('Root directory not found:', root, file=sys.stderr)
        sys.exit(2)

    projects = find_project_dirs(root, recursive=args.recursive)
    if not projects:
        print('No project directories with page_ images found under', root)
        sys.exit(0)

    print(f'Found {len(projects)} project(s) to consider under {root}')
    processed = 0
    skipped = 0
    failed = 0
    for p in projects:
        out_path = os.path.join(p, DEFAULT_OUT_NAME)
        if os.path.exists(out_path) and not args.force:
            print('Skipping (exists):', p)
            skipped += 1
            continue
        print('OCRing:', p)
        ret = run_ocr(p, out_path=out_path, lang=args.lang)
        if ret == 0:
            processed += 1
        else:
            failed += 1
    print(f'Done. processed={processed}, skipped={skipped}, failed={failed}')

if __name__ == '__main__':
    main()
