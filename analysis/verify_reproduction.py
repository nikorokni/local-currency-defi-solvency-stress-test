#!/usr/bin/env python3
"""Check the archived inputs, regenerated outputs and manuscript exhibit links.

Run after ``bash run_all.sh`` from a clean checkout. The reference hashes are
frozen in documentation/reproducibility_manifest.json. PDF byte hashes are
intentionally excluded because the PDF backends record compilation dates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "documentation/reproducibility_manifest.json"
EVENT_SHA256 = "0a9e0f0528345086b3a0f4ece8bb2fddd9080c97f5a0657f27a3549587e132b5"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def check_market_panel() -> None:
    """Independently compute the monthly marks and returns from raw snapshots."""
    fx = []
    for currency, filename in (("ars", "ars_usd_fred.csv"), ("try", "try_usd_fred.csv")):
        raw = pd.read_csv(ROOT / "data/raw_fx" / filename)
        check(len(raw.columns) == 2, f"Unexpected FX columns: {filename}")
        raw.iloc[:, 0] = pd.to_datetime(raw.iloc[:, 0])
        values = pd.to_numeric(raw.iloc[:, 1], errors="raise")
        dates = pd.to_datetime(raw.iloc[:, 0])
        select = dates.between("2020-01-01", "2023-07-31")
        series = pd.Series(values[select].to_numpy(), index=dates[select])
        series.index = series.index.to_period("M").to_timestamp()
        check(not series.index.has_duplicates, f"Duplicate FX months: {filename}")
        fx.append(series.rename(f"{currency}_per_usd"))

    crypto = []
    for asset in ("eth", "btc"):
        raw = pd.read_csv(ROOT / f"data/raw_prices/coinmetrics_{asset}.csv")
        check(list(raw.columns) == ["time", "PriceUSD"], f"Unexpected price columns: {asset}")
        raw["time"] = pd.to_datetime(raw["time"])
        check(len(raw) == 1308, f"Unexpected daily row count: {asset}")
        check(raw["time"].is_unique, f"Duplicate daily marks: {asset}")
        check(raw["time"].min() == pd.Timestamp("2020-01-01") and
              raw["time"].max() == pd.Timestamp("2023-07-31"), f"Wrong price window: {asset}")
        series = raw.set_index("time")["PriceUSD"].resample("MS").mean()
        crypto.append(series.rename(f"{asset}_usd"))

    expected = pd.concat(fx + crypto, axis=1, join="inner").sort_index()
    months = pd.date_range("2020-01-01", "2023-07-01", freq="MS")
    check(expected.index.equals(months) and expected.notna().all().all(),
          "Market panel has missing or extra months")
    for level, ret in (("ars_per_usd", "ars_depreciation"),
                       ("try_per_usd", "try_depreciation"),
                       ("eth_usd", "eth_return"), ("btc_usd", "btc_return")):
        expected[ret] = expected[level].pct_change()

    actual = pd.read_csv(ROOT / "data/processed/joint_monthly_market_panel.csv", parse_dates=["month"])
    check(actual["month"].equals(pd.Series(months, name="month")), "Market-panel dates differ")
    check(list(actual.columns) == ["month", *expected.columns], "Market-panel columns differ")
    np.testing.assert_allclose(actual[expected.columns].to_numpy(dtype=float),
                               expected.to_numpy(dtype=float), rtol=1e-10, atol=1e-10,
                               equal_nan=True)
    check(len(actual) == 43 and actual["eth_return"].notna().sum() == 42,
          "Market-panel observation count differs")


def check_links(manifest: dict) -> None:
    manuscript = (ROOT / "manuscript/main.tex").read_text(encoding="utf-8")
    table_refs = set(re.findall(r"\\input\{\.\./tables/([^}]+)\}", manuscript))
    figure_refs = set(re.findall(r"\\includegraphics\[[^]]*\]\{\.\./figures/([^}]+)\}", manuscript))
    expected_tables = {Path(p).stem for p in manifest["files"] if p.startswith("tables/")}
    expected_figures = {p.removeprefix("figures/") for p in manifest["figures"]}
    check(table_refs == expected_tables,
          f"Table/macro references differ: missing={expected_tables-table_refs}, extra={table_refs-expected_tables}")
    check(figure_refs == expected_figures,
          f"Figure references differ: missing={expected_figures-figure_refs}, extra={figure_refs-expected_figures}")
    for ref in expected_figures:
        check((ROOT / "figures" / ref).is_file(), f"Figure missing: {ref}")
    check((ROOT / "manuscript/main.pdf").is_file(), "Compiled manuscript missing")


def check_makerdao(path: Path) -> None:
    check(sha256(path) == EVENT_SHA256, "MakerDAO event-file checksum differs")
    with tempfile.TemporaryDirectory(prefix="makerdao-audit-") as temp:
        command = [sys.executable, str(ROOT / "analysis/prepare_data.py"),
                   "--makerdao-events", str(path.resolve()), "--output-dir", temp]
        subprocess.run(command, check=True, cwd=ROOT, stdout=subprocess.DEVNULL)
        for name in ("joint_monthly_market_panel.csv", "portfolio_principal_quantiles.csv",
                     "portfolio_principal_summary.json"):
            check(sha256(Path(temp) / name) == sha256(ROOT / "data/processed" / name),
                  f"MakerDAO rebuild differs: {name}")
        metadata = json.loads((Path(temp) / "input_metadata.json").read_text())
        check(metadata["makerdao_events_verified_this_run"] is True and
              metadata["raw_file_sha256"]["external/makerdao_eth_a_draw_events_analysis.csv"] == EVENT_SHA256,
              "MakerDAO metadata does not record verified event input")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--makerdao-events", type=Path,
                        help="Companion repository's event-level ETH-A draw CSV")
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for path, expected_hash in manifest["files"].items():
        actual_path = ROOT / path
        check(actual_path.is_file(), f"Missing archived/generated file: {path}")
        check(sha256(actual_path) == expected_hash, f"SHA-256 mismatch: {path}")
    metadata = json.loads((ROOT / "data/processed/input_metadata.json").read_text())
    for path, expected_hash in metadata["raw_file_sha256"].items():
        if path.startswith("external/"):
            check(expected_hash == EVENT_SHA256, "Incorrect recorded external event checksum")
        else:
            check(sha256(ROOT / path) == expected_hash, f"Input metadata mismatch: {path}")
    check_market_panel()
    check_links(manifest)
    if args.makerdao_events:
        check_makerdao(args.makerdao_events)
    print(f"PASS: {len(manifest['files'])} exact input/data/result/table files; "
          f"43 market levels, 42 joint returns; {len(manifest['figures'])} linked figures" +
          ("; MakerDAO event file and principal derivatives" if args.makerdao_events else ""))
    print("PDF bytes are not compared: embedded creation times vary between builds.")


if __name__ == "__main__":
    main()
