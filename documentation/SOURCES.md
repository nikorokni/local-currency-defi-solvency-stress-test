# Data provenance and checksums

Access date for online sources: **8 August 2026**.

## MakerDAO calibration

- Dataset paper: Yatipa Chaleenutthawut et al., “Loan Portfolio Dataset From MakerDAO Blockchain Project,” *IEEE Access*, 12 (2024), 24843–24854. DOI: <https://doi.org/10.1109/ACCESS.2024.3363225>.
- Public source repository: <https://github.com/Sudarut-kas/Data-Mining-for-MakerDAO>.
- Raw archive SHA-256: `85a43199a808c70575201e15cd367907e0dbc31d74869b47c15d37f312b80c23`.
- Decoded event file SHA-256: `0a9e0f0528345086b3a0f4ece8bb2fddd9080c97f5a0657f27a3549587e132b5`.
- Companion replication repository and decoder: <https://github.com/nikorokni/inflation-driven-debt-erosion-defi>.
- Companion commit: `6f6710982391b88f48a3dc7bb5bbfecc7691a47f`.
- Included derivatives: `sample_construction.csv`, 100 principal-quantile bins, and the exact principal summary.

The event-level file is 36 MB and the original raw archive is substantially larger. They are linked rather than duplicated. Running `analysis/prepare_data.py --makerdao-events <path>` regenerates the included principal calibration.

## Official foreign-exchange series

Both series are official monthly averages from OECD Main Economic Indicators, distributed by FRED, expressed as national-currency units per USD.

### Argentina

- Series: `ARGCCUSMA02STM`.
- Page: <https://fred.stlouisfed.org/series/ARGCCUSMA02STM>.
- Included file: `data/raw_fx/ars_usd_fred.csv`.
- SHA-256: `1dacf0b03e50660e0bbd819e3b73f6783576517a8d0cf9ac2559dbb92d0f455d`.

### Türkiye

- Series: `CCUSMA02TRM618N`.
- Page: <https://fred.stlouisfed.org/series/CCUSMA02TRM618N>.
- Included file: `data/raw_fx/try_usd_fred.csv`.
- SHA-256: `51d90a2eb45a989dcc078e04dacfcb06637026e90a3ead8d8290e8a61a32aad4`.

Official rates may differ from executable parallel-market rates under exchange controls. This is a stated limitation, not a missing-data adjustment.

## Crypto-collateral prices

- Publisher: Coin Metrics.
- Public archive: <https://github.com/coinmetrics/data>.
- Pinned commit: `f1a36afb962731c387bb03982758ab0103063da5` (archive update dated 24 May 2026).
- License: CC BY-NC 4.0.
- Included ETH analysis-window extract: `data/raw_prices/coinmetrics_eth.csv`.
- ETH extract SHA-256: `2c4588fac04c67a4f237054e24f63d8e78ef71f41f4edf5be44ccb3179649237`.
- Upstream full ETH snapshot SHA-256: `46b18f3df967405374b1f6ee8a3d11ee1b7a5b176ac9fb4342caf6bf8648f2cc`.
- Included BTC analysis-window extract: `data/raw_prices/coinmetrics_btc.csv`.
- BTC extract SHA-256: `d8534df0ef2a8435e414f201c1081773ec5b07a7e20c7cf19fef1183758d5d79`.
- Upstream full BTC snapshot SHA-256: `06495ff8e643432e6948b7b4686ce44fc106217287dabdc1b38351d9ddec46c3`.
- Metric: `PriceUSD`; last available daily value in each calendar month.

The included files retain only the `time` and `PriceUSD` columns for 1 January 2020 through 31 July 2023. They are deterministic extracts of the pinned upstream snapshots; the upstream checksums above permit independent verification against the complete source files.

## Common analysis window

The common panel contains 43 monthly level observations from January 2020 through July 2023 and 42 complete joint return observations. No eligible month is interpolated. All checksums are also stored in `data/processed/input_metadata.json`.
