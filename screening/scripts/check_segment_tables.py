"""Compare girder segment tables across consecutive-run evidence cases."""

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


def collect(node, prefix=""):
    if isinstance(node, dict):
        for key, value in node.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, (dict, list)):
                yield from collect(value, path)
            elif "segment" in path.lower():
                yield path, value


def main() -> None:
    for case in CASES:
        data = json.loads(
            (SEQ / case / "backend-output-before-ui.json").read_text(encoding="utf-8")
        )
        rows = list(collect(data))
        print(f"\n== {case}: {len(rows)} segment leaves ==")
        for path, value in rows[:40]:
            print(f"  {path}: {value}")


if __name__ == "__main__":
    main()
