# Sequence 02 assessment — carriageway width change and return

Environment and instrumentation as in `sequence-01`. One GUI process, two designs:
F (carriageway 7 m) then G (back to 5 m), same 20 m span, default grades E 350A / M40.
2026-11-22 13:48:59 → 13:52:19 IST.

| Case | Input after Design | Overall width | Girders (input) | Spacing | Output keys |
|---|---|---|---|---|---|
| F-width-7 | `geometry.carriageway_width = 7` | 7.9 m | 4 | 1.975 m | 1,066 |
| G-width-5 | `geometry.carriageway_width = 5` | 5.9 m | 4 | 1.475 m | 1,066 |

Both designs completed without a worker exception; inputs locked and `.osi` saved.

## Confirmed behavior

- The width edit itself reaches the backend and layout: 7 m produces a 7.9 m overall width with
  four girders at 1.975 m.
- Returning to 5 m produces a 5.9 m overall width but **keeps four girders at 1.475 m** instead of
  re-solving to the fresh-start layout for the same input (three girders at 1.9667 m, as in
  `sequence-01/A-default`, 824 output keys). The result therefore depends on the previously typed
  width, not on the current inputs (existing issues #112 and #220).
- The design-check report again counts grillage lines rather than user girders: it states
  `No. of Girders : 6` for an input of four (finding F2).

## Evidence

- `session.json`, `cases.json`/`../../tests/width-cases.json`, `driver.py`
- `F-width-7/`, `G-width-5/` (backend input/output, UI snapshots, screenshots, `.osi`)
- `../../environment/sequence-02.log`
