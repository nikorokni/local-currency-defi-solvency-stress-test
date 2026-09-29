---
title: Response to the major-revision comments
author: Niko Rokni Lamouki, corresponding author
date: 28 September 2026
geometry: margin=24mm
fontsize: 10pt
---

Dear Salma,

I am sending you the point-by-point revision record. I have revised the model, rerun the analysis, and rewritten the manuscript to make the claims correspond to what the data and simulations can support. In particular, I now distinguish contractual credit loss from the broader question of protocol solvency. I have responded to each point below and provided the revised manuscript, code, generated results, model algorithm, parameter table, and numerical reconciliation.

# 1. Title

**Comment:** Shorten the title and use “protocol solvency” only if the model includes a sufficiently complete balance sheet.

**Response:** I have changed the title to “Local-Currency DeFi Lending under Joint FX and Crypto Shocks: A Path-Dependent Credit-Loss Stress Test.” Credit loss after collateral recovery is the primary quantity I estimate. I have added an explicit, restricted funding ledger in Section 3, but I do not present it as a complete model of protocol solvency or token redemption.

# 2. Abstract

**Comment:** Reduce the numerical detail, identify observed inputs and assumptions, mention the 42 monthly returns, and qualify the trilemma claim.

**Response:** I have limited the abstract to the principal liquidation, mean-loss, and tail-loss results. It now distinguishes observed market returns from the assumed collateral distribution, auction parameters, rate rules, and funding arrangement. I state the 42-return sample size and describe the policy result as a trade-off within the tested design space. I have also corrected the typesetting and regenerated its numbers directly from the results files.

# 3. Introduction

**Comment:** Introduce the balance sheet and redemption promise, identify the primary estimand and unit of analysis, and narrow the contribution claims.

**Response:** I have introduced the illustrative LCU loan asset, matching LCU funding liability, pledged crypto collateral, and equity-funded USD reserves near the beginning of Section 1. The assumed token is redeemable for one unit of local currency at loan settlement, not for one USD. I explain who absorbs a shortfall and where the model leaves an unfunded gap. I now define the estimand as contractual credit loss after collateral recovery, normalized by initial USD principal, across simulated portfolio paths. I have replaced the claim of a “complete stress test” and reduced repetition in the conclusion.

# 4. Related literature and research gap

**Comment:** Make the review more analytical, explain the selection of studies, distinguish this paper from its companion paper, and verify references.

**Response:** I have reorganized Section 2 around what prior lending, liquidation, stablecoin, and emerging-market FX studies establish and what each leaves outside the present model. The research-gap table is labelled as a selection of representative studies for specific mechanisms, not a survey of each entire field.

I have identified the data, event definitions, and FX-translation identity reused from the companion working paper. The joint FX–crypto paths, monthly breach and close-out rules, auction accounting, funding diagnostic, and new sensitivity results belong to this study. The MakerDAO principal summaries are inherited; I have not claimed to have decoded the raw transactions again for this revision.

I checked the recent references and DOI metadata against publisher or institutional records where available. I corrected a substantive error in the BIS Papers 138 citation: its title is *Financial stability risks from cryptoassets in emerging market economies*, attributed to the Consultative Group of Directors of Financial Stability. I also updated the Maker/Sky accounting-documentation link. The accompanying reference audit records the checks and the sources I could not independently confirm in full.

# 5. System architecture and balance-sheet logic

**Comment:** Add a balance sheet and notation table; separate credit loss, FX translation, liabilities, peg shortfall, and insolvency; write the borrower measure and monthly algorithm explicitly.

**Response:** I have added both tables in Section 3. The balance sheet treats pledged collateral as borrower property rather than counting it again as an unencumbered protocol asset. The equations distinguish the translated LCU loan claim from the translated funding principal, loan recovery from credit loss, and the credit-budget indicator from a restricted accounting gap. Peg deviations, early redemption, and comprehensive insolvency remain outside this model and are labelled accordingly.

I have written an explicit financing-side net debt effect for every cohort, including positions that are liquidated. The revised event order appears in Section 5 and in the separate one-page algorithm. I checked the debt, recovery, penalty, borrower-residual, and funding-ledger identities with executable tests.

# 6. Data and reproducible construction

**Comment:** Clarify what the 130,742 MakerDAO draws do in a homogeneous model, run a weighting ablation, explain the 100-by-31 construction, align market observations, and discuss official versus executable FX.

**Response:** I now state that the MakerDAO draw sizes illustrate principal scale and concentration. With the assumed independence of loan size and starting collateral ratio, the 100 principal bins and 31 collateral-ratio points form 3,100 product-weighted cells. The ablation compares MakerDAO principal weights, equal principal-bin weights, and a normalized unit over the same collateral-ratio weights. Their percentage results coincide to numerical precision. I also test the literal “one dollar at each collateral-ratio point” interpretation; that changes the collateral distribution to uniform, so I report its effect separately.

I have reconstructed the main market panel with monthly averages for both the official FX rates and the daily crypto prices. The original mixed measurement is retained only as a labelled sensitivity comparison; its results differ materially from the aligned analysis. I independently matched the archived ETH and BTC daily extracts to the pinned Coin Metrics sources. I discuss why official FX, especially for Argentina, cannot automatically be treated as an executable or parallel-market conversion rate. I have not substituted an unobserved parallel-rate series.

# 7. Stress-test design

**Comment:** Specify the bootstrap and rate initialization, acknowledge the short sample, and examine data, model, and parameter uncertainty.

**Response:** I specify non-circular moving blocks, eligible full-block starting points, truncation of the final sampled block, and the 20% initial annual rate. Each subsequent rate uses only prior simulated FX returns, with an expanding history until its stated lookback is available. All baseline policy comparisons use the same simulated paths, extended to 14 months for scheduled close-out.

I have added block lengths 1, 3, and 6; leave-one-year-out and early/late subperiod analyses; an IID bivariate Gaussian log-return benchmark; and an outer block-resampling exercise with 100 calibrations and 2,000 inner paths each. Blocks cannot cross a removed calendar year. I report the resulting ranges as descriptive sensitivity, not confidence intervals with validated coverage. The 20,000 baseline paths reduce simulation noise but do not add economic observations to the 42-return calibration. I separate observed inputs, external sources, inherited accounting conventions, illustrative parameters, and numerical simulation settings in the provenance materials.

**Remaining boundary:** I have not assembled a defensible longer joint market series within this revision. I report subperiod sensitivity rather than treating simulated paths as a substitute for additional history. The Gaussian comparison is not a fitted copula or a regime model.

# 8. Rate rules

**Comment:** Diagnose very high applied rates, test less aggressive rules, and avoid claiming a universal trilemma.

**Response:** I now report the mean, median, 90th and 99th percentiles, maximum, cap frequency, and mean and median absolute monthly changes for each currency. The applied-rate diagnostics weight months by the initial-principal exposure still outstanding under the timely ETH scenario; rates after a position settles are excluded. I also retain unweighted posted-rate means and medians in the machine-generated file.

I have tested a rule with up to twelve trailing months of history, a lower 60% cap, and partial adjustment capped at a five-percentage-point monthly change. Since a newly simulated path has fewer than twelve earlier observations in its first year, I describe the expanding initialization explicitly. These rule coefficients are assumptions, not estimated optimal parameters. I have not introduced a forward-looking proxy without a supporting forecast or market series. I have recast the apparent trilemma as a conditional comparison among the policies actually tested.

# 9. Collateral, liquidation, and reserves

**Comment:** Define breach and settlement precisely, address last-month censoring, and distinguish breaches, executed sales, pending sales, and losses.

**Response:** I define breach as strictly CR < 1.5. The first breach queues an irrevocable full-collateral sale, including if prices subsequently recover. Debt continues accruing during the execution delay. Sale proceeds cover debt first; a penalty of up to 13% of accrued debt is collected only from any remaining proceeds, with the rest returned to the borrower. The penalty cannot create recovery in excess of debt.

Every breach registered in months 1–12 now receives its scheduled settlement by month 14. The outputs separately show breached exposure, sales executed by month 12, pending exposure, pending undercollateralized exposure and debt, and credit losses after close-out. I compare timely auctions with delay-only, haircut-only, and combined delayed-stressed auctions, so delay is not conflated with a larger haircut. A deterministic test confirms that a final-month breach and its loss are not dropped.

# 10. Results and denominators

**Comment:** Define each portfolio and borrower outcome, and avoid interpreting “any liquidation” as a borrower probability.

**Response:** I define the path-level probability of any cohort liquidation separately from the initial-exposure share liquidated and from individual cohort probabilities. I report credit loss both per initial principal and per aggregate accrued debt of liquidated positions. I calculate financing-side outcomes for survivors, liquidated positions, and the complete ex ante portfolio with stated denominators; a test checks their weighted reconciliation.

I have replaced the broad label “borrower benefit” with “financing-side net debt effect.” The revised measure includes settlement costs for liquidated positions. I specify that it is neither investment profit nor borrower welfare, since collateral returns, taxes, conversion costs, peg deviations, utility, and different holding periods remain outside its scope.

# 11. Robustness and sensitivity

**Comment:** Vary haircut, congestion, execution delay, and initial collateral ratios jointly, including alternative collateral distributions.

**Response:** I have run a 108-cell joint grid per currency for the adaptive ETH scenario: three base haircuts, three congestion slopes, three delays, and four starting collateral distributions. The distributions include uniform ratios, greater concentration near the threshold, and larger buffers. Each cell uses the same 5,000 paths within a currency. I present the full grid as two heat maps and summarize its loss ranges. Some combinations produce substantially greater losses, so I do not claim that one numerical headline survives all assumptions. The grid represents scenario sensitivity, not estimated probabilities for the parameter combinations.

# 12. Protocol-design implications

**Comment:** Separate model-supported conclusions from recommendations about untested mechanisms.

**Response:** I tie the design discussion to the simulated effects of rate rules, auction assumptions, and funding accounting. I identify diversified auction participation, circuit breakers, and backstop liquidity as possibilities requiring separate tests; this model does not establish their efficacy. I have removed claims about a universally safe debt ceiling and a general impossibility result.

# 13. Limitations

**Comment:** Correct analytically tractable issues rather than leaving them solely in the limitations section.

**Response:** I have corrected the market-data measurement mismatch and the end-of-horizon close-out treatment, made rate initialization explicit, added alternative collateral distributions, and examined parameter and input sensitivity. The limitations section now concentrates on unresolved constraints: monthly rather than executable intramonth prices, official rather than accessible FX, the short history, assumed auction and borrower behavior, early redemption, and other obligations that a real protocol would face.

# 14. Conclusion

**Comment:** Shorten the conclusion and bound the contribution to results supported by the revisions.

**Response:** I have shortened the conclusion and updated it with numbers from the revised analysis. It describes a reproducible counterfactual credit-loss framework. I do not infer the viability, solvency, or safety of an implemented local-currency protocol.

# 15. Tables, figures, and numerical consistency

**Comment:** Repair typography and exhibit sizes; standardize denominators and rounding; reconcile reserve percentages, the block-three results, and the combined delay/haircut label.

**Response:** I have rebuilt the clean manuscript in a readable single-column format, enlarged the figures, revised captions to define denominators, and defined CVaR at first use. Tables display consistently rounded percentages. The earlier 10.96/10.97 and 15.02/15.03 discrepancies are superseded by recalculated values; shared generated macros supply the revised abstract and narrative. The block-three robustness row reuses exactly the baseline simulated paths, and a test checks equality. I call the combined case a “delayed stressed auction” and report delay-only and haircut-only cases independently.

# Additional request for Salma: complete reproducibility package

**Comment:** The revised manuscript makes reproducibility claims and reports simulations. For Salma's assessment, the repository, data, generated CSVs and code must be supplied so that every table and figure can be regenerated and the MakerDAO, FX and crypto inputs checked against the manuscript.

**Response:** I agree that the manuscript needs an auditable package. I have supplied the full repository with archived FX and daily crypto CSVs, the processed monthly panel, all machine-generated simulation CSVs, model and input-preparation code, the table/figure builder, tests, LaTeX source and compiled manuscript. `documentation/REPRODUCIBILITY_AUDIT.md` maps each generated table and figure to its immediate CSV source and records the exact source-series IDs, upstream links, measurement convention and limitations. `documentation/reproducibility_manifest.json` freezes SHA-256 values for 34 input/data/result/table files. From a separate clean checkout I ran `bash run_all.sh`: all 34 of those files matched byte for byte, the manuscript retained 18 pages with identical extracted text, all four figures had identical raster renders, and the unit tests passed. The PDF backends embed new timestamps, so PDF byte hashes are not a meaningful equality test. I added `analysis/verify_reproduction.py` so this check, including an independent monthly-panel calculation and every exhibit reference, can be repeated with a single command after the build.

The MakerDAO event-level CSV is linked at a pinned commit of the companion repository, with SHA-256 `0a9e0f0528345086b3a0f4ece8bb2fddd9080c97f5a0657f27a3549587e132b5`. I verified that file and rebuilt the 100 principal-bin CSV and summary JSON with exact matching hashes. The original blockchain archive decoding was not rerun here; I have made that boundary explicit. The FX snapshots are identified as official OECD/FRED monthly averages; all 43 analysis-window values in each series matched the current FRED source tables. ETH/BTC snapshots are Coin Metrics daily `PriceUSD` marks averaged by month. This verifies the archived-input transformation, not executable FX or intramonth liquidation prices. The model's collateral ratios, auction frictions and funding architecture remain assumed scenarios, not empirically estimated protocol parameters. I do not treat reproducibility alone as validation of those assumptions or as a guarantee of journal approval.

**Salma's verification command:** `bash run_all.sh && python analysis/verify_reproduction.py`. For the optional MakerDAO derivative check, add `--makerdao-events /path/to/makerdao_eth_a_draw_events_analysis.csv` to the verifier command.

# Materials supplied

1. Clean revised manuscript and LaTeX source: `manuscript/main.pdf` and `manuscript/main.tex`.
2. This point-by-point response in PDF and editable Markdown.
3. Revised executable code, tests, and machine-generated results: `analysis/`, `tests/`, and `results/`.
4. One-page monthly algorithm: `documentation/model_algorithm.pdf`.
5. Parameter-provenance table: manuscript Section 4 and `documentation/parameter_provenance.csv`.
6. Headline-number reconciliation: manuscript appendix and `results/headline_reconciliation.csv`.
7. Input/output hash manifest, clean-checkout audit, per-exhibit source map and executable verifier: `documentation/reproducibility_manifest.json`, `documentation/REPRODUCIBILITY_AUDIT.md`, `analysis/verify_reproduction.py`.

I have kept the remaining data and modelling boundaries explicit in the manuscript so the revised findings can be assessed on their actual evidence.

Sincerely,

Niko Rokni Lamouki

Corresponding author
