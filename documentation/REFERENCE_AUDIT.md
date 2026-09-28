# Reference and provenance audit — 28 September 2026

This audit distinguishes bibliographic verification from empirical validation. Finding a DOI or article does not validate this manuscript's model. No reference was invented to fill a gap.

## Bibliographic checks

| Reference | Verification | Outcome / change |
|---|---|---|
| Schär (2021), 10.20955/r.103.153-74 | Federal Reserve Bank of St. Louis article page | Title and DOI confirmed; Crossref request was rate-limited. |
| Werner et al. (2022), 10.1145/3558535.3559780 | Crossref DOI record | Title, authors, date and pages confirmed. |
| Gudgeon et al. (2020), 10.1145/3419614.3423254 | Crossref DOI record | Metadata confirmed. |
| Saengchote (2023), 10.1016/j.intfin.2023.101807 | Crossref DOI record | Title, author, volume and article number confirmed. |
| Cornelli et al. (2025), 10.1016/j.jfi.2025.101166 | Publisher-indexed ScienceDirect result; BIS author record and working-paper page | 2025 journal article exists, volume 63, article 101166. Direct publisher open failed; Crossref was rate-limited. Working-paper version is BIS 1183 (2024), not substituted as the 2025 publication. |
| Qin et al. (2021), 10.1145/3487552.3487811 | Crossref DOI record | Metadata confirmed. |
| Sasi-Brodesky & Kaousar Nassr (2023), 10.1787/0524faaf-en | Crossref and OECD publication page | Authors, title, number 48 and 31 July 2023 date confirmed. |
| Perez et al., Liquidations: DeFi on a Knife-Edge | Author preprint arXiv:2009.13235 and Springer conference book listing | Identified the real paper; author-preprint URL added. |
| Kjaer et al. (2021), 10.1109/BRAINS52497.2021.9569811 | Crossref DOI record | Title, authors and pages confirmed. |
| Eskandari et al. (2021), 10.1145/3479722.3480994 | Crossref DOI record | Metadata confirmed; Crossref title field abbreviates title to “SoK”. |
| Chaleenutthawut et al. (2024), 10.1109/ACCESS.2024.3363225 | Crossref DOI record | Seven authors, title, volume and pages confirmed. |
| Maker/Sky Vat documentation | Old MakerDAO URL redirects to Sky homepage; followed its Vat link | Updated to actual current core-accounting page. No numerical liquidation parameter is claimed to have been calibrated from this page. |
| Rokni Lamouki & Soofiyan companion package | Current GitHub README via connector | Working-paper title/topic and inherited input role confirmed; not asserted to be a published journal article. |
| Lyons & Viswanath-Natraj (2023), 10.1016/j.jimonfin.2022.102777 | Crossref DOI record | Title, authors, volume and article number confirmed. DOI contains 2022 while journal issue is 2023. |
| Klages-Mundt & Minca (2022), 10.1111/mafi.12357 | Crossref DOI record | Title, authors, volume and pages confirmed. |
| Gorton & Zhang (2023), Taming Wildcat Stablecoins | University of Chicago Law Review publication and volume 90.3 pages | Identified actual publication; no DOI added without evidence. |
| BIS Papers 138 (2023) | BIS publication page | **Corrected erroneous title and attribution.** Correct title: *Financial stability risks from cryptoassets in emerging market economies*. Report by the Consultative Group of Directors of Financial Stability. |
| Copestake et al. (2023), 10.5089/9798400258367.063 | Crossref DOI record | Title and four authors confirmed. |
| Aldasoro, Beltrán & Grinberg (2026), BIS WP 1340 | BIS publication page and PDF; IMF parallel version | Real 2026 paper, published 27 March 2026. Retained; no invented DOI. |
| FRED ARS / TRY series | Official series pages | Monthly average-of-daily-rates convention confirmed. Historical archive retained. |
| Coin Metrics archive | Public repository and pinned raw files | Both full upstream hashes and all 1,308 daily rows in each local extract independently matched. |
| Künsch (1989), 10.1214/aos/1176347265 | Crossref DOI record | Title, author, volume and year confirmed. |

Raw Crossref responses reduced to relevant metadata are in `reference_metadata_audit.json`. Failures are retained rather than relabelled as successful queries. Source-page/metadata checks occurred on 28 September 2026; the repository's original 8 August 2026 acquisition dates are inherited provenance, not a new acquisition claim.

## Primary verification URLs

- https://www.stlouisfed.org/publications/review/2021/02/05/decentralized-finance-on-blockchain-and-smart-contract-based-financial-markets
- https://www.sciencedirect.com/science/article/abs/pii/S1042957325000348
- https://www.bis.org/publications/working-paper-1183-why-defi-lending-evidence-aave-v2
- https://www.oecd.org/en/publications/defi-liquidations_0524faaf-en.html
- https://arxiv.org/abs/2009.13235
- https://developers.skyeco.com/protocol/core/vat/
- https://lawreview.uchicago.edu/print-archive/taming-wildcat-stablecoins
- https://www.bis.org/publ/bppdf/bispap138.htm
- https://www.bis.org/publ/work1340.htm
- https://fred.stlouisfed.org/series/ARGCCUSMA02STM
- https://fred.stlouisfed.org/series/CCUSMA02TRM618N
- https://github.com/coinmetrics/data
- https://github.com/nikorokni/inflation-driven-debt-erosion-defi

## Scope and authorship

The uploaded review PDF lists Amin Karami as an additional author, whereas GitHub commit `c1e8ef839bc91c3830f6c08b45a10183c68125ba` explicitly updated authorship and lists Niko Rokni Lamouki and Salma Soofiyan. This revision preserves that current repository author list; it does not independently decide authorship eligibility.

The major-revision comments supplied in this turn concern the second (credit-loss/solvency) paper. The first paper's repository is consulted for provenance only and is not modified without its own revision comments.
