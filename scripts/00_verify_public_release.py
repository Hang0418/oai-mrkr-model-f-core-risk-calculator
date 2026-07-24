#!/usr/bin/env python3
"""Validate the manuscript-aligned public release without restricted data."""

from __future__ import annotations

import csv
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    main_figures = list((ROOT / "assets/figures/main").glob("*.png"))
    supplementary_figures = list((ROOT / "assets/figures/supplementary").glob("*.png"))
    require(len(main_figures) == 5, f"Expected 5 main PNG figures, found {len(main_figures)}")
    require(len(supplementary_figures) == 10, f"Expected 10 supplementary PNG figures, found {len(supplementary_figures)}")

    for png in main_figures + supplementary_figures:
        for extension in (".pdf", ".svg"):
            require(png.with_suffix(extension).exists(), f"Missing {png.with_suffix(extension)}")

    manifest = ROOT / "data/tables/table_manifest.csv"
    with manifest.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    main_groups = {row["table"] for row in rows if row["section"] == "main"}
    supplementary_groups = {row["table"] for row in rows if row["section"] == "supplementary"}
    require(main_groups == {"1", "2", "3", "4"}, f"Unexpected main table groups: {main_groups}")
    require(supplementary_groups == {f"s{i}" for i in range(1, 18)}, "Supplementary table groups must be S1-S17")
    for row in rows:
        require((ROOT / "data/tables" / row["section"] / row["file"]).exists(), f"Missing table file: {row['file']}")

    html = (ROOT / "index.html").read_text(encoding="utf-8")
    for exact in (
        "0.00164077477256476",
        "0.0705638786413772",
        "0.681400186474898",
        "Model version: F-core v1.0",
    ):
        require(exact in html, f"Calculator is missing expected value: {exact}")

    prohibited_extensions = {".docx", ".xlsx", ".rds", ".dta", ".sav"}
    for path in ROOT.rglob("*"):
        if ".git" in path.parts or not path.is_file():
            continue
        require(path.suffix.lower() not in prohibited_extensions, f"Restricted/build artifact present: {path}")
    require(not any(ROOT.rglob("strict_reviewer_recalibration_offset_audit_metrics.csv")), "Superseded offset audit must not be released")
    print("Public release verification passed.")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
