#!/usr/bin/env python3
"""Path-dependent solvency stress test for hypothetical LCU DeFi lending.

All random draws use a documented seed.  Joint monthly FX and crypto returns are
sampled in contiguous blocks, preserving observed within-block dependence.  The
model is deliberately a design stress test, not a forecast of a live protocol.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np
import pandas as pd


SEED = 20260810
HORIZON = 12
N_PATHS = 20_000
BASE_BLOCK = 3
THRESHOLD = 1.50
CR_GRID = np.linspace(1.50, 2.25, 31)


@dataclass(frozen=True)
class Mechanism:
    name: str
    oracle_delay_months: int
    auction_haircut: float
    congestion_slope: float


MECHANISMS = (
    Mechanism("timely", 0, 0.08, 0.20),
    Mechanism("delayed_stress", 1, 0.15, 0.20),
)
RATE_RULES = ("static_20", "adaptive_75", "indexed_100")
RESERVE_RATIOS = (0.05, 0.10, 0.20)


def cr_weights(grid: np.ndarray = CR_GRID) -> np.ndarray:
    """Triangular exposure density on [1.50, 2.25] with mode 1.75."""
    low, mode, high = 1.50, 1.75, 2.25
    density = np.where(
        grid <= mode,
        2.0 * (grid - low) / ((high - low) * (mode - low)),
        2.0 * (high - grid) / ((high - low) * (high - mode)),
    )
    density[0] = max(density[0], 1e-6)
    density[-1] = max(density[-1], 1e-6)
    return density / density.sum()


def moving_block_bootstrap(data: np.ndarray, n_paths: int, horizon: int, block: int, rng: np.random.Generator) -> np.ndarray:
    if data.ndim != 2 or data.shape[1] != 2:
        raise ValueError("Joint-return input must have shape (months, 2)")
    max_start = data.shape[0] - block
    if max_start < 0:
        raise ValueError("Block length exceeds history")
    n_blocks = math.ceil(horizon / block)
    starts = rng.integers(0, max_start + 1, size=(n_paths, n_blocks))
    out = np.empty((n_paths, n_blocks * block, 2), dtype=float)
    for b in range(n_blocks):
        offsets = starts[:, b][:, None] + np.arange(block)[None, :]
        out[:, b * block : (b + 1) * block, :] = data[offsets]
    return out[:, :horizon, :]


def annual_rate_path(fx_depreciation: np.ndarray, rule: str) -> np.ndarray:
    n_paths, horizon = fx_depreciation.shape
    if rule == "static_20":
        return np.full((n_paths, horizon), 0.20)

    annual = np.empty((n_paths, horizon), dtype=float)
    annual[:, 0] = 0.20
    loading = 0.75 if rule == "adaptive_75" else 1.00
    margin = 0.10 if rule == "adaptive_75" else 0.05
    cap = 1.50 if rule == "adaptive_75" else 2.00
    for month in range(1, horizon):
        lookback = fx_depreciation[:, max(0, month - 3) : month]
        trailing_monthly = np.exp(np.mean(np.log1p(np.clip(lookback, -0.95, None)), axis=1)) - 1.0
        trailing_annual = np.maximum((1.0 + trailing_monthly) ** 12 - 1.0, 0.0)
        annual[:, month] = np.clip(margin + loading * trailing_annual, 0.05, cap)
    return annual


def simulate_portfolio(
    joint_returns: np.ndarray,
    rate_rule: str,
    mechanism: Mechanism,
    threshold: float = THRESHOLD,
    grid: np.ndarray = CR_GRID,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, np.ndarray]]:
    fx_ret = joint_returns[:, :, 0]
    crypto_ret = joint_returns[:, :, 1]
    n_paths, horizon = fx_ret.shape
    annual_rates = annual_rate_path(fx_ret, rate_rule)

    fx_factor = np.cumprod(1.0 + fx_ret, axis=1)
    crypto_factor = np.cumprod(1.0 + crypto_ret, axis=1)
    lcu_debt_factor = np.cumprod(1.0 + annual_rates / 12.0, axis=1)
    usd_debt_factor = lcu_debt_factor / fx_factor

    weights = cr_weights(grid)
    ratios = grid[None, :, None] * crypto_factor[:, None, :] / usd_debt_factor[:, None, :]
    breached = ratios < threshold
    any_breach = breached.any(axis=2)
    first_breach = np.where(any_breach, breached.argmax(axis=2), -1)
    execution_month = np.where(any_breach, first_breach + mechanism.oracle_delay_months, -1)
    executable = any_breach & (execution_month < horizon)
    execution_month = np.where(executable, execution_month, -1)

    liquidated_share_by_month = np.zeros((n_paths, horizon), dtype=float)
    for month in range(horizon):
        liquidated_share_by_month[:, month] = (execution_month == month) @ weights

    cohort_bad_debt = np.zeros((n_paths, grid.size), dtype=float)
    cohort_penalty_loss = np.zeros((n_paths, grid.size), dtype=float)
    for j, cr0 in enumerate(grid):
        valid = execution_month[:, j] >= 0
        if not np.any(valid):
            continue
        rows = np.flatnonzero(valid)
        months = execution_month[rows, j]
        share = liquidated_share_by_month[rows, months]
        haircut = np.minimum(0.30, mechanism.auction_haircut + mechanism.congestion_slope * share)
        debt = usd_debt_factor[rows, months]
        collateral = cr0 * crypto_factor[rows, months]
        cohort_bad_debt[rows, j] = np.maximum(debt - collateral * (1.0 - haircut), 0.0)
        # The borrower-side penalty is collectible only from collateral left
        # after covering debt; it is capped at 13% of debt.
        cohort_penalty_loss[rows, j] = np.minimum(0.13 * debt, np.maximum(collateral - debt, 0.0))

    # A delayed breach in the final month cannot be executed inside the
    # 12-month horizon.  Any actual collateral shortfall is nevertheless a
    # protocol loss at maturity and must not disappear from the balance sheet.
    not_executed = execution_month < 0
    terminal_debt = usd_debt_factor[:, -1][:, None]
    terminal_collateral = grid[None, :] * crypto_factor[:, -1][:, None]
    maturity_shortfall = np.maximum(terminal_debt - terminal_collateral, 0.0)
    cohort_bad_debt = np.where(not_executed, maturity_shortfall, cohort_bad_debt)

    liquidated = execution_month >= 0
    portfolio_liquidated_share = liquidated @ weights
    portfolio_bad_debt = cohort_bad_debt @ weights
    portfolio_penalty_loss = cohort_penalty_loss @ weights
    any_liquidation = portfolio_liquidated_share > 0
    surviving_share = 1.0 - portfolio_liquidated_share
    terminal_debt_erosion = 1.0 - usd_debt_factor[:, -1]
    survivor_weighted_erosion = terminal_debt_erosion * surviving_share
    borrower_net_benefit_after_penalty = survivor_weighted_erosion - portfolio_penalty_loss
    terminal_shortfall_share = ((cohort_bad_debt > 0) & not_executed) @ weights

    mean_bad = float(portfolio_bad_debt.mean())
    sd_bad = float(portfolio_bad_debt.std(ddof=1)) if n_paths > 1 else 0.0
    var99 = float(np.quantile(portfolio_bad_debt, 0.99))
    tail = portfolio_bad_debt[portfolio_bad_debt >= var99]
    cvar99 = float(tail.mean()) if tail.size else var99
    p_any = float(any_liquidation.mean())
    p_liq_share = float(portfolio_liquidated_share.mean())
    se_any = math.sqrt(p_any * (1.0 - p_any) / n_paths)

    summary = {
        "rate_rule": rate_rule,
        "mechanism": mechanism.name,
        "paths": n_paths,
        "probability_any_liquidation": p_any,
        "probability_any_liquidation_ci_low": max(0.0, p_any - 1.96 * se_any),
        "probability_any_liquidation_ci_high": min(1.0, p_any + 1.96 * se_any),
        "expected_liquidated_exposure_share": p_liq_share,
        "mean_bad_debt_ratio": mean_bad,
        "mean_bad_debt_ci_low": max(0.0, mean_bad - 1.96 * sd_bad / math.sqrt(n_paths)),
        "mean_bad_debt_ci_high": mean_bad + 1.96 * sd_bad / math.sqrt(n_paths),
        "bad_debt_var_99": var99,
        "bad_debt_cvar_99": cvar99,
        "mean_terminal_debt_erosion_all_paths": float(terminal_debt_erosion.mean()),
        "mean_survivor_weighted_debt_erosion": float(survivor_weighted_erosion.mean()),
        "mean_borrower_net_benefit_after_penalty": float(borrower_net_benefit_after_penalty.mean()),
        "mean_terminal_shortfall_share": float(terminal_shortfall_share.mean()),
        "mean_annual_rate": float(annual_rates.mean()),
        "reserve_breach_5pct": float((portfolio_bad_debt > 0.05).mean()),
        "reserve_breach_10pct": float((portfolio_bad_debt > 0.10).mean()),
        "reserve_breach_20pct": float((portfolio_bad_debt > 0.20).mean()),
        "safe_debt_ceiling_usd_for_10m_reserve": float(10_000_000 / cvar99) if cvar99 > 0 else math.inf,
    }
    summary_frame = pd.DataFrame([summary])

    cohort_rows = []
    for j, cr0 in enumerate(grid):
        cohort_rows.append(
            {
                "initial_collateral_ratio": cr0,
                "exposure_weight": weights[j],
                "liquidation_probability": float(liquidated[:, j].mean()),
                "mean_bad_debt_ratio": float(cohort_bad_debt[:, j].mean()),
            }
        )
    cohort_frame = pd.DataFrame(cohort_rows)
    arrays = {
        "portfolio_bad_debt": portfolio_bad_debt,
        "portfolio_liquidated_share": portfolio_liquidated_share,
        "terminal_debt_erosion": terminal_debt_erosion,
        "usd_debt_factor": usd_debt_factor,
    }
    return summary_frame, cohort_frame, arrays


def replay_windows(data: np.ndarray, rate_rule: str, mechanism: Mechanism) -> pd.DataFrame:
    rows = []
    for start in range(0, data.shape[0] - HORIZON + 1):
        path = data[start : start + HORIZON][None, :, :]
        summary, _, arrays = simulate_portfolio(path, rate_rule, mechanism)
        rows.append(
            {
                "window_start_index": start,
                "liquidated_exposure_share": float(arrays["portfolio_liquidated_share"][0]),
                "bad_debt_ratio": float(arrays["portfolio_bad_debt"][0]),
                "terminal_debt_erosion": float(arrays["terminal_debt_erosion"][0]),
                "mean_annual_rate": float(summary.loc[0, "mean_annual_rate"]),
            }
        )
    return pd.DataFrame(rows)


def market_descriptives(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for currency, fx_col in [("ARS", "ars_depreciation"), ("TRY", "try_depreciation")]:
        for asset, crypto_col in [("ETH", "eth_return"), ("BTC", "btc_return")]:
            subset = panel[[fx_col, crypto_col]].dropna()
            rows.append(
                {
                    "currency": currency,
                    "collateral": asset,
                    "months": len(subset),
                    "mean_monthly_depreciation": subset[fx_col].mean(),
                    "sd_monthly_depreciation": subset[fx_col].std(ddof=1),
                    "mean_monthly_crypto_return": subset[crypto_col].mean(),
                    "sd_monthly_crypto_return": subset[crypto_col].std(ddof=1),
                    "pearson_correlation": subset[fx_col].corr(subset[crypto_col]),
                    "joint_adverse_month_share": ((subset[fx_col] > 0) & (subset[crypto_col] < 0)).mean(),
                }
            )
    return pd.DataFrame(rows)


def make_latex_tables(results: dict[str, pd.DataFrame], table_dir: Path) -> None:
    table_dir.mkdir(parents=True, exist_ok=True)

    desc = results["market_descriptives"].copy()
    lines = ["\\begin{tabular}{llrrrr}", "\\toprule", "Currency & Collateral & Months & FX mean (\\%) & Crypto SD (\\%) & Correlation \\\\", "\\midrule"]
    for row in desc.itertuples(index=False):
        lines.append(f"{row.currency} & {row.collateral} & {row.months} & {100*row.mean_monthly_depreciation:.2f} & {100*row.sd_monthly_crypto_return:.2f} & {row.pearson_correlation:.3f} \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    (table_dir / "table_market_descriptives.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")

    main = results["main_results"].copy()
    focus = main[(main["collateral"] == "ETH") & (main["mechanism"] == "timely")]
    lines = ["\\begin{tabular}{lllrrrr}", "\\toprule", "Currency & Rate rule & Mechanism & Liquidated (\\%) & Bad debt (\\%) & CVaR$_{99}$ (\\%) & Debt erosion (\\%) \\\\", "\\midrule"]
    for row in focus.itertuples(index=False):
        rule = {"static_20":"Static 20\\%", "adaptive_75":"Adaptive 75\\%", "indexed_100":"Indexed 100\\%"}[row.rate_rule]
        lines.append(f"{row.currency} & {rule} & Timely & {100*row.expected_liquidated_exposure_share:.2f} & {100*row.mean_bad_debt_ratio:.2f} & {100*row.bad_debt_cvar_99:.2f} & {100*row.mean_terminal_debt_erosion_all_paths:.2f} \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    (table_dir / "table_main_results.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")

    mech = main[(main["collateral"] == "ETH") & (main["rate_rule"] == "adaptive_75")]
    lines = ["\\begin{tabular}{lllrrrr}", "\\toprule", "Currency & Mechanism & Any liquidation (\\%) & Liquidated exposure (\\%) & Bad debt (\\%) & Reserve breach 10\\% (\\%) & Safe ceiling (USD m) \\\\", "\\midrule"]
    for row in mech.itertuples(index=False):
        name = "Timely" if row.mechanism == "timely" else "One-month delay"
        lines.append(f"{row.currency} & {name} & {100*row.probability_any_liquidation:.2f} & {100*row.expected_liquidated_exposure_share:.2f} & {100*row.mean_bad_debt_ratio:.2f} & {100*row.reserve_breach_10pct:.2f} & {row.safe_debt_ceiling_usd_for_10m_reserve/1e6:.1f} \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    (table_dir / "table_mechanism_comparison.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")

    replay_summary = results["historical_replay_summary"].copy()
    lines = ["\\begin{tabular}{llrrrrl}", "\\toprule", "Currency & Collateral & Mean liquidated (\\%) & Maximum liquidated (\\%) & Mean bad debt (\\%) & Maximum bad debt (\\%) & Worst start \\\\", "\\midrule"]
    for row in replay_summary.itertuples(index=False):
        lines.append(f"{row.currency} & {row.collateral} & {100*row.mean_liquidated_exposure_share:.2f} & {100*row.maximum_liquidated_exposure_share:.2f} & {100*row.mean_bad_debt_ratio:.2f} & {100*row.maximum_bad_debt_ratio:.2f} & {row.worst_bad_debt_window_start} \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    (table_dir / "table_historical_replay.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")

    robustness = results["robustness"].copy()
    lines = ["\\begin{tabular}{llrrrr}", "\\toprule", "Currency & Variation & Value & Liquidated (\\%) & Bad debt (\\%) & CVaR$_{99}$ (\\%) \\\\", "\\midrule"]
    for row in robustness.itertuples(index=False):
        value_label = str(row.value_label).replace("%", "\\%")
        lines.append(f"{row.currency} & {row.parameter.replace('_',' ')} & {value_label} & {100*row.expected_liquidated_exposure_share:.2f} & {100*row.mean_bad_debt_ratio:.2f} & {100*row.bad_debt_cvar_99:.2f} \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    (table_dir / "table_robustness.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot_framework(path: Path) -> None:
    fig, ax = plt.subplots(figsize=(11, 4.4))
    ax.set_xlim(0, 11); ax.set_ylim(0, 4.4); ax.axis("off")
    boxes = [
        (0.3, 1.45, 2.1, 1.5, "Observed inputs", "MakerDAO draws\nFX and crypto paths"),
        (3.0, 1.45, 2.1, 1.5, "Debt engine", "Static or adaptive\nLCU interest rule"),
        (5.7, 1.45, 2.1, 1.5, "Liquidation engine", "Collateral threshold\nDelay and auction haircut"),
        (8.4, 1.45, 2.3, 1.5, "Joint outcomes", "Borrower debt erosion\nBad debt and reserves"),
    ]
    for x, y, w, h, title, subtitle in boxes:
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05", fc="#E8F1F8", ec="#1F4E79", lw=1.5))
        ax.text(x+w/2, y+h*0.66, title, ha="center", va="center", fontsize=11, fontweight="bold", color="#17365D")
        ax.text(x+w/2, y+h*0.30, subtitle, ha="center", va="center", fontsize=9.5, color="#333333")
    for x in [2.45, 5.15, 7.85]:
        ax.add_patch(FancyArrowPatch((x,2.2),(x+0.5,2.2),arrowstyle="-|>",mutation_scale=15,lw=1.6,color="#1F4E79"))
    ax.text(5.5, 3.75, "Path-dependent stress-testing architecture", ha="center", fontsize=14, fontweight="bold")
    ax.text(5.5, 0.65, "Joint monthly blocks preserve observed FX–collateral dependence; all policy parameters remain explicit.", ha="center", fontsize=10)
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def make_figures(panel: pd.DataFrame, results: dict[str, pd.DataFrame], figure_dir: Path) -> None:
    figure_dir.mkdir(parents=True, exist_ok=True)
    mpl.rcParams.update({"font.size": 9.5, "axes.titlesize": 11, "axes.labelsize": 10, "legend.fontsize": 8.5, "figure.dpi": 130})
    plot_framework(figure_dir / "figure1_framework.png")

    p = panel.set_index("month")
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.2), sharex=True)
    series = [("ars_per_usd","ARS per USD"),("try_per_usd","TRY per USD"),("eth_usd","ETH/USD"),("btc_usd","BTC/USD")]
    colors = ["#C44E52", "#DD8452", "#4C72B0", "#55A868"]
    for ax, (col, title), color in zip(axes.flat, series, colors):
        indexed = 100 * p[col] / p[col].iloc[0]
        ax.plot(indexed.index, indexed.values, color=color, lw=2)
        ax.axhline(100, color="#777777", lw=0.8, ls="--")
        ax.set_title(title); ax.set_ylabel("Index (Jan 2020 = 100)"); ax.grid(alpha=0.25)
    fig.suptitle("Observed market paths used for calibration", fontweight="bold")
    fig.tight_layout(); fig.savefig(figure_dir / "figure2_market_paths.png", dpi=300, bbox_inches="tight"); plt.close(fig)

    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.3), sharex=False, sharey=False)
    for ax, currency, asset in [(axes[0,0],"ARS","ETH"),(axes[0,1],"ARS","BTC"),(axes[1,0],"TRY","ETH"),(axes[1,1],"TRY","BTC")]:
        fx = p[f"{currency.lower()}_depreciation"]
        cr = p[f"{asset.lower()}_return"]
        valid = fx.notna() & cr.notna()
        ax.scatter(100*fx[valid], 100*cr[valid], s=27, alpha=0.72, color="#4C72B0", edgecolor="white", linewidth=0.3)
        ax.axhline(0,color="#777",lw=0.7); ax.axvline(0,color="#777",lw=0.7)
        corr = fx[valid].corr(cr[valid])
        ax.set_title(f"{currency} debt / {asset} collateral (r = {corr:.2f})")
        ax.set_xlabel("Monthly LCU depreciation (%)"); ax.set_ylabel("Monthly crypto return (%)"); ax.grid(alpha=0.18)
    fig.suptitle("Joint FX–collateral shocks", fontweight="bold")
    fig.tight_layout(); fig.savefig(figure_dir / "figure3_joint_shocks.png", dpi=300, bbox_inches="tight"); plt.close(fig)

    cohorts = results["cohort_results"]
    fig, axes = plt.subplots(2, 2, figsize=(10.8, 7.4), sharex=True, sharey=True)
    for ax, currency, asset in [(axes[0,0],"ARS","ETH"),(axes[0,1],"ARS","BTC"),(axes[1,0],"TRY","ETH"),(axes[1,1],"TRY","BTC")]:
        sub = cohorts[(cohorts.currency==currency)&(cohorts.collateral==asset)&(cohorts.mechanism=="timely")]
        for rule, label, color in [("static_20","Static 20%","#C44E52"),("adaptive_75","Adaptive 75%","#4C72B0"),("indexed_100","Indexed 100%","#55A868")]:
            s = sub[sub.rate_rule==rule]
            ax.plot(100*s.initial_collateral_ratio, 100*s.liquidation_probability, label=label, lw=2, color=color)
        ax.set_title(f"{currency} / {asset}"); ax.set_xlabel("Initial collateral ratio (%)"); ax.set_ylabel("Liquidation probability (%)"); ax.grid(alpha=0.22)
    axes[0,0].legend(frameon=False)
    fig.suptitle("Liquidation probability by collateral buffer and rate rule", fontweight="bold")
    fig.tight_layout(); fig.savefig(figure_dir / "figure4_liquidation_curves.png", dpi=300, bbox_inches="tight"); plt.close(fig)

    main = results["main_results"]
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.8), sharey=True)
    for ax, currency in zip(axes, ["ARS","TRY"]):
        sub = main[(main.currency==currency)&(main.mechanism=="timely")]
        markers = {"ETH":"o", "BTC":"s"}
        colors = {"static_20":"#C44E52","adaptive_75":"#4C72B0","indexed_100":"#55A868"}
        for row in sub.itertuples(index=False):
            ax.scatter(100*row.mean_bad_debt_ratio, 100*row.mean_survivor_weighted_debt_erosion, s=70, marker=markers[row.collateral], color=colors[row.rate_rule], alpha=0.85)
            ax.annotate(f"{row.collateral}-{row.rate_rule.split('_')[0]}", (100*row.mean_bad_debt_ratio,100*row.mean_survivor_weighted_debt_erosion), xytext=(4,4), textcoords="offset points", fontsize=7.5)
        ax.axhline(0,color="#777",lw=0.8); ax.set_title(currency); ax.set_xlabel("Mean protocol bad debt (% of principal)"); ax.grid(alpha=0.2)
    axes[0].set_ylabel("Survivor-weighted debt erosion (% of principal)")
    fig.suptitle("Borrower–protocol design frontier", fontweight="bold")
    fig.tight_layout(); fig.savefig(figure_dir / "figure5_design_frontier.png", dpi=300, bbox_inches="tight"); plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(10.6, 4.5), sharey=True)
    mech = main[(main.collateral=="ETH")&(main.rate_rule=="adaptive_75")]
    x = np.array(RESERVE_RATIOS)
    for ax, currency in zip(axes,["ARS","TRY"]):
        sub = mech[mech.currency==currency]
        for mechanism,label,color in [("timely","Timely","#4C72B0"),("delayed_stress","Delay + stressed auction","#C44E52")]:
            row = sub[sub.mechanism==mechanism].iloc[0]
            vals = [row.reserve_breach_5pct,row.reserve_breach_10pct,row.reserve_breach_20pct]
            ax.plot(100*x,100*np.array(vals),marker="o",lw=2,label=label,color=color)
        ax.set_title(currency); ax.set_xlabel("Reserve ratio (% of debt)"); ax.grid(alpha=0.22)
    axes[0].set_ylabel("Reserve-breach probability (%)"); axes[0].legend(frameon=False)
    fig.suptitle("Reserve adequacy under liquidation frictions", fontweight="bold")
    fig.tight_layout(); fig.savefig(figure_dir / "figure6_reserve_breach.png", dpi=300, bbox_inches="tight"); plt.close(fig)

    replay = results["historical_replay"]
    fig, axes = plt.subplots(2, 1, figsize=(10.8, 6.5), sharex=True)
    for ax, metric, ylabel in [(axes[0],"liquidated_exposure_share","Liquidated exposure (%)"),(axes[1],"bad_debt_ratio","Bad debt (% of principal)")]:
        for currency,color in [("ARS","#C44E52"),("TRY","#4C72B0")]:
            s = replay[(replay.currency==currency)&(replay.collateral=="ETH")&(replay.rate_rule=="adaptive_75")&(replay.mechanism=="timely")]
            ax.plot(pd.to_datetime(s.window_start),100*s[metric],label=currency,color=color,lw=1.8)
        ax.set_ylabel(ylabel); ax.grid(alpha=0.22)
    axes[0].legend(frameon=False); axes[1].set_xlabel("Start of realised 12-month window")
    fig.suptitle("Historical rolling-window replay", fontweight="bold")
    fig.tight_layout(); fig.savefig(figure_dir / "figure7_historical_replay.png", dpi=300, bbox_inches="tight"); plt.close(fig)

    robust = results["robustness"]
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 5.1), sharey=True)
    for ax,currency in zip(axes,["ARS","TRY"]):
        s=robust[robust.currency==currency].copy()
        labels=(s.parameter+"="+s.value_label).tolist()
        y=np.arange(len(s))
        ax.barh(y,100*s.mean_bad_debt_ratio,color="#4C72B0",alpha=0.82)
        ax.set_yticks(y,labels); ax.invert_yaxis(); ax.set_title(currency); ax.set_xlabel("Mean bad debt (% of principal)"); ax.grid(axis="x",alpha=0.2)
    fig.suptitle("Robustness of protocol loss estimates",fontweight="bold")
    fig.tight_layout(); fig.savefig(figure_dir / "figure8_robustness.png",dpi=300,bbox_inches="tight"); plt.close(fig)


def run(args: argparse.Namespace) -> dict[str, pd.DataFrame]:
    panel = pd.read_csv(args.panel, parse_dates=["month"])
    desc = market_descriptives(panel)
    rng = np.random.default_rng(SEED)
    main_rows, cohort_rows, replay_rows = [], [], []

    pair_data: dict[tuple[str, str], np.ndarray] = {}
    for currency, fx_col in [("ARS","ars_depreciation"),("TRY","try_depreciation")]:
        for asset, cr_col in [("ETH","eth_return"),("BTC","btc_return")]:
            data = panel[[fx_col,cr_col]].dropna().to_numpy(float)
            pair_data[(currency,asset)] = data
            # Common bootstrap draw per currency/asset; policy rules see identical paths.
            paths = moving_block_bootstrap(data, args.paths, HORIZON, args.block_length, rng)
            for rule in RATE_RULES:
                for mechanism in MECHANISMS:
                    summary, cohorts, _ = simulate_portfolio(paths, rule, mechanism)
                    summary.insert(0,"collateral",asset); summary.insert(0,"currency",currency)
                    main_rows.append(summary)
                    cohorts.insert(0,"mechanism",mechanism.name); cohorts.insert(0,"rate_rule",rule)
                    cohorts.insert(0,"collateral",asset); cohorts.insert(0,"currency",currency)
                    cohort_rows.append(cohorts)

                    replay = replay_windows(data, rule, mechanism)
                    dates = panel.loc[panel[[fx_col,cr_col]].notna().all(axis=1),"month"].reset_index(drop=True)
                    replay["window_start"] = [dates.iloc[i].strftime("%Y-%m") for i in replay.window_start_index]
                    replay.insert(0,"mechanism",mechanism.name); replay.insert(0,"rate_rule",rule)
                    replay.insert(0,"collateral",asset); replay.insert(0,"currency",currency)
                    replay_rows.append(replay)

    main = pd.concat(main_rows,ignore_index=True)
    cohorts = pd.concat(cohort_rows,ignore_index=True)
    replay = pd.concat(replay_rows,ignore_index=True)

    replay_focus = replay[(replay["rate_rule"] == "adaptive_75") & (replay["mechanism"] == "timely")].copy()
    replay_summary_rows = []
    for (currency, asset), group in replay_focus.groupby(["currency", "collateral"], sort=True):
        worst = group.loc[group["bad_debt_ratio"].idxmax()]
        replay_summary_rows.append({
            "currency": currency,
            "collateral": asset,
            "realised_windows": int(len(group)),
            "mean_liquidated_exposure_share": float(group["liquidated_exposure_share"].mean()),
            "maximum_liquidated_exposure_share": float(group["liquidated_exposure_share"].max()),
            "mean_bad_debt_ratio": float(group["bad_debt_ratio"].mean()),
            "maximum_bad_debt_ratio": float(group["bad_debt_ratio"].max()),
            "windows_bad_debt_above_10pct": int((group["bad_debt_ratio"] > 0.10).sum()),
            "worst_bad_debt_window_start": worst["window_start"],
        })
    replay_summary = pd.DataFrame(replay_summary_rows)

    robust_rows=[]
    variations=[
        ("block_length","1",1,Mechanism("timely",0,0.08,0.20),THRESHOLD),
        ("block_length","3",3,Mechanism("timely",0,0.08,0.20),THRESHOLD),
        ("block_length","6",6,Mechanism("timely",0,0.08,0.20),THRESHOLD),
        ("auction_haircut","5%",3,Mechanism("custom",0,0.05,0.20),THRESHOLD),
        ("auction_haircut","15%",3,Mechanism("custom",0,0.15,0.20),THRESHOLD),
        ("oracle_delay","1 month",3,Mechanism("custom",1,0.08,0.20),THRESHOLD),
        ("congestion_slope","0%",3,Mechanism("custom",0,0.08,0.00),THRESHOLD),
        ("liquidation_threshold","140%",3,Mechanism("custom",0,0.08,0.20),1.40),
        ("liquidation_threshold","160%",3,Mechanism("custom",0,0.08,0.20),1.60),
    ]
    for currency in ["ARS","TRY"]:
        data=pair_data[(currency,"ETH")]
        for k,(parameter,label,block,mechanism,threshold) in enumerate(variations):
            # Reuse the same base-block draw across one-factor mechanism
            # variations so differences are caused by the parameter, not by
            # Monte Carlo re-sampling.  Alternative block lengths retain their
            # own deterministic draw.
            local_rng=np.random.default_rng(SEED+1000*(1 if currency=="TRY" else 0)+block)
            paths=moving_block_bootstrap(data,args.robustness_paths,HORIZON,block,local_rng)
            summary,_,_=simulate_portfolio(paths,"adaptive_75",mechanism,threshold=threshold)
            row=summary.iloc[0].to_dict(); row.update({"currency":currency,"collateral":"ETH","parameter":parameter,"value_label":label})
            robust_rows.append(row)
    robustness=pd.DataFrame(robust_rows)

    results={"market_descriptives":desc,"main_results":main,"cohort_results":cohorts,"historical_replay":replay,"historical_replay_summary":replay_summary,"robustness":robustness}
    return panel,results


def parse_args() -> argparse.Namespace:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel",type=Path,default=Path("data/processed/joint_monthly_market_panel.csv"))
    parser.add_argument("--results-dir",type=Path,default=Path("results"))
    parser.add_argument("--figure-dir",type=Path,default=Path("figures"))
    parser.add_argument("--table-dir",type=Path,default=Path("tables"))
    parser.add_argument("--paths",type=int,default=N_PATHS)
    parser.add_argument("--robustness-paths",type=int,default=10_000)
    parser.add_argument("--block-length",type=int,default=BASE_BLOCK)
    return parser.parse_args()


def main() -> None:
    args=parse_args(); args.results_dir.mkdir(parents=True,exist_ok=True)
    panel,results=run(args)
    for name,frame in results.items():
        frame.to_csv(args.results_dir/f"{name}.csv",index=False,float_format="%.10g")
    make_latex_tables(results,args.table_dir)
    make_figures(panel,results,args.figure_dir)
    validation={
        "seed":SEED,"bootstrap_paths":args.paths,"robustness_paths":args.robustness_paths,
        "horizon_months":HORIZON,"base_block_length":args.block_length,
        "joint_return_observations":42,"main_result_rows":int(len(results["main_results"])),
        "cohort_result_rows":int(len(results["cohort_results"])),
        "historical_window_rows":int(len(results["historical_replay"])),
        "all_main_values_finite":bool(np.isfinite(results["main_results"].select_dtypes(include=[np.number]).to_numpy()).all()),
        "probabilities_in_unit_interval":bool(((results["main_results"].filter(regex="probability|share|breach")>=0)&(results["main_results"].filter(regex="probability|share|breach")<=1)).all().all()),
    }
    (args.results_dir/"validation_summary.json").write_text(json.dumps(validation,indent=2,sort_keys=True)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
