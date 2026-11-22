# Confirmed findings and existing-issue mapping

Base revision `d74f56dd7f22925fb8148cabf5740ed8d1e39ff3`. All findings below were reproduced
with the real desktop GUI or with the shipped validation API; no upstream source was modified.
Existing issues were re-checked on 22 November 2026 before proposing any independent report.

## Publication status

Evidence was added as comments on the existing issues; no new issue was opened.

| Finding | Issue | Comment |
|---|---|---|
| F1 | #20 | https://github.com/Nidhikhare12/OsdagBridge/issues/20#issuecomment-7076669657 |
| F2 | #113 | https://github.com/Nidhikhare12/OsdagBridge/issues/113#issuecomment-7076669945 |
| F3 | #92 | https://github.com/Nidhikhare12/OsdagBridge/issues/92#issuecomment-7076670193 |
| F4 | #112 | https://github.com/Nidhikhare12/OsdagBridge/issues/112#issuecomment-7076670432 |
| V1 | #96 | https://github.com/Nidhikhare12/OsdagBridge/issues/96#issuecomment-7076670718 |
| V2 | #129 | https://github.com/Nidhikhare12/OsdagBridge/issues/129#issuecomment-7076671035 |

V3 has no existing duplicate and remains documented in this report only.

## F1 — Custom girder unit weight is ignored

- **Reproduction**: case B of `evidence/sequence-01`. Girder steel typed as Fy 375 MPa,
  Fu 510 MPa, E 210 GPa, density 78 kN/m³.
- **Observed**: `consumed-material-properties.json` shows `Fy = 375e6`, `Fu = 510e6`,
  `E = 210e9`, but `rho = 78500` — identical to the default E 350A case A, whose density input
  was 76.4 kN/m³. The SW shear summary is consequently identical between A and B
  (`G1 8.486 kN`, `G2 6.739 kN`), although self-weight should change with density.
- **Cause**: `_build_material_props()` reads `material.girder.e/.fy/.fu/.poisson` for custom
  grades but not `material.girder.density`; it falls back to the constant `78500.0`
  (`src/osdagbridge/core/bridge_types/plate_girder/plategirderbridge.py:1192–1194`).
- **Suggested fix**: read `KEY_MATERIAL_GIRDER_DENSITY` when the grade is not in the database and
  convert kN/m³ → N/m³ (`float(raw_density) * 1000.0`), keeping the current fallback.
- **Existing issue**: [#20](https://github.com/Nidhikhare12/OsdagBridge/issues/20) — same defect;
  this run adds GUI-driven evidence and the SW-invariance proof.

## F2 — Design-check report states the wrong girder count

- **Reproduction**: case A of `evidence/sequence-01`; input `typical_section.no_of_girders = 3`
  (20 m span, 5 m carriageway, 0° skew). Also reproduced in `sequence-02`: input 4 girders,
  report says 6.
- **Observed**: `design_results.report_text` (also printed in the report PDF) states
  `No. of Girders : 5`, while the LaTeX report generated from the same design states 3
  (`application-report.tex:220`, `:440`) and `design_results.per_girder` contains G1–G5.
- **Cause**: the report config uses `n_girders = geom.n_l` (`designer.py:401`, stored at `:434`),
  which counts the two overhang edge grillage lines; the code itself notes at `:410–413` that
  `_girder_count()` excludes those edge beams.
- **Suggested fix**: populate `GeometryConfig.n_girders` from `bridge._girder_count()` for the
  report, or relabel the line as "grillage lines" and report the user's girder count separately.
- **Existing issue**: [#113](https://github.com/Nidhikhare12/OsdagBridge/issues/113) — deck-edge
  lines designed as girders; this run adds the user-visible report contradiction.

## F3 — Thermal load never enters ULS/SLS combinations

- **Reproduction**: every design in `evidence/sequence-01`; 165 warnings in
  `environment/sequence-01.log` (33 per design), e.g.
  `BASIC_2: 'thermal_load' load case not available — create it before calling create_uls_combinations()`.
- **Observed**: all generated combinations contain DL/DW/LL/WL terms only; no TL term appears in
  any combination name or in the analysed load cases, so thermal effects are silently absent.
- **Cause**: the design pipeline creates LL, DL+LL, ULS and SLS combinations
  (`plategirderbridge.py:630–644`) but never calls `create_temperature_load()`
  (`analyser.py:905`); the combination builder warns and skips the missing case
  (`analyser.py:2376–2385`).
- **Suggested fix**: create the temperature load inside `_stage_load_combinations()` with the
  canonical temperature inputs before building ULS/SLS, or gate TL terms out when the case is
  not configured and suppress the per-combination warning.
- **Existing issue**: [#92](https://github.com/Nidhikhare12/OsdagBridge/issues/92).

## F4 — Girder layout is not re-solved when the carriageway width is edited back

- **Reproduction**: `evidence/sequence-02`, one GUI session: design at carriageway 7 m, unlock,
  design at carriageway 5 m (span 20 m, default grades).
- **Observed**: after returning to 5 m the backend keeps four girders at 1.475 m (1,066 output
  keys), whereas a fresh session with the same 5 m input gives three girders at 1.9667 m
  (824 keys, `sequence-01/A-default`). The 7 m design itself is consistent (overall 7.9 m,
  four girders at 1.975 m).
- **Suggested fix**: recompute the girder layout (count, spacing, overhang) from the current
  carriageway width on every width edit instead of reusing the previous layout.
- **Existing issues**: [#112](https://github.com/Nidhikhare12/OsdagBridge/issues/112) (count
  depends on the first width typed) and [#220](https://github.com/Nidhikhare12/OsdagBridge/pull/220)
  (pending fix to re-seed the count); this run adds a GUI-driven before/after reproduction.

## V1 — `.osi` load accepts out-of-range girder/deck materials

- `material.girder.fy = 1201`, `material.girder.e = 99`, `material.deck.fck = 9` are rejected by
  the dialog-level validator but accepted by `OsiInputValidator`
  (`core/utils/osi_validator.py:89–111`, `:142–157`).
- Existing issue: [#96](https://github.com/Nidhikhare12/OsdagBridge/issues/96).

## V2 — Cross-bracing/end-diaphragm material ranges unchecked

- `material.cross_bracing.fy = 1201` and `material.end_diaphragm.fy = 1201` pass both the
  per-field validator and the `.osi` validator.
- Existing issue: [#129](https://github.com/Nidhikhare12/OsdagBridge/issues/129).

## V3 — Deck 100 mm: entry accepts, load rejects; inverted bound message

- Deck thickness 100 mm is accepted by the per-field deck check (`validator.py:213`) but the
  `.osi` load fails on the default 80 mm stud height, because `max_h = 100 − 25 = 75 mm` is below
  `min_h = 4 × 20 = 80 mm`; the message then reads “between 80 mm … and 75 mm”
  (`validator.py:817–828`).
- No exact duplicate found; this is a validation-layer inconsistency worth a short new issue with
  the two `.osi`/API paths as evidence.

## Observations not filed as defects

- Shutdown access violation `3221225477` after `app.quit()` (no Python frame) in both baseline
  and sequence sessions; attribution not established.
- Plot camera orientation is not reset between runs with identical data; numeric plot state and
  titles are correct.
- PySide6 6.12.0 resolves outside `requirements.txt` (`<=6.9.3`); `QtWebEngineWidgets` fails to
  import but is unused by the active `MplPlotWidget` GUI.
