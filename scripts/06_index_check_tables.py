#!/usr/bin/env python3
"""Index downloaded CHECK cohort tables."""

from __future__ import annotations

import csv
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw" / "CHECK"
META = ROOT / "metadata" / "CHECK"

VISIT_RE = re.compile(r"(?:CHECK_)?T(\d+)|Rontgen.*T(\d+)", re.IGNORECASE)


def infer_visit(filename: str) -> str:
    m = VISIT_RE.search(filename)
    if not m:
        return ""
    return next(g for g in m.groups() if g is not None)


def infer_domain(filename: str) -> str:
    lower = filename.lower()
    if "radiographic" in lower or "rontgen" in lower:
        return "radiographic"
    if "description" in lower or lower.endswith(".pdf"):
        return "documentation"
    return "clinical"


def read_columns(path: Path) -> tuple[int, list[str]]:
    suffix = path.suffix.lower()
    if suffix == ".tab":
        df = pd.read_csv(path, sep="\t", nrows=0, encoding="utf-8")
        n_rows = sum(1 for _ in path.open("rb")) - 1
        return max(n_rows, 0), list(df.columns)
    if suffix == ".dta":
        df = pd.read_stata(path, iterator=False)
        return len(df), list(df.columns)
    return 0, []


def main() -> None:
    META.mkdir(parents=True, exist_ok=True)
    table_rows = []
    variable_rows = []
    files = sorted([p for p in RAW.iterdir() if p.is_file()])

    for path in files:
        suffix = path.suffix.lower()
        n_rows, columns = (0, [])
        if suffix in {".tab", ".dta"}:
            n_rows, columns = read_columns(path)
        row = {
            "relative_path": str(path.relative_to(ROOT)),
            "filename": path.name,
            "extension": suffix,
            "domain": infer_domain(path.name),
            "visit": infer_visit(path.name),
            "size_bytes": path.stat().st_size,
            "n_rows": n_rows,
            "n_cols": len(columns),
            "columns_preview": ";".join(columns[:20]),
        }
        table_rows.append(row)
        for pos, col in enumerate(columns, start=1):
            variable_rows.append(
                {
                    "filename": path.name,
                    "domain": row["domain"],
                    "visit": row["visit"],
                    "position": pos,
                    "variable": col,
                    "variable_lower": col.lower(),
                }
            )

    with (META / "check_table_index.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(table_rows[0].keys()))
        writer.writeheader()
        writer.writerows(table_rows)

    with (META / "check_variable_index.csv").open("w", newline="", encoding="utf-8") as f:
        fieldnames = ["filename", "domain", "visit", "position", "variable", "variable_lower"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(variable_rows)

    print(f"Indexed {len(table_rows)} CHECK files")
    print(f"Indexed {len(variable_rows)} CHECK variables")


if __name__ == "__main__":
    main()
