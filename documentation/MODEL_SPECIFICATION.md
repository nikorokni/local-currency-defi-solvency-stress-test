# Revised model specification

The normative equations, units and assumptions are in Sections 3–6 of `manuscript/main.tex`. The executable implementation is `analysis/stress_test.py`; the concise event order is in `model_algorithm.tex` and its one-page PDF.

- Initial-principal-normalized, synthetic CR cohorts, independent of principal size.
- Joint FX and crypto returns from monthly averages, not mixed average/end-of-month observations.
- Nominal annual rate divided by 12; no forward return enters the rate rule.
- First strict CR < 1.5 breach in months 1–12 is irreversible.
- Full collateral liquidation after 0/1/2 months; interest continues during delay.
- No new breaches after month 12; all queued sales close by month 14.
- Proceeds go to loan recovery, collectible surplus-only penalty, then the borrower residual.
- All-path credit loss uses initial principal; liquidated-debt loss uses aggregate accrued liquidated debt.
- Borrower outcomes cover survivors and liquidated cohorts, then reconcile to the complete portfolio.
- Gross 10% credit-budget exhaustion and a matched-LCU-funding settlement gap are separate diagnostics.
- Collateral is pledged borrower property, not double-counted as an unencumbered protocol asset.
- No early token redemption, endogenous peg, external recapitalization, operating costs or strategic borrower behavior is simulated.

Parameter provenance is in `parameter_provenance.csv`. Numerical choices and exact input hashes are generated in `results/run_metadata.json`. Outputs supersede the original model at pre-revision commit c1e8ef8; the previous results must not be interpreted using these revised definitions.
