#!/usr/bin/env python3
"""Index downloaded OAI ASCII tables and surface candidate variables.

This script reads only table headers and line counts from raw OAI downloads,
then writes metadata files used for the variable-selection stage.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_OAI = ROOT / "raw" / "OAI"
META_OAI = ROOT / "metadata" / "OAI"


DELIMITERS = ["|", "\t", ",", ";"]

VISIT_RE = re.compile(r"(?<!\d)(?:V)?(\d{2})(?!\d)", re.IGNORECASE)

KEYWORD_GROUPS = {
    "id_side": [
        "id",
        "side",
        "knee",
        "barcd",
        "barcode",
        "visit",
        "version",
    ],
    "pain_function": [
        "womac",
        "koos",
        "pain",
        "symptom",
        "function",
        "stiff",
        "wk",
        "koosk",
        "wom",
    ],
    "imaging_xray": [
        "kl",
        "kellgren",
        "jsn",
        "oarsi",
        "osteo",
        "xray",
        "joint",
        "space",
        "align",
        "fta",
        "jsw",
        "osteophyte",
    ],
    "outcome_tka_kr": [
        "tka",
        "thr",
        "replace",
        "replacement",
        "arthro",
        "kr",
        "outcome",
        "death",
    ],
    "medication": [
        "med",
        "drug",
        "nsaid",
        "analgesic",
        "mif",
        "rx",
        "ingname",
    ],
    "surgery_injury": [
        "surg",
        "inj",
        "arthrosc",
        "menisc",
        "ligament",
        "trauma",
        "acl",
    ],
    "demographics_bmi": [
        "age",
        "sex",
        "gender",
        "race",
        "ethnic",
        "bmi",
        "height",
        "weight",
        "income",
        "educ",
    ],
}


def detect_delimiter(header: str) -> str:
    counts = {delimiter: header.count(delimiter) for delimiter in DELIMITERS}
    return max(counts, key=counts.get)


def clean_header(raw_header: str) -> str:
    return raw_header.lstrip("\ufeff").rstrip("\r\n")


def read_header(path: Path) -> tuple[str, list[str]]:
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        header = clean_header(handle.readline())
    delimiter = detect_delimiter(header)
    columns = next(csv.reader([header], delimiter=delimiter))
    columns = [column.strip() for column in columns]
    return delimiter, columns


def count_data_rows(path: Path) -> int:
    with path.open("rb") as handle:
        line_count = sum(1 for _ in handle)
    return max(line_count - 1, 0)


def infer_visit_code(filename: str, columns: list[str]) -> str:
    candidates = [filename, *columns[:20]]
    for candidate in candidates:
        match = VISIT_RE.search(candidate)
        if match:
            return match.group(1)
    return ""


def infer_domain(path: Path, columns: list[str]) -> str:
    text = " ".join(
        [
            path.name.lower(),
            path.parent.name.lower(),
            path.parts[-3].lower() if len(path.parts) >= 3 else "",
            " ".join(column.lower() for column in columns[:80]),
        ]
    )
    if "x-ray" in text or "xray" in text or "kxr" in text or "jsw" in text:
        return "imaging_xray"
    if "mif" in text or "medication" in text:
        return "medication"
    if "outcome" in text:
        return "outcome"
    if "clinical" in text or "womac" in text or "koos" in text:
        return "clinical"
    if "subject" in text or "enrollees" in text:
        return "demographics"
    return "other"


def package_for(path: Path) -> str:
    relative = path.relative_to(RAW_OAI)
    return relative.parts[0]


def keyword_groups_for(variable: str, table_name: str, domain: str) -> list[str]:
    haystack = f"{variable} {table_name} {domain}".lower()
    groups = []
    for group, keywords in KEYWORD_GROUPS.items():
        if any(keyword in haystack for keyword in keywords):
            groups.append(group)
    return groups


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    table_rows: list[dict[str, object]] = []
    variable_rows: list[dict[str, object]] = []
    candidate_rows: list[dict[str, object]] = []

    data_files = sorted(
        [
            path
            for path in RAW_OAI.rglob("*")
            if path.is_file() and path.suffix.lower() in {".txt", ".csv"}
        ]
    )

    for path in data_files:
        delimiter, columns = read_header(path)
        relative_path = path.relative_to(ROOT)
        table_name = path.stem
        domain = infer_domain(path, columns)
        visit_code = infer_visit_code(table_name, columns)
        id_vars = [column for column in columns if column.upper() in {"ID", "SIDE", "VERSION"}]

        table_rows.append(
            {
                "package": package_for(path),
                "domain": domain,
                "relative_path": str(relative_path),
                "filename": path.name,
                "table_name": table_name,
                "extension": path.suffix.lower(),
                "delimiter": "\\t" if delimiter == "\t" else delimiter,
                "visit_code": visit_code,
                "n_rows": count_data_rows(path),
                "n_cols": len(columns),
                "id_variables": ";".join(id_vars),
                "columns_preview": ";".join(columns[:20]),
            }
        )

        for position, variable in enumerate(columns, start=1):
            base_row = {
                "package": package_for(path),
                "domain": domain,
                "relative_path": str(relative_path),
                "table_name": table_name,
                "visit_code": visit_code,
                "position": position,
                "variable": variable,
                "variable_lower": variable.lower(),
            }
            variable_rows.append(base_row)

            groups = keyword_groups_for(variable, table_name, domain)
            if groups:
                candidate_rows.append({**base_row, "candidate_groups": ";".join(groups)})

    write_csv(
        META_OAI / "oai_table_index.csv",
        table_rows,
        [
            "package",
            "domain",
            "relative_path",
            "filename",
            "table_name",
            "extension",
            "delimiter",
            "visit_code",
            "n_rows",
            "n_cols",
            "id_variables",
            "columns_preview",
        ],
    )
    write_csv(
        META_OAI / "oai_variable_index.csv",
        variable_rows,
        [
            "package",
            "domain",
            "relative_path",
            "table_name",
            "visit_code",
            "position",
            "variable",
            "variable_lower",
        ],
    )
    write_csv(
        META_OAI / "oai_candidate_variables.csv",
        candidate_rows,
        [
            "package",
            "domain",
            "relative_path",
            "table_name",
            "visit_code",
            "position",
            "variable",
            "variable_lower",
            "candidate_groups",
        ],
    )

    print(f"Indexed {len(table_rows)} OAI tables")
    print(f"Indexed {len(variable_rows)} OAI variables")
    print(f"Flagged {len(candidate_rows)} candidate variable-table rows")
    print(f"Wrote outputs to {META_OAI}")


if __name__ == "__main__":
    main()
