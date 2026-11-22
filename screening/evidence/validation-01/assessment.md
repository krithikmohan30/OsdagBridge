# Validation 01 assessment — per-field validator vs `.osi` load validator

Direct API comparison on the baseline configuration (no GUI interaction, no structural design).
Base revision `d74f56dd…`; Conda `osdagbridge-env`. Captured 2026-11-22 13:37 IST.

Method: for each key/value pair, the per-field validator
(`BridgeInputValidator.validate_material_inputs` / `validate_additional_inputs`) was called
directly, then the full baseline `.osi` was loaded, mutated, and passed to
`OsiInputValidator.validate()`. Expected validity comes from the documented ranges.

Baseline `.osi` validates cleanly (no errors, no warnings, no corrections).

## Results (18 comparisons, 6 deviations)

| Case | Key = value | Per-field | OSI load | Verdict |
|---|---|---|---|---|
| span-below | `geometry.span = 19.9` | reject (corrects 20.0) | reject | consistent |
| span-min / span-max | 20 / 45 | accept | accept | consistent |
| span-above | 45.1 | reject | reject | consistent |
| skew-min / skew-max / skew-above | −15 / 15 / 15.1 | accept / accept / reject | same | consistent |
| **deck-min** | `typical_section.deck_thickness = 100` | **accept** | **reject** | **inconsistent** |
| deck-max | 500 | accept | accept | consistent |
| deck-below | 99 | reject | reject (plus stud error) | consistent |
| steel-fy-min / max | 100 / 1200 | accept | accept | consistent |
| **steel-fy-above** | `material.girder.fy = 1201` | **reject** | **accept** | **inconsistent** |
| **steel-e-below** | `material.girder.e = 99` | **reject** | **accept** | **inconsistent** |
| **concrete-fck-below** | `material.deck.fck = 9` | **reject** | **accept** | **inconsistent** |
| concrete-fck-max | 80 | accept | accept | consistent |
| **cross-bracing-fy-above** | `material.cross_bracing.fy = 1201` | **accept** | **accept** | both miss the documented 100–1200 MPa range |
| **end-diaphragm-fy-above** | `material.end_diaphragm.fy = 1201` | **accept** | **accept** | both miss the documented 100–1200 MPa range |

## Findings

### V1 — `.osi` load accepts out-of-range girder and deck materials
`OsiInputValidator` only iterates `_BASIC_KEYS` and `_ADDITIONAL_KEYS`
(`core/utils/osi_validator.py:89`, `:142`, `:150`); no `material.*` key is present in either list,
so out-of-range custom steel or concrete values pass load-time validation even though the same
values are rejected when typed in the dialog (`validator.py:78–138`). Matches existing issue #96.
Suggested fix: add the material keys to `_ADDITIONAL_KEYS` and route them through
`validate_material_inputs`, or validate all present `material.*` keys explicitly.

### V2 — cross-bracing and end-diaphragm material ranges are not checked anywhere
`validate_material_inputs` only recognises girder and deck keys (`validator.py:78–138`), and the
`.osi` validator does not cover them either, so `material.cross_bracing.fy = 1201` and
`material.end_diaphragm.fy = 1201` are accepted by both paths. Matches existing issue #129.
Suggested fix: validate the transverse-member keys with the same steel ranges, mapping them to
the girder field set.

### V3 — deck thickness 100 mm: entry accepts, load rejects
With the default 80 mm stud height, deck thickness 100 mm leaves a 75 mm maximum stud height, so
the stud cross-check (`validator.py:817–828`) fails. The per-field deck check
(`validator.py:213`) accepts 100 mm, and the message prints inverted bounds
(“between 80 mm … and 75 mm”). This is a validation-layer inconsistency, not a design failure.
Suggested fix: reject the deck/stud combination at the deck field, or clamp the default stud
height to `min(80, deck_thickness − 25)`, and emit a coherent message when `max_h < min_h`.

## Evidence

- `results.json` — all 18 comparisons with raw responses
- `*.osi` — mutated inputs retained only for the six deviating cases
- Script: `../../scripts/probe_validation.py`
