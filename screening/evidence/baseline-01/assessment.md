# Baseline 01 assessment

Environment: initial Conda solve, PySide6 6.12.0 (outside the upper bound in
upstream `requirements.txt`). Source revision `d74f56d`; upstream source untouched.

- Span 20 m; carriageway 5 m; skew 0; no median/footpath.
- Location: Tamil Nadu / Chennai (Nungambakkam).
- Steel E 350A for all three exposed steel selectors; concrete M40.
- The GUI-triggered worker completed without a Python exception.
- The real GUI locked its inputs and displayed a populated 3D bridge.
- 824 output dictionary keys were saved before and after the UI completion slot.
- `design-window.png` visibly reports span 20.00 m, overall width 5.90 m,
  girder spacing 1.97 m, and deck thickness 250 mm.
- The saved input and normalized backend dictionary are retained.

## Separate shutdown failure

The process exited with code **3** after the completion evidence was written.
`../../environment/baseline-01.log:3350` contains `Fatal Python error: Aborted`,
with no Python frame. Therefore this is a completed design with an unresolved
shutdown failure, not a clean end-to-end PASS.

The driver called the application's ordinary `close()` and then `app.quit()`.
Its version is saved as `driver.py`. Attribution to application, harness,
Qt, OpenSees, or native CAD teardown has not been established.

Plots were initialized by the completion slot but were not displayed/captured
in this first run. Application report generation was not attempted here.
