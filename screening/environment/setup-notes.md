# Setup record

Started: 2026-11-21, approximately 14:47 IST.

## Verified

- Host: Windows; commands use PowerShell.
- Existing default Python: 3.13.12 (outside project constraint `>=3.11,<3.13`).
- Git is installed.
- Fork created and verified as a fork of `Nidhikhare12/OsdagBridge`.
- Local path: `C:\Users\krith\OsdagBridge`.
- Branch: `screening/software-testing`, based on fetched `upstream/dev`.
- Base revision: `d74f56dd7f22925fb8148cabf5740ed8d1e39ff3`.

## Miniconda installation

User approved a current-user installation to `C:\Users\krith\miniconda3`.

- Official download: https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe
- Published SHA-256 recorded from the official index:
  `c147ac9b3ec8af9c1f5de8e99f9326064f1af3451fda0dab07f273eccbb74f1c`
- Initial `System.Net.WebClient` download returned HTTP 403.
- Retrying with Windows `curl.exe` and a browser user-agent succeeded.
- Installer invocation verifies SHA-256 and Authenticode before execution.
- Options: `/InstallationType=JustMe /RegisterPython=0 /AddToPath=0 /S`.
- Installation completed successfully; SHA-256 matched and Authenticode was valid
  (Anaconda, Inc.). Installed Conda version: **26.9.4**.
- Initial environment creation started from the unmodified `environment.yml`.
  Output is recorded in `conda-create.log`.
- That attempt stopped with `CondaToSNonInteractiveError` because Conda added
  implicit Anaconda default channels. No terms were accepted on the user's behalf.
- Retry uses `environment.windows.yml`, preserving upstream dependencies and
  the three named channels while adding `nodefaults`. This is a per-environment
  channel-selection change; the upstream manifest is untouched.
- `conda env create` still triggered the defaults-channel terms check before
  honoring that manifest. The next attempt uses Conda 26's supported
  `conda create --file ... --format environment.yml --override-channels`,
  explicitly specifying `osdag`, `geompy`, and `conda-forge` on the command line.
  Output: `conda-create-explicit-channels.log`.
- Explicit-channel installation completed the native Conda transaction, including
  Python 3.12.16, Osdag, pythonOCC, navcube, and Osdag's bundled LaTeX environment.
- Its pip phase failed because the relocated manifest's `-e .` was resolved
  relative to `screening/environment`, not the shell working directory. This was
  introduced by our setup manifest, not an upstream application bug.
- Corrected the manifest to `-e ../..`. For the already-created environment,
  install the pip requirements and editable project from the repository root
  using `conda run ... python -m pip install ... -e .`.
  Output: `pip-install-project.log`.
- The Conda solve selected PySide6 6.12.0 although `requirements.txt` specifies
  `<=6.9.3`. Record this manifest discrepancy; verify startup before choosing a
  compatible pin. Functional tests must identify the actual environment used.

## Baseline readiness

- Editable installation completed successfully: OsdagBridge 1.0.0,
  OpenSeesPy/openseespywin 3.8.0.0, and opsvis 1.3.8.
- `runtime-probe-01.json`: 16 of 17 isolated imports passed. QtWebEngineWidgets
  failed with `ImportError: DLL load failed ... specified module could not be found`.
  The failure also occurs after importing the desktop entry point.
- `../evidence/startup-01/result.json`: actual desktop startup **PASS** at
  2026-11-21 22:37 IST; screenshot and named-widget inventory saved. The CAD
  viewer initialized with Intel UHD Graphics / OpenGL 4.6.
- The active `template_page.py` constructs `MplPlotWidget`, not the WebEngine
  widget in `plots_ui.py`. The failed optional-path import is therefore not
  evidence of a broken active plot view.
- Baseline uses the environment resolved from `environment.yml`, with PySide6
  6.12.0. This is not a `requirements.txt`-conforming environment. Preserve
  `conda-explicit-initial.txt` and `pip-freeze-initial.txt`; any Qt-specific
  functional failure needs a supported-version comparison before attribution.
- Design, plot rendering, and report generation remain unverified at this point.

## GUI evidence instrumentation

- `../scripts/run_gui_case.py` drives the real application with Qt keyboard and
  mouse events for basic fields/design and uses the real location dialog.
- A subclass snapshots the backend immediately before the original completion
  slot runs. It does not change calculation methods or inputs behind the widgets.
- The save-file chooser alone is replaced with an evidence-file path; upstream
  validation/default handling and `.osi` serialization are executed.
- Message boxes are captured before acknowledgment. A completed worker is
  recorded separately from GUI completion and engineering correctness.

## Source observations

- `tests/unit/test_io.py` is a placeholder, not functional validation.
- `examples/plate_girder/example_basic.yaml` is a placeholder.
- `desktop/ui/template_page.py` prints input dictionaries before/after default
  handling and performs design on a worker thread.
- `.osi` save/load uses YAML in the current source.
- The baseline needs actual required span, carriageway, and location inputs.
