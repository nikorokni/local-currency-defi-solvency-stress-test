# Revision validation

## Accounting and boundary tests

`python -m unittest discover -s tests -v` checks:

1. Strict threshold equality does not itself trigger liquidation.
2. A month-12 breach remains pending at month 12 and generates a close-out loss.
3. A queued liquidation remains irrevocable if collateral recovers.
4. Debt accrues during the execution delay.
5. Auction proceeds equal debt recovery + collectible penalty + borrower residual, and the independent interest-minus-loss funding bridge equals the capital ledger.
6. Rate rules do not look ahead; partial adjustment respects the monthly move limit.
7. Non-circular block sampling cannot bridge a removed calendar year.
8. Principal-by-CR aggregation is invariant under independent principal weighting.
9. Main and block-three robustness outputs are identical; breach = executed + pending; conditional borrower effects reconcile to the whole portfolio; tail loss is at least mean loss.

These checks verify implementation identities, not empirical model validity or protocol safety. The Gaussian benchmark, subperiods, outer bootstrap and joint parameter grid measure sensitivity rather than validate the assumed auction law.

## Reproducibility

`run_all.sh` rebuilds the aligned panel, full simulations, tests, reporting tables/macros and PDFs. `analysis/build_outputs.py` is the only source of displayed result tables and headline macros. Numerical values in the abstract and prose are therefore shared with the generated reconciliation file, rather than manually rounded independently.

The upstream ETH/BTC price verification independently matched the archived daily extracts and full source hashes at the pinned Coin Metrics commit. MakerDAO principal summaries remain inherited; raw blockchain decoding was not rerun. Full input provenance and verification limits are documented separately.

The 29 September 2026 clean-checkout rebuild and the executable SHA-256/market-panel verifier are documented in `REPRODUCIBILITY_AUDIT.md`. The optional event-level MakerDAO CSV from the companion repository was hash-checked and regenerated the inherited 100 principal bins and summary exactly. This verifies the derivative, not the original blockchain decoder.
