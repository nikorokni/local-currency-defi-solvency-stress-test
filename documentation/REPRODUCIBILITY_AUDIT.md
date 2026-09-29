# Reproducibility audit — 29 September 2026

## Salma's reproducibility request and scope

The revised paper reports simulated results and makes reproducibility claims. This record identifies the exact input snapshots, code, generated outputs and manuscript exhibits and reports an independent clean-checkout rebuild. It does **not** establish that illustrative auction and funding assumptions are empirically calibrated, that official FX was executable, or that a real protocol is solvent.

## Clean-checkout reproduction

The published repository snapshot `4f5f4a1072f7af88dadbcb8d9eeb7159e23d17a5` was checked out into a separate detached worktree on 29 September 2026. In that checkout, `bash run_all.sh` completed with exit code zero, including all unit tests and LaTeX/Pandoc PDF builds. Before and after the run, SHA-256 was calculated for the 34 archived/generated market, result and table files frozen in `reproducibility_manifest.json`: **34 of 34 matched exactly**. The 18-page manuscript and both revision-document PDFs had identical extracted text and page counts before and after. All four figure PDFs had identical extracted text and identical SHA-256 values for their 1,600-pixel PNG renders. PDF bytes differed because Matplotlib/LaTeX insert generation times and document IDs. The scientific CSVs and TeX result tables did not differ.

For a fresh clone of this revision, install Python 3.11+ dependencies (`requirements.txt`), LaTeX and Pandoc, then run from the repository root:

```bash
bash run_all.sh
python analysis/verify_reproduction.py
```

The verifier independently recomputes the 43 monthly levels and 42 joint returns from the supplied raw FX and daily crypto snapshots. It checks the SHA-256 of four raw input CSVs, five processed files, ten result files and 15 generated TeX table/macro files; it checks that all generated table and figure files are referenced by the manuscript. The exact file list and hashes are in `reproducibility_manifest.json`. The `results/run_metadata.json` records seed 20260928, 20,000 main paths, 5,000 sensitivity paths per cell, 100 outer replicates, 2,000 inner paths, library versions, model settings and input hashes. This records a reproducible numerical run; Monte Carlo paths do not enlarge the 42-observation empirical sample.

### External MakerDAO input

The inherited ETH-A draw file is supplied by the [companion repository at a pinned commit](https://github.com/nikorokni/inflation-driven-debt-erosion-defi/blob/6f6710982391b88f48a3dc7bb5bbfecc7691a47f/data/processed/makerdao_eth_a_draw_events_analysis.csv). Its SHA-256 is `0a9e0f0528345086b3a0f4ece8bb2fddd9080c97f5a0657f27a3549587e132b5`; the same Git blob exists at the companion's published `054cae4cc86b545ac660125044a6295833ddc8de` revision. It contains 130,742 eligible draw events. The 29 September audit passed this file to `prepare_data.py` in the detached checkout: the resulting 100-bin principal CSV, principal summary JSON and market panel had **identical file hashes** to the archived outputs. Only `input_metadata.json` changed from `makerdao_events_verified_this_run: false` to `true`, as intended; the main simulation results were not changed by this optional verification.

To reproduce that check in a clean checkout without altering its baseline metadata:

```bash
python analysis/verify_reproduction.py --makerdao-events /path/to/makerdao_eth_a_draw_events_analysis.csv
```

The script uses a temporary directory for the optional rebuild. The first paper's raw dataset/archive and decoder are in the companion repository. This audit verifies the event-file checksum and the derived bins but does not independently rerun the original blockchain decoding. The current main stress-test percentages use the included principal bins only for a scale/weighting ablation; the model proves and tests their irrelevance to normalized percentage results under independent size and collateral-ratio weights.

## Input provenance and measurement

| Input | Supplied snapshot | Source and transformation | Important boundary |
|---|---|---|---|
| ARS/USD, TRY/USD | `data/raw_fx/*.csv` | Archived official OECD monthly-average LCU-per-USD series distributed by FRED; the precise series IDs, URLs and hashes are in `SOURCES.md`. | Official reference marks may differ from executable/parallel FX, particularly ARS. |
| ETH/USD, BTC/USD | `data/raw_prices/coinmetrics_*.csv` | 1,308 daily `PriceUSD` rows per asset, extracted from Coin Metrics `data` at pinned commit `f1a36afb962731c387bb03982758ab0103063da5`; arithmetic average by calendar month. `upstream_price_verification.json` records full upstream file hashes and the prior extract comparison. | A daily reference mark averaged by month is not an intramonth executable liquidation price. |
| MakerDAO ETH-A draws | Pinned 36 MB event CSV in companion repository; 100-bin derivative and summary in `data/processed/` here. | The optional verifier checks the event SHA-256 and regenerates the bins. | Draw events are not independent borrowers and do not calibrate initial CRs or auction haircuts here. |
| Joint panel | `data/processed/joint_monthly_market_panel.csv` | `analysis/prepare_data.py`: 43 months of aligned levels, then 42 monthly returns, January 2020–July 2023. | No additional observed market months are created by simulation. |

The four raw snapshot hashes in `input_metadata.json` and the frozen manifest match the actual repository files. Historical FRED snapshots may be revised at the live source; this package reproduces its archived version. Full original-source verification details and limits are in `SOURCES.md` and `REFERENCE_AUDIT.md`.

On 29 September 2026, the 43 ARS values in the analysis window were compared numerically with the [official FRED ARS table](https://fred.stlouisfed.org/data/ARGCCUSMA02STM), and the 43 TRY values with the [official FRED TRY table](https://fred.stlouisfed.org/data/CCUSMA02TRM618N). All 86 matched at the displayed source precision (absolute difference below `1e-10`). This is an additional current-source cross-check of the archived series; it does not make the official ARS rate an accessible trading price.

## Exhibit-to-source map

All generated numerical TeX tables and macros are made by `analysis/build_outputs.py`, then included by `manuscript/main.tex`. `analysis/stress_test.py` writes the eight principal simulation CSVs and `run_metadata.json`; `build_outputs.py` writes `headline_reconciliation.csv`. Extra cohort-level output is supplied in `results/cohort_results.csv` even though it is not a headline table.

| Manuscript exhibit / generated file | Immediate machine-readable source |
|---|---|
| Principal ablation `tables/ablation.tex` | `results/principal_ablation.csv` |
| ARS and TRY rate diagnostics `tables/rates_ARS.tex`, `rates_TRY.tex` | `results/rate_diagnostics.csv` |
| Main ETH, BTC appendix, mechanism, capital and borrower tables (`main`, `btc`, `mechanisms`, `capital`, `borrower`) | `results/main_results.csv` |
| Uncertainty `tables/uncertainty.tex` | `results/main_results.csv`, `results/input_uncertainty.csv` |
| Joint parameter ranges `tables/joint_ranges.tex` | `results/joint_sensitivity.csv` |
| Historical replay `tables/historical.tex` | `results/historical_replay.csv` |
| ARS and TRY robustness `tables/robust_ARS.tex`, `robust_TRY.tex` | `results/robustness.csv` |
| Reconciliation table `tables/reconciliation.tex`, headline macros `tables/numbers.tex`, and `results/headline_reconciliation.csv` | `results/main_results.csv` |
| Market averages `figures/market_averages.pdf` | `data/processed/joint_monthly_market_panel.csv` |
| Policy trade-off `figures/policy_tradeoff.pdf` | `results/main_results.csv` |
| ARS and TRY joint heatmaps `figures/joint_ARS.pdf`, `joint_TRY.pdf` | `results/joint_sensitivity.csv` |

The four authored tables on literature, illustrative balance sheet, notation and parameter provenance live directly in `manuscript/main.tex`. They are descriptive/assumption tables rather than simulated numeric outputs. `documentation/parameter_provenance.csv` lists the assumed and sourced inputs separately. The PDF is built from the LaTeX source, generated TeX files and generated figure PDFs. No manually transcribed simulation number is required to rebuild the headline abstract: it uses macros from `main_results.csv`.

## Interpretation of a successful audit

The package lets Salma regenerate and compare the reported numbers and displays from the archived inputs. It does not validate the assumed collateral distribution, auction haircut, congestion rule, matched-funding liability timing, or economically executable ARS conversion. Those choices are labeled as scenarios and sensitivity checks in the manuscript. Data provenance and computational reproducibility are narrower claims than external validity or Q1 acceptance.
