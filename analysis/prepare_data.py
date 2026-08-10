#!/usr/bin/env python3
"""Prepare auditable monthly stress-test inputs.

The script never edits raw files.  It converts official OECD/FRED exchange-rate
levels and Coin Metrics daily reference prices into a common monthly panel.  If
the first paper's event-level MakerDAO draw file is supplied, it also rebuilds
the principal calibration used to describe the synthetic portfolio.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


START = pd.Timestamp("2020-01-01")
END = pd.Timestamp("2023-07-31")
EXPECTED_MAKERDAO_EVENT_SHA256 = "0a9e0f0528345086b3a0f4ece8bb2fddd9080c97f5a0657f27a3549587e132b5"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_fx(path: Path, output_name: str) -> pd.Series:
    frame = pd.read_csv(path)
    if frame.shape[1] != 2:
        raise ValueError(f"Expected two columns in {path}; found {frame.shape[1]}")
    date_col, value_col = frame.columns
    frame[date_col] = pd.to_datetime(frame[date_col], errors="raise")
    frame[value_col] = pd.to_numeric(frame[value_col], errors="coerce")
    frame = frame.loc[frame[date_col].between(START, END)].copy()
    series = frame.set_index(date_col)[value_col].sort_index()
    series.index = series.index.to_period("M").to_timestamp()
    series.name = output_name
    return series


def read_coinmetrics_monthly(path: Path, output_name: str) -> pd.Series:
    frame = pd.read_csv(path, usecols=["time", "PriceUSD"])
    frame["time"] = pd.to_datetime(frame["time"], errors="raise")
    frame["PriceUSD"] = pd.to_numeric(frame["PriceUSD"], errors="coerce")
    frame = frame.loc[frame["time"].between(START, END) & frame["PriceUSD"].notna()].copy()
    # Last available daily reference price in each calendar month.
    series = frame.set_index("time")["PriceUSD"].sort_index().resample("MS").last()
    series.name = output_name
    return series


def build_panel(args: argparse.Namespace) -> pd.DataFrame:
    levels = pd.concat(
        [
            read_fx(args.ars_fx, "ars_per_usd"),
            read_fx(args.try_fx, "try_per_usd"),
            read_coinmetrics_monthly(args.eth_prices, "eth_usd"),
            read_coinmetrics_monthly(args.btc_prices, "btc_usd"),
        ],
        axis=1,
        join="inner",
    ).sort_index()
    expected = pd.date_range("2020-01-01", "2023-07-01", freq="MS")
    if not levels.index.equals(expected):
        missing = expected.difference(levels.index)
        raise ValueError(f"Monthly panel is incomplete; missing {missing.tolist()}")

    panel = levels.copy()
    panel["ars_depreciation"] = panel["ars_per_usd"].pct_change()
    panel["try_depreciation"] = panel["try_per_usd"].pct_change()
    panel["eth_return"] = panel["eth_usd"].pct_change()
    panel["btc_return"] = panel["btc_usd"].pct_change()
    panel.index.name = "month"
    return panel.reset_index()


def build_principal_calibration(events_path: Path) -> tuple[pd.DataFrame, dict[str, float]]:
    events = pd.read_csv(events_path, usecols=["borrowed_dai"])
    principal = pd.to_numeric(events["borrowed_dai"], errors="coerce")
    principal = principal[np.isfinite(principal) & (principal >= 1.0)]
    if len(principal) != 130_742:
        raise ValueError(f"Expected 130,742 eligible draws; found {len(principal):,}")

    ranked = principal.sort_values().reset_index(drop=True)
    bins = pd.qcut(ranked.rank(method="first"), q=100, labels=False)
    calibration = (
        pd.DataFrame({"principal_usd": ranked, "quantile_bin": bins})
        .groupby("quantile_bin", as_index=False)
        .agg(event_count=("principal_usd", "size"), mean_principal_usd=("principal_usd", "mean"),
             total_principal_usd=("principal_usd", "sum"), min_principal_usd=("principal_usd", "min"),
             max_principal_usd=("principal_usd", "max"))
    )
    calibration["event_weight"] = calibration["event_count"] / calibration["event_count"].sum()
    calibration["exposure_weight"] = calibration["total_principal_usd"] / calibration["total_principal_usd"].sum()

    summary = {
        "event_count": int(principal.size),
        "total_principal_usd": float(principal.sum()),
        "mean_principal_usd": float(principal.mean()),
        "median_principal_usd": float(principal.median()),
        "p10_principal_usd": float(principal.quantile(0.10)),
        "p90_principal_usd": float(principal.quantile(0.90)),
        "p99_principal_usd": float(principal.quantile(0.99)),
        "maximum_principal_usd": float(principal.max()),
    }
    return calibration, summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ars-fx", type=Path, default=Path("data/raw_fx/ars_usd_fred.csv"))
    parser.add_argument("--try-fx", type=Path, default=Path("data/raw_fx/try_usd_fred.csv"))
    parser.add_argument("--eth-prices", type=Path, default=Path("data/raw_prices/coinmetrics_eth.csv"))
    parser.add_argument("--btc-prices", type=Path, default=Path("data/raw_prices/coinmetrics_btc.csv"))
    parser.add_argument("--makerdao-events", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    panel = build_panel(args)
    panel.to_csv(args.output_dir / "joint_monthly_market_panel.csv", index=False, float_format="%.12g")

    checksums = {
        str(path): sha256(path)
        for path in [args.ars_fx, args.try_fx, args.eth_prices, args.btc_prices]
    }
    checksums["external/makerdao_eth_a_draw_events_analysis.csv"] = EXPECTED_MAKERDAO_EVENT_SHA256

    if args.makerdao_events is not None:
        event_checksum = sha256(args.makerdao_events)
        if event_checksum != EXPECTED_MAKERDAO_EVENT_SHA256:
            raise ValueError(
                "MakerDAO event file checksum does not match the documented companion dataset: "
                f"{event_checksum}"
            )
        calibration, summary = build_principal_calibration(args.makerdao_events)
        calibration.to_csv(args.output_dir / "portfolio_principal_quantiles.csv", index=False, float_format="%.12g")
        (args.output_dir / "portfolio_principal_summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        checksums["external/makerdao_eth_a_draw_events_analysis.csv"] = event_checksum

    metadata = {
        "analysis_window": ["2020-01", "2023-07"],
        "monthly_level_observations": int(len(panel)),
        "joint_return_observations": int(panel[["ars_depreciation", "try_depreciation", "eth_return", "btc_return"]].dropna().shape[0]),
        "raw_file_sha256": checksums,
        "coinmetrics_repository_commit": "f1a36afb962731c387bb03982758ab0103063da5",
        "makerdao_source_repository_commit": "6f6710982391b88f48a3dc7bb5bbfecc7691a47f",
    }
    (args.output_dir / "input_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
