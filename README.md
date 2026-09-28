# Local-Currency DeFi Lending under Joint FX and Crypto Shocks
## A Path-Dependent Credit-Loss Stress Test

Niko Rokni Lamouki · Salma Soofiyan

**Major revision, 28 September 2026.** This version supersedes the former *From Debt Erosion to Protocol Solvency* manuscript and its numerical outputs. It studies a hypothetical architecture; it does not establish real-protocol solvency, peg stability or safe capital requirements.

- [Clean revised paper](manuscript/main.pdf)
- [Point-by-point response](documentation/RESPONSE_TO_REVIEWERS.pdf)
- [One-page model algorithm](documentation/model_algorithm.pdf)
- [Parameter provenance](documentation/parameter_provenance.csv)
- [Headline-number reconciliation](results/headline_reconciliation.csv)
- [Source and reference audit](documentation/REFERENCE_AUDIT.md)

## What changed

Both FX and crypto marks now use monthly averages. Liquidation close-out extends beyond the 12-month origination horizon, and pending exposure is reported explicitly. Debt recovery, collectible penalties, borrower residuals and matched funding liabilities are separate. Credit-budget exhaustion is not called insolvency. Six rate rules, principal-weight ablations, joint auction/CR sensitivities, sample perturbations and input-resampling uncertainty are included.

Empirical information consists of 42 joint monthly returns. Collateral ratios, auction frictions, policy coefficients and funding assumptions are **illustrative**. MakerDAO principal summaries illustrate scale/concentration; they do not calibrate the percentage-loss model when size and CR are independent.

## Reproduce

Python 3.11+, dependencies in `requirements.txt`, a standard LaTeX installation, and Pandoc are required. Reproduction uses local input snapshots and makes no network requests.

```bash
python -m pip install -r requirements.txt
bash run_all.sh
```

To regenerate the optional inherited MakerDAO principal summaries, supply the companion event file:

```bash
bash run_all.sh /path/to/makerdao_eth_a_draw_events_analysis.csv
```

The script checks that external file's documented hash. The main percentage results require only the included market snapshots. Main simulations use 20,000 paths per pair; the joint grid uses 5,000 common paths per cell; input uncertainty uses 100 outer calibrations and 2,000 inner paths each. Run settings and input hashes are recorded in `results/run_metadata.json`.

```bash
python -m unittest discover -s tests -v
```

Tests cover strict breach semantics, final-month close-out, irreversible liquidation, delayed accrual, cash conservation, capital accounting, no rate look-ahead, governance limits, calendar-safe block sampling and result reconciliation.

## Repository map

| Location | Contents |
|---|---|
| `analysis/prepare_data.py` | Raw snapshots to monthly-average panel |
| `analysis/stress_test.py` | Model, simulations, ablations and sensitivity |
| `analysis/build_outputs.py` | CSV-backed tables, figures and headline macros |
| `data/` | Archived raw prices/FX and processed input summaries |
| `results/` | Machine-generated results and run metadata |
| `tests/` | Accounting and boundary-case checks |
| `manuscript/` | Current paper source and compiled PDF |
| `documentation/` | Response, algorithm, provenance and verification records |

The earlier manuscript and outputs remain accessible in Git history at `c1e8ef839bc91c3830f6c08b45a10183c68125ba`. They should not be mixed with this revision's CSVs or conclusions.

Companion paper: [Inflation-driven debt erosion](https://github.com/nikorokni/inflation-driven-debt-erosion-defi). Reused data and methodological overlap are disclosed explicitly in the revised paper.
