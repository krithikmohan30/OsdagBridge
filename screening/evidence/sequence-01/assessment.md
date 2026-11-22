# Sequence 01 assessment — five consecutive GUI design runs

Environment: Conda `osdagbridge-env`, Python 3.12.16, PySide6 6.12.0, Osdag 2026.04.0.0.
Base revision `d74f56dd7f22925fb8148cabf5740ed8d1e39ff3`; upstream source unmodified.
One GUI process, five designs (A–E), 2026-11-21 22:48:00 → 22:54:44 IST.

## Procedure

- Real desktop GUI; inputs typed with QTest keyboard events; project location chosen through
  the actual location dialog (Chennai, Nungambakkam).
- Between cases the real Unlock button was used and its "Clear Results" confirmation accepted.
- Custom material values were typed in the real material-properties dialog (screenshots saved).
- Save went through the real "Saved OSI Successfully!" dialog to a per-case evidence path.
- Each case captured: UI input dictionaries, backend input, backend output before/after the UI
  completion slot, consumed material properties, widget inventory, design window, plot window
  and extracted plot state, dialogs, saved `.osi`.

## Cases and outcomes

| Case | Change applied | Result | Output leaves differing from A | Notes |
|---|---|---|---|---|
| A-default | 20 m span, 5 m carriageway, 0° skew, E 350A, M40 | PASS | — | 824 top-level output keys; 3D CAD rendered; report PDF generated |
| B-custom-steel | Girder steel typed as Fy 375, Fu 510, E 210, density 78 | PASS (calculation) / FAIL (density not applied) | 12,812 | `Fy`, `Fu`, `E` reach design (fyd 318.18 → 340.91 MPa); density ignored, see finding F1 |
| C-custom-concrete | Deck typed as fck 45, fctm 3.4, Ecm 35 (custom steel from B retained) | PASS | 12,880 | Consumed concrete `fck 45.0 / fctm 3.4 / Ecm 35.0`; report regenerated with custom grades |
| D-span-25 | Span 20 → 25 m | PASS | 20,372 | Saved input and design outputs use 25 m; SW plot summary rises 8.486 → 16.788 kN |
| E-reset-baseline | Grades reset to E 350A / M40, span 20 m | PASS | 1 (report timestamp only) | UI input hash, backend input hash and output values equal A |

Flattened comparison basis: 58,523 scalar leaves per backend output snapshot
(`backend-output-before-ui.json`).

## Determinism of the reset (T13)

`E-reset-baseline/ui-input-before.json` and `A-default/ui-input-before.json` are byte-identical
(SHA-256 prefix `4F79E2B21313E8E8`); `backend-input.json` is identical too (`F307EF6D5319DF78`).
The only difference between the A and E backend outputs is the report generation timestamp in
`design_results.report_text`. Saved `.osi` files are byte-identical (`23F92093AD336D76`).
Conclusion: unlock → edit → design returns the baseline to an identical numeric state after four
different runs, including custom materials and a span change.

## Report/input inconsistency (F2)

The application's design-check report text (from `design_results.report_text`, also in the
report PDF) states `No. of Girders : 5`, while:

- the input dictionary has `typical_section.no_of_girders = 3`;
- the LaTeX report built from the same design states `No. of Girders & 3`
  (`application-report.tex:220` and `:440`);
- `design_results.per_girder` contains `G1…G5` because the two overhang edge grillage lines are
  treated as girders (existing issue #113).

## Warnings and shutdown

- 165 non-fatal `'thermal_load' load case not available` warnings across the five designs
  (33 per design); combinations are created without any TL term. Thermal effects are therefore
  silently absent from every ULS/SLS combination (existing issue #92).
- Process exit code `3221225477` (0xC0000005, access violation) after `app.quit()`, with no
  Python frame and after all five evidence sets were written (`E-reset-baseline/shutdown.json`).
  This is the same class of teardown failure as `baseline-01` (exit 3) and remains unattributed.

## Visualisation observation

The plot window title and selected load case/member match the selection
(`Shear Force Diagram — V_y (kN)`, `SW`, all girders), and the extracted summary matches the
selected member set. The plot canvas is a 3D axes view with no tick labels or numeric axes in
the capture. With identical inputs and identical plot state, A and E render the diagram at
different camera orientations, so the visual state is not reset with the design (low severity;
numeric data is unaffected).

## Video

`workflow.mp4`: 375 s, 1920×1110, H.264, 5 fps, 3.2 MB; records the five-case session.

## Linked evidence

- `session.json`, `cases.json`, `driver.py`
- `A-default/` … `E-reset-baseline/` (inputs, dictionaries, screenshots, `.osi`, reports)
- `../../environment/sequence-01.log`
- Comparison scripts: `../../scripts/compare_outputs.py`, `extract_design_scalars.py`
