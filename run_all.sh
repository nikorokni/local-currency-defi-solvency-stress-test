#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"
export MPLCONFIGDIR="${TMPDIR:-/tmp}/solvency-revision-mpl"
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
mkdir -p "$MPLCONFIGDIR"
if [[ $# -gt 0 ]]; then
  python analysis/prepare_data.py --makerdao-events "$1"
else
  python analysis/prepare_data.py
fi
python analysis/stress_test.py
python -m unittest discover -s tests -v
python analysis/build_outputs.py
(cd manuscript && pdflatex -interaction=nonstopmode -halt-on-error main.tex && pdflatex -interaction=nonstopmode -halt-on-error main.tex)
(cd documentation && pdflatex -interaction=nonstopmode -halt-on-error model_algorithm.tex)
pandoc documentation/RESPONSE_TO_REVIEWERS.md --pdf-engine=pdflatex -V geometry:margin=0.85in -o documentation/RESPONSE_TO_REVIEWERS.pdf
printf '%s\n' 'Reproduction complete: manuscript/main.pdf and revision documents.'
