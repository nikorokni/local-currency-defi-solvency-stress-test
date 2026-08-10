#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

MPL_CACHE_DIR="${TMPDIR:-/tmp}/local-currency-defi-solvency-mpl"
export MPLCONFIGDIR="$MPL_CACHE_DIR"
mkdir -p "$MPL_CACHE_DIR"

if [[ $# -gt 0 ]]; then
  python analysis/prepare_data.py --makerdao-events "$1"
else
  python analysis/prepare_data.py
fi

python analysis/stress_test.py
python - <<'PY'
from pathlib import Path

from PIL import Image

for path in sorted(Path("figures").glob("figure*.png")):
    with Image.open(path) as image:
        image.verify()
PY
cp figures/figure*.png manuscript/figures/

cd manuscript
if command -v latexmk >/dev/null 2>&1; then
  latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
else
  pdflatex -interaction=nonstopmode -halt-on-error main.tex
  pdflatex -interaction=nonstopmode -halt-on-error main.tex
fi

if command -v gs >/dev/null 2>&1; then
  OPTIMIZED_PDF="$(mktemp "${TMPDIR:-/tmp}/solvency-main.XXXXXX.pdf")"
  trap 'rm -f "$OPTIMIZED_PDF"' EXIT
  gs -q -dNOPAUSE -dBATCH \
    -sDEVICE=pdfwrite \
    -dCompatibilityLevel=1.5 \
    -dPDFSETTINGS=/ebook \
    -dDetectDuplicateImages=true \
    -dCompressFonts=true \
    -sOutputFile="$OPTIMIZED_PDF" \
    main.pdf
  mv "$OPTIMIZED_PDF" main.pdf
  trap - EXIT
fi

echo "Reproduction complete: $PROJECT_DIR/manuscript/main.pdf"
