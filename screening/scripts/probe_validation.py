"""Compare interactive per-field validators with OSI load-time validation."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if not args.baseline.is_file():
        parser.error("Baseline file does not exist.")
    if args.output_dir.exists():
        parser.error("Use a new evidence directory.")
    import yaml
    from osdagbridge.core.bridge_types.plate_girder.validator import (
        BridgeInputValidator,
    )
    from osdagbridge.core.utils.osi_validator import validate_osi_inputs

    baseline = yaml.safe_load(args.baseline.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True)
    validator = BridgeInputValidator()
    # Expected bounds are read from validator.py and common.py, not inferred from outcomes.
    cases = [
        ("span-below", "basic", "geometry.span", 19.9, False),
        ("span-min", "basic", "geometry.span", 20, True),
        ("span-max", "basic", "geometry.span", 45, True),
        ("span-above", "basic", "geometry.span", 45.1, False),
        ("skew-min", "basic", "geometry.skew_angle", -15, True),
        ("skew-max", "basic", "geometry.skew_angle", 15, True),
        ("skew-above", "basic", "geometry.skew_angle", 15.1, False),
        ("deck-min", "additional", "typical_section.deck_thickness", 100, True),
        ("deck-max", "additional", "typical_section.deck_thickness", 500, True),
        ("deck-below", "additional", "typical_section.deck_thickness", 99, False),
        ("steel-fy-min", "material", "material.girder.fy", 100, True),
        ("steel-fy-max", "material", "material.girder.fy", 1200, True),
        ("steel-fy-above", "material", "material.girder.fy", 1201, False),
        ("steel-e-below", "material", "material.girder.e", 99, False),
        ("concrete-fck-below", "material", "material.deck.fck", 9, False),
        ("concrete-fck-max", "material", "material.deck.fck", 80, True),
        (
            "cross-bracing-fy-above",
            "material",
            "material.cross_bracing.fy",
            1201,
            False,
        ),
        (
            "end-diaphragm-fy-above",
            "material",
            "material.end_diaphragm.fy",
            1201,
            False,
        ),
    ]
    results = []
    for name, category, key, value, expected_valid in cases:
        data = dict(baseline)
        data[key] = value
        per_field = getattr(validator, f"validate_{category}_inputs")(key, data)
        osi = validate_osi_inputs(data)
        observed_field_valid = per_field is None
        results.append(
            {
                "case": name,
                "key": key,
                "value": value,
                "expected_valid": expected_valid,
                "per_field_valid": observed_field_valid,
                "per_field_response": per_field,
                "osi": asdict(osi),
                "per_field_matches_expectation": observed_field_valid == expected_valid,
                "osi_matches_expectation": osi.is_valid == expected_valid,
            }
        )
        if observed_field_valid != expected_valid or osi.is_valid != expected_valid:
            (args.output_dir / f"{name}.osi").write_text(
                yaml.safe_dump(data, sort_keys=True),
                encoding="utf-8",
            )
    report = {
        "captured_at": datetime.now().astimezone().isoformat(),
        "scope": "Direct validation API checks; no UI interaction or structural design.",
        "python": sys.version,
        "baseline_validation": asdict(validate_osi_inputs(baseline)),
        "results": results,
    }
    (args.output_dir / "results.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    mismatches = [
        r
        for r in results
        if not (r["per_field_matches_expectation"] and r["osi_matches_expectation"])
    ]
    print(
        f"Executed {len(results)} validation comparisons; {len(mismatches)} mismatched expected rules."
    )
    for row in mismatches:
        print(
            f"{row['case']}: per-field valid={row['per_field_valid']}; OSI valid={row['osi']['is_valid']}"
        )
    print(f"Evidence: {args.output_dir / 'results.json'}")
    # A diagnostic finding is data, not failure of the evidence script itself.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
