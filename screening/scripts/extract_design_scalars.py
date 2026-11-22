"""Extract comparable design scalars from consecutive-run backend snapshots."""

from __future__ import annotations

import json
from pathlib import Path

SEQ = Path(__file__).resolve().parents[1] / "evidence" / "sequence-01"
CASES = [
    "A-default",
    "B-custom-steel",
    "C-custom-concrete",
    "D-span-25",
    "E-reset-baseline",
]

PATTERNS = [
    "overall_depth",
    "web_thickness",
    "flange_width",
    "flange_thickness",
    "girder_spacing",
    "no_of_girders",
    "span",
    "fy",
    "fck",
]


def walk(node, prefix=""):
    if isinstance(node, dict):
        for key, value in node.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, (dict, list)):
                yield from walk(value, path)
            else:
                yield path, value


def main() -> None:
    for case in CASES:
        path = SEQ / case / "backend-output-before-ui.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        print(f"\n== {case} ==")
        for path_, value in walk(data):
            low = path_.lower()
            if any(token in low for token in PATTERNS) and isinstance(
                value, (int, float, str)
            ):
                print(f"  {path_}: {value}")
        state = SEQ / case / "plot-state.json"
        if state.is_file():
            print("  plot:", json.loads(state.read_text(encoding="utf-8"))["summary"])


if __name__ == "__main__":
    main()
