"""Regression check for shelf coverage sunburst outer-ring category labels."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.shelf.domain import _build_sunburst_data


def main() -> None:
    df = pd.DataFrame(
        {
            "fragrance_category": [
                "Woody Aromatic",
                "Woody",
                "Oriental",
                "Floral",
                "",
            ]
        }
    )

    data = _build_sunburst_data(df)

    outer_labels = {
        label
        for label, parent in zip(data["labels"], data["parents"])
        if parent and label != "No fragrances"
    }
    expected_outer = {"Woody Aromatic", "Woody", "Oriental", "Floral", "Uncategorized"}
    missing = expected_outer - outer_labels
    assert not missing, f"Missing expected outer labels: {sorted(missing)}"

    forbidden_labels = {"Other Woody", "Other Floral"}
    unexpected = outer_labels & forbidden_labels
    assert not unexpected, f"Found forbidden fallback labels: {sorted(unexpected)}"

    inner_counts: dict[str, int] = {}
    for label, parent, cd in zip(data["labels"], data["parents"], data["customdata"]):
        if parent == "" and not cd.get("is_empty"):
            inner_counts[str(label)] = int(cd.get("count", 0))

    assert inner_counts.get("Woody") == 2, f"Expected Woody count=2, got {inner_counts.get('Woody')}"
    assert inner_counts.get("Oriental") == 1, f"Expected Oriental count=1, got {inner_counts.get('Oriental')}"
    assert inner_counts.get("Floral") == 1, f"Expected Floral count=1, got {inner_counts.get('Floral')}"
    assert inner_counts.get("Other") == 1, f"Expected Other count=1, got {inner_counts.get('Other')}"

    print("Sunburst outer-ring regression check passed.")


if __name__ == "__main__":
    main()
