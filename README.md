# Local-currency DeFi solvency stress test

Replication package for:

> *From Debt Erosion to Protocol Solvency: Path-Dependent Stress Testing of Local-Currency DeFi Lending under Joint FX and Crypto-Collateral Shocks*

Authors: Niko Rokni Lamouki, Salma Soofiyan, and Amin Karami. Corresponding author: `nrokni@uel.ac.uk`.

The manuscript source is `manuscript/main.tex`; the compiled paper is `manuscript/main.pdf`.

## Research design

The package extends the companion debt-erosion paper from a terminal collateral screen to a monthly, path-dependent solvency model. It combines:

- 130,742 decoded MakerDAO ETH-A debt draws for portfolio calibration;
- official ARS/USD and TRY/USD monthly averages from OECD Main Economic Indicators via FRED;
- Coin Metrics ETH and BTC daily reference prices aggregated to month-end;
- all realised 12-month windows from February 2020 through July 2023;
- 20,000 three-month moving-block bootstrap paths per currency–collateral pair;
- static and lagged FX-responsive borrowing rates;
- collateral-ratio triggers, execution delay, auction haircuts, congestion, bad debt, reserve breach, and CVaR-consistent debt ceilings.

The system is hypothetical. The results are transparent design stresses, not realised user returns, a forecast, or evidence that an ARS- or TRY-pegged lending protocol has been implemented.

## Main reproducibility anchors

- Joint monthly return observations: 42.
- Realised 12-month windows per currency–collateral pair: 31.
- Bootstrap paths per pair: 20,000.
- Base block length: 3 months.
- Random seed: `20260810`.
- Adaptive 75% ARS/ETH mean bad debt, timely: 3.44% of principal.
- Adaptive 75% TRY/ETH mean bad debt, timely: 3.21%.
- Adaptive 75% ARS/ETH 99% CVaR, timely: 30.26%.
- Adaptive 75% TRY/ETH 99% CVaR, timely: 25.75%.

## Folder guide

- `analysis/`: input preparation and complete stress-test code.
- `data/raw_fx/`: original official FRED CSV downloads.
- `data/raw_prices/`: pinned Coin Metrics BTC and ETH analysis-window extracts (`time` and `PriceUSD`).
- `data/processed/`: common monthly panel, MakerDAO sample construction, 100 principal-quantile bins, summaries, and checksums.
- `results/`: all numerical outputs and validation checks.
- `tables/`: machine-generated LaTeX table fragments.
- `figures/`: eight generated 300-dpi figures.
- `manuscript/`: English LaTeX source, figures, journal class files, and compiled PDF.
- `documentation/`: provenance, equations, assumptions, and manuscript anchors.

## Reproduce

Python 3.11 or later is recommended.

```bash
python -m pip install -r requirements.txt
bash run_all.sh
```

`run_all.sh` rebuilds the joint market panel, stress results, tables, figures, and PDF. The included principal calibration is sufficient because percentage stress outcomes are homogeneous in principal.

To rebuild the principal quantiles from the companion event-level file as well:

```bash
bash run_all.sh /path/to/makerdao_eth_a_draw_events_analysis.csv
```

The event-level file and raw archive are documented in `documentation/SOURCES.md` and the companion repository:

<https://github.com/nikorokni/inflation-driven-debt-erosion-defi>

## Licensing

Analysis code and original text are released under the MIT License. Source data retain their original terms. Coin Metrics Community Data are distributed under CC BY-NC 4.0; the package preserves attribution and pinned analysis-window extracts. Users are responsible for checking whether their intended use is permitted.

## Repository

<https://github.com/nikorokni/local-currency-defi-solvency-stress-test>
