# Model specification

## Units and state variables

- `E_t`: local-currency units per USD. A positive return is LCU depreciation.
- `P_t`: USD collateral price.
- `d_t`: USD-equivalent debt divided by initial USD principal.
- `CR_t`: collateral value divided by USD-equivalent debt.
- Horizon: 12 months.

The debt factor is

`d_t = product(1 + i_m / 12) / product(1 + fx_depreciation_m)`.

The collateral ratio is

`CR_t = initial_CR * product(1 + crypto_return_m) / d_t`.

## Rate rules

- Static: 20% annual nominal rate.
- Adaptive 75%: 10% margin plus 75% of annualised trailing geometric depreciation, using up to the previous three months; clipped to 5–150%.
- Indexed 100%: 5% margin plus 100% of the same lagged depreciation signal; clipped to 5–200%.

The first month starts at 20% because no simulated lookback is available. Rules use lagged values only.

## Collateral distribution

Initial collateral ratios use 31 equally spaced points from 150% to 225%. Exposure weights follow a triangular density with mode 175%. This is a transparent stress assumption, not an estimate from the MakerDAO trace archive.

## Liquidation and recovery

- Liquidation threshold: 150%.
- Timely mechanism: zero-month delay and 8% base auction haircut.
- Delayed stress: one-month delay and 15% base haircut.
- Congestion surcharge: `0.20 × exposure liquidated in the same month`.
- Total haircut cap: 30%.
- Bad debt: debt minus haircut-adjusted collateral recovery, floored at zero.
- A final-month breach delayed beyond the horizon is not executed, but any actual maturity shortfall remains protocol bad debt.

## Borrower metric

Surviving exposure receives terminal debt erosion `1 - d_12`. Liquidated exposure receives no debt-erosion benefit and loses the collectible 13% penalty, capped by collateral remaining after debt. The metric excludes collateral returns, taxes, conversion spreads, depeg losses, and utility from borrowed funds.

## Scenario generation

- Historical replay: every contiguous 12-month window in 42 joint monthly returns (31 windows).
- Bootstrap: three-month moving blocks sampled with replacement until 12 months.
- Paths: 20,000 per currency–collateral pair.
- Seed: `20260810`.
- FX and crypto returns are paired and remain contiguous inside each block.

## Capital metrics

Reserve breach occurs when portfolio bad debt exceeds 5%, 10%, or 20% of initial debt. The 99% CVaR is the mean loss at or above the empirical 99th percentile. A CVaR-consistent debt ceiling for a USD 10 million reserve is `10,000,000 / CVaR_99`.
