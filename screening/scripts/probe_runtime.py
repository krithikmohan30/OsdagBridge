"""Check required imports in isolated subprocesses; does not launch the GUI."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import platform
from pathlib import Path
import shutil
import subprocess
import sys


MODULES = (
    "osdag_core",
    "PySide6.QtWidgets",
    "PySide6.QtWebEngineWidgets",
    "OCC.Core.gp",
    "numpy",
    "scipy",
    "matplotlib",
    "xarray",
    "pydantic",
    "fiona",
    "shapely",
    "openseespy.opensees",
    "ospgrillage",
    "opsvis",
    "ifcopenshell",
    "openpyxl",
    "navcube",
)


def check_import(name: str) -> dict:
    code = (
        "import importlib, json, sys; "
        "m = importlib.import_module(sys.argv[1]); "
        "print(json.dumps({'module_file': getattr(m, '__file__', None), "
        "'version': str(getattr(m, '__version__', 'not exposed'))}))"
    )
    try:
        result = subprocess.run(
            [sys.executable, "-c", code, name],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            check=False,
        )
        return {
            "module": name,
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"module": name, "ok": False, "error": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(
            "Output already exists; choose a new filename to preserve evidence."
        )

    results = []
    for name in MODULES:
        result = check_import(name)
        results.append(result)
        print(f"{'OK' if result['ok'] else 'FAIL'} {name}", flush=True)

    report = {
        "captured_at": datetime.now().astimezone().isoformat(),
        "python": sys.version,
        "executable": sys.executable,
        "prefix": sys.prefix,
        "platform": platform.platform(),
        "imports": results,
        "executables_on_path": {
            name: shutil.which(name) for name in ("pdflatex", "latexmk", "ffmpeg")
        },
        "scope": "Import checks only; GUI, CAD rendering, and design not verified.",
    }
    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    except OSError as exc:
        print(f"Could not save runtime probe: {exc}", file=sys.stderr)
        return 2
    print(f"Saved {args.output}", flush=True)
    return 0 if all(result["ok"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
