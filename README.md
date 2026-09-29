# Local-Currency DeFi Lending under Joint FX and Crypto Shocks
## A Path-Dependent Credit-Loss Stress Test

Niko Rokni Lamouki · Salma Soofiyan

**Major revision, 28 September 2026.** This version supersedes the former *From Debt Erosion to Protocol Solvency* manuscript and its numerical outputs. It studies a hypothetical architecture; it does not establish real-protocol solvency, peg stability or safe capital requirements.

- [Clean revised paper](manuscript/main.pdf)
- [Point-by-point response for Salma](documentation/RESPONSE_TO_SALMA.pdf)
- [One-page model algorithm](documentation/model_algorithm.pdf)
- [Parameter provenance](documentation/parameter_provenance.csv)
- [Headline-number reconciliation](results/headline_reconciliation.csv)
- [Source and reference audit](documentation/REFERENCE_AUDIT.md)
- [End-to-end reproducibility audit and exhibit map](documentation/REPRODUCIBILITY_AUDIT.md)
- [Frozen SHA-256 manifest](documentation/reproducibility_manifest.json)

## What changed

Both FX and crypto marks now use monthly averages. Liquidation close-out extends beyond the 12-month origination horizon, and pending exposure is reported explicitly. Debt recovery, collectible penalties, borrower residuals and matched funding liabilities are separate. Credit-budget exhaustion is not called insolvency. Six rate rules, principal-weight ablations, joint auction/CR sensitivities, sample perturbations and input-resampling uncertainty are included.

Empirical information consists of 42 joint monthly returns. Collateral ratios, auction frictions, policy coefficients and funding assumptions are **illustrative**. MakerDAO principal summaries illustrate scale/concentration; they do not calibrate the percentage-loss model when size and CR are independent.

## Reproduce

Python 3.11+, dependencies in `requirements.txt`, a standard LaTeX installation, and Pandoc are required. Reproduction uses local input snapshots and makes no network requests.

```bash
python -m pip install -r requirements.txt
bash run_all.sh
python analysis/verify_reproduction.py
```

This checks the archived inputs, market-panel arithmetic, generated CSVs and LaTeX tables against 34 frozen SHA-256 values and confirms that all four generated figures are referenced by the manuscript. PDF creation timestamps vary across runs; the audit reports separate rendered/text comparison evidence.

The full event-level MakerDAO CSV is in the [companion repository at a pinned commit](https://github.com/nikorokni/inflation-driven-debt-erosion-defi/blob/6f6710982391b88f48a3dc7bb5bbfecc7691a47f/data/processed/makerdao_eth_a_draw_events_analysis.csv) (SHA-256 `0a9e0f0528345086b3a0f4ece8bb2fddd9080c97f5a0657f27a3549587e132b5`). To verify and regenerate the inherited principal bins without changing the main checkout, put both repositories side by side and run:

```bash
python analysis/verify_reproduction.py --makerdao-events ../inflation-driven-debt-erosion-defi/data/processed/makerdao_eth_a_draw_events_analysis.csv
```

The optional verifier checks the external file hash and rebuilds the inherited MakerDAO principal summaries in a temporary directory. The main percentage results require only the included market snapshots. Main simulations use 20,000 paths per pair; the joint grid uses 5,000 common paths per cell; input uncertainty uses 100 outer calibrations and 2,000 inner paths each. Run settings and input hashes are recorded in `results/run_metadata.json`.

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

See the [exhibit map](documentation/REPRODUCIBILITY_AUDIT.md#exhibit-to-source-map) for the source CSV of each displayed table and figure. The four nonnumerical/assumption tables (literature, balance sheet, notation and parameters) are authored directly in `manuscript/main.tex`.

The earlier manuscript and outputs remain accessible in Git history at `c1e8ef839bc91c3830f6c08b45a10183c68125ba`. They should not be mixed with this revision's CSVs or conclusions.

Companion paper: [Inflation-driven debt erosion](https://github.com/nikorokni/inflation-driven-debt-erosion-defi). Reused data and methodological overlap are disclosed explicitly in the revised paper.
