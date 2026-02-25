#!/usr/bin/env bash
set -euo pipefail

# batch_ocr.sh
# Usage: batch_ocr.sh [-r] [-f] [-l LANG] ROOT_DIR
# -r : recursive (search subdirectories)
# -f : force overwrite existing report.txt
# -l LANG : tesseract language (e.g. chi_sim)

usage(){
  cat <<EOF
Usage: $0 [-r] [-f] [-l LANG] ROOT_DIR
  -r    Recurse into subdirectories to find project dirs containing page_*.png
  -f    Force re-run OCR even if report.txt exists
  -l    Tesseract language code (e.g. chi_sim). If omitted, default Tesseract language is used.

This script finds directories with files named page_*.png/.jpg and runs tesseract on each page
in lexical order, concatenating results into <project_dir>/report.txt. A simple divider is
inserted between pages.
EOF
}

RECURSIVE=0
FORCE=0
LANG=""

while getopts ":rfl:h" opt; do
  case ${opt} in
    r ) RECURSIVE=1 ;;
    f ) FORCE=1 ;;
    l ) LANG=${OPTARG} ;;
    h ) usage; exit 0 ;;
    \? ) echo "Invalid option: -$OPTARG" >&2; usage; exit 2 ;;
    : ) echo "Option -$OPTARG requires an argument." >&2; usage; exit 2 ;;
  esac
done
shift $((OPTIND -1))

ROOT=${1:-}
if [ -z "$ROOT" ]; then
  usage
  exit 2
fi

if [ ! -d "$ROOT" ]; then
  echo "Root directory not found: $ROOT" >&2
  exit 2
fi

# Find candidate project directories
mapfile -t PROJECT_DIRS < <( 
  if [ "$RECURSIVE" -eq 1 ]; then
    # find any directory containing a page_ file
    find "$ROOT" -type f \( -iname 'page_*.png' -o -iname 'page_*.jpg' -o -iname 'page_*.jpeg' -o -iname 'page_*.tif' -o -iname 'page_*.tiff' \) -print0 | xargs -0 -n1 dirname | sort -u
  else
    # only immediate children
    for d in "$ROOT"/*/ ; do
      [ -d "$d" ] || continue
      shopt -s nullglob
      files=("$d"page_*.png "$d"page_*.jpg "$d"page_*.jpeg "$d"page_*.tif "$d"page_*.tiff)
      if [ ${#files[@]} -gt 0 ]; then
        printf '%s
' "$d"
      fi
    done | sort -u
  fi
)

if [ ${#PROJECT_DIRS[@]} -eq 0 ]; then
  echo "No project directories with page_ images found under $ROOT"
  exit 0
fi

echo "Found ${#PROJECT_DIRS[@]} project(s) to process"

for proj in "${PROJECT_DIRS[@]}"; do
  # normalize proj path (remove trailing slash)
  proj=${proj%/}
  out="$proj/report.txt"
  if [ -f "$out" ] && [ "$FORCE" -eq 0 ]; then
    echo "Skipping (exists): $proj"
    continue
  fi
  echo "OCRing: $proj"
  tmpf=$(mktemp)
  cleanup(){ rm -f "$tmpf"; }
  trap cleanup RETURN

  # iterate pages in name order
  shopt -s nullglob
  pages=("$proj"/page_*.png "$proj"/page_*.jpg "$proj"/page_*.jpeg "$proj"/page_*.tif "$proj"/page_*.tiff)
  # ensure sorting by basename
  if [ ${#pages[@]} -eq 0 ]; then
    echo "  No page images found, skipping: $proj"
    continue
  fi
  # sort by filename
  IFS=$'\n' sorted=( $(printf '%s\n' "${pages[@]}" | sort) )
  unset IFS

  for img in "${sorted[@]}"; do
    echo "\n\n----- PAGE: $(basename "$img") -----\n\n" >> "$tmpf"
    if [ -n "$LANG" ]; then
      if ! tesseract "$img" stdout -l "$LANG" >> "$tmpf" 2>> "$tmpf"; then
        echo "  tesseract failed on $img, continuing" >&2
      fi
    else
      if ! tesseract "$img" stdout >> "$tmpf" 2>> "$tmpf"; then
        echo "  tesseract failed on $img, continuing" >&2
      fi
    fi
  done

  # move tmp to final
  mv "$tmpf" "$out"
  echo "  Wrote $out"
  trap - RETURN
done

exit 0
