"""Compare backend output dictionaries across consecutive-run evidence cases.

Reads backend-output-before-ui.json (the worker result snapshotted before the UI
slot mutates it) for each case directory and reports leaf-level differences
against a reference case. No application source is imported or modified.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(value, dict):
        for key, child in value.items():
            out.update(flatten(child, f"{prefix}.{key}" if prefix else str(key)))
    elif isinstance(value, list):
        out[f"{prefix}.__len__"] = len(value)
        for index, child in enumerate(value):
            out.update(flatten(child, f"{prefix}[{index}]"))
    else:
        out[prefix] = value
    return out


def comparable(a: Any, b: Any) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) <= 1e-9 * max(1.0, abs(float(a)), abs(float(b)))
    return a == b


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sequence", required=True, type=Path)
    parser.add_argument("--reference", default="A-default")
    parser.add_argument("--limit", type=int, default=15)
    args = parser.parse_args()

    cases = [p for p in sorted(args.sequence.iterdir()) if p.is_dir()]
    data: dict[str, dict[str, Any]] = {}
    for case in cases:
        path = case / "backend-output-before-ui.json"
        if path.is_file():
            data[case.name] = flatten(json.loads(path.read_text(encoding="utf-8")))

    if args.reference not in data:
        raise SystemExit(f"reference case not found: {args.reference}")

    reference = data[args.reference]
    print(f"reference={args.reference} keys={len(reference)}")
    for name, values in data.items():
        if name == args.reference:
            continue
        diffs = [
            (key, reference[key], values[key])
            for key in reference.keys() & values.keys()
            if not comparable(reference[key], values[key])
        ]
        missing = sorted(reference.keys() - values.keys())
        extra = sorted(values.keys() - reference.keys())
        print(
            f"\n{name}: differing={len(diffs)} missing={len(missing)} extra={len(extra)}"
        )
        for key, old, new in diffs[: args.limit]:
            print(f"  {key}: {old!r} -> {new!r}")
        for key in missing[:5]:
            print(f"  missing key: {key}")
        for key in extra[:5]:
            print(f"  extra key: {key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
