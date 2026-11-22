"""Launch the real desktop window, capture startup evidence, and exit."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
import traceback


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Choose a new output directory to preserve earlier evidence.")
    args.output_dir.mkdir(parents=True)
    result = {
        "started_at": datetime.now().astimezone().isoformat(),
        "scope": "Desktop startup only; no bridge design executed.",
        "python": sys.version,
        "executable": sys.executable,
        "status": "STARTING",
    }

    def save_result() -> None:
        (args.output_dir / "result.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    save_result()
    try:
        # Preserve the upstream entry point's database and DLL initialization.
        import osdagbridge.desktop.__main__ as desktop
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication, QWidget

        desktop._set_windows_app_id()
        app = QApplication([sys.argv[0]])
        stylesheet = desktop.load_stylesheet()
        if stylesheet:
            app.setStyleSheet(stylesheet)
        window = desktop.CustomWindow("OsdagBridge", desktop.PlateGirderBridge)
        window.showMaximized()
        window.show()

        def capture_and_exit() -> None:
            try:
                image = window.screen().grabWindow(int(window.winId()))
                image_path = args.output_dir / "startup-window.png"
                screenshot_ok = not image.isNull() and image.save(str(image_path))
                widgets = [
                    {
                        "class": type(widget).__name__,
                        "name": widget.objectName(),
                        "visible": widget.isVisible(),
                        "enabled": widget.isEnabled(),
                    }
                    for widget in window.findChildren(QWidget)
                    if widget.objectName()
                ]
                (args.output_dir / "named-widgets.json").write_text(
                    json.dumps(widgets, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                result.update(
                    status="PASS" if window.isVisible() and screenshot_ok else "FAIL",
                    window_visible=window.isVisible(),
                    screenshot_saved=screenshot_ok,
                    captured_at=datetime.now().astimezone().isoformat(),
                )
            except Exception:
                result.update(status="FAIL", traceback=traceback.format_exc())
            finally:
                save_result()
                window.close()
                app.quit()

        QTimer.singleShot(5000, capture_and_exit)
        app.exec()
    except Exception:
        result.update(status="FAIL", traceback=traceback.format_exc())
        traceback.print_exc()
        save_result()
    print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
