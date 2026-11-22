"""Drive one real Qt design case and preserve its evidence without source edits.

Instrumentation: subclass the completion slot to snapshot the worker result before
the upstream slot updates the GUI; auto-dismiss recorded message boxes; replace
only the save-file chooser with a deterministic evidence path. Basic inputs use
QTest keyboard events and the real project-location dialog.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from datetime import datetime
import json
from pathlib import Path
import sys
import traceback
from unittest.mock import patch


def json_default(value):
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "tolist"):
        return value.tolist()
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return {"type": type(value).__name__, "repr": repr(value)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--span", default="20")
    parser.add_argument("--width", default="5")
    parser.add_argument("--timeout-seconds", type=int, default=1200)
    args = parser.parse_args()
    out = args.output_dir.resolve()
    if out.exists():
        parser.error("Choose a new output directory; existing evidence is preserved.")
    out.mkdir(parents=True)

    def write(name, data):
        (out / name).write_text(
            json.dumps(data, indent=2, ensure_ascii=False, default=json_default) + "\n",
            encoding="utf-8",
        )

    result = {
        "started_at": datetime.now().astimezone().isoformat(),
        "status": "STARTING",
        "scope": "GUI-driven design; engineering correctness requires reconciliation.",
        "requested": {
            "span_m": args.span,
            "carriageway_m": args.width,
            "skew_deg": "0",
        },
        "python": sys.version,
        "instrumentation": __doc__,
        "dialogs": [],
    }
    write("result.json", result)
    import osdagbridge.desktop.__main__ as desktop
    from PySide6 import __version__ as qt_binding_version
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QLabel,
        QLineEdit,
        QPushButton,
        QWidget,
    )
    from osdagbridge.desktop.ui.dialogs.custom_messagebox import CustomMessageBox
    from osdagbridge.desktop.ui.dialogs.project_location import ProjectLocationDialog

    result["pyside6"] = qt_binding_version
    app = QApplication([sys.argv[0]])
    app.setStyleSheet(desktop.load_stylesheet())
    desktop._set_windows_app_id()

    def screenshot(widget, name):
        pixmap = widget.screen().grabWindow(int(widget.winId()))
        if pixmap.isNull() or not pixmap.save(str(out / name)):
            raise RuntimeError(f"Screenshot failed: {name}")

    def widget_values(root):
        values = []
        for widget in root.findChildren(QWidget):
            if not widget.objectName():
                continue
            item = {
                "class": type(widget).__name__,
                "name": widget.objectName(),
                "visible": widget.isVisible(),
                "enabled": widget.isEnabled(),
            }
            if isinstance(widget, QComboBox):
                item["value"] = widget.currentText()
                item["options"] = [widget.itemText(i) for i in range(widget.count())]
            elif isinstance(widget, (QLineEdit, QLabel)):
                item["value"] = widget.text()
            values.append(item)
        return values

    class EvidenceWindow(desktop.CustomWindow):
        def _on_design_done(self, exc_obj, err_trace, cancelled):
            result.update(
                worker_exception=repr(exc_obj) if exc_obj else None,
                worker_traceback=err_trace,
                cancelled=cancelled,
                worker_finished_at=datetime.now().astimezone().isoformat(),
            )
            write("backend-input.json", self.backend.input_dict)
            write("backend-output-before-ui.json", self.backend.output_dict)
            write("result.json", result)
            try:
                super()._on_design_done(exc_obj, err_trace, cancelled)
            except Exception:
                result["completion_slot_traceback"] = traceback.format_exc()
            QTimer.singleShot(2000, finish)

    window = EvidenceWindow("OsdagBridge", desktop.PlateGirderBridge)
    window.showMaximized()
    seen_dialogs = set()

    def handle_dialogs():
        for dialog in app.topLevelWidgets():
            if not isinstance(dialog, CustomMessageBox) or not dialog.isVisible():
                continue
            identity = id(dialog)
            if identity in seen_dialogs:
                continue
            seen_dialogs.add(identity)
            index = len(result["dialogs"]) + 1
            texts = [w.text() for w in dialog.findChildren(QLabel) if w.text()]
            result["dialogs"].append(
                {"texts": texts, "screenshot": f"dialog-{index:02d}.png"}
            )
            screenshot(dialog, f"dialog-{index:02d}.png")
            write("result.json", result)
            # Acknowledge informational/error messages, never confirm destructive actions.
            buttons = dialog.findChildren(QPushButton)
            safe = next(
                (b for b in buttons if b.text().strip() in ("OK", "Ok", "Close")), None
            )
            if safe:
                safe.click()
            else:
                dialog.reject()

    dialog_timer = QTimer()
    dialog_timer.timeout.connect(handle_dialogs)
    dialog_timer.start(300)

    def fail():
        result.update(status="HARNESS ERROR", harness_traceback=traceback.format_exc())
        write("result.json", result)
        traceback.print_exc()
        if not getattr(window, "_design_running", False):
            window.close()
            app.quit()

    def finish():
        try:
            write("ui-input-after.json", window.input_dict)
            write("backend-output-after-ui.json", window.backend.output_dict)
            write("widgets-after.json", widget_values(window))
            screenshot(window, "design-window.png")
            result["input_locked"] = window.input_dock.is_locked
            result["output_key_count"] = len(window.backend.output_dict)
            result["plot_widget_class"] = type(window.plots_widget).__name__
            result["status"] = (
                "DESIGN COMPLETED"
                if not result.get("worker_exception")
                and not result.get("completion_slot_traceback")
                and not result.get("cancelled")
                and window.input_dock.is_locked
                and len(window.backend.output_dict) > 0
                else "DESIGN FAILED"
            )
            result["finished_at"] = datetime.now().astimezone().isoformat()
            write("result.json", result)
        except Exception:
            fail()
        finally:
            print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)
            window.close()
            app.quit()

    def set_text(key, value):
        widget = window.input_dock.input_widget.findChild(QLineEdit, key)
        if widget is None:
            raise LookupError(f"Missing input widget: {key}")
        window.input_dock.scroll_area.ensureWidgetVisible(widget)
        widget.setFocus()
        widget.selectAll()
        QTest.keyClicks(widget, value)
        QTest.keyClick(widget, Qt.Key_Tab)
        if widget.text() != value:
            raise ValueError(f"{key}: requested {value!r}, displayed {widget.text()!r}")

    def set_location():
        try:
            dialog = next(
                w
                for w in app.topLevelWidgets()
                if isinstance(w, ProjectLocationDialog) and w.isVisible()
            )
            dialog.method_radio_location.setChecked(True)
            for combo, value in (
                (dialog.state_combo, "Tamil Nadu"),
                (dialog.district_combo, "Chennai (Nungambakkam)"),
            ):
                index = combo.findText(value)
                if index < 0:
                    raise ValueError(f"Location option not found: {value}")
                combo.setCurrentIndex(index)
            write("location-selection.json", dialog.get_selected_location())
            screenshot(dialog, "location-selection.png")
            dialog.findChild(QPushButton, "primary").click()
        except Exception:
            fail()

    def begin():
        try:
            set_text("geometry.span", args.span)
            set_text("geometry.carriageway_width", args.width)
            set_text("geometry.skew_angle", "0")
            QTimer.singleShot(500, set_location)
            window.input_dock.show_project_location_dialog()
            if not window.input_dict.get("project.location"):
                raise RuntimeError("Location was not saved.")
            window.input_dock.scroll_area.verticalScrollBar().setValue(0)
            screenshot(window, "inputs-window.png")
            # Only substitute path selection; use upstream validation and serialization.
            with patch(
                "osdagbridge.desktop.ui.template_page.QFileDialog.getSaveFileName",
                return_value=(str(out / "inputs.osi"), "Input Files(*.osi)"),
            ):
                window.common_design_func("Save")
            if not (out / "inputs.osi").is_file():
                raise RuntimeError("Application did not save inputs.osi.")
            write("ui-input-before.json", window.input_dict)
            write("widgets-before.json", widget_values(window.input_dock))
            result["status"] = "DESIGN RUNNING"
            write("result.json", result)
            QTest.mouseClick(window.input_dock.design_btn, Qt.LeftButton)
            if not getattr(window, "_design_running", False):
                raise RuntimeError("Design button did not start the worker.")
        except Exception:
            fail()

    def timeout():
        if getattr(window, "_design_running", False):
            from osdagbridge.core.utils.logger import bridge_logger

            result["timeout_requested_at"] = datetime.now().astimezone().isoformat()
            write("result.json", result)
            bridge_logger.cancel()
        else:
            result["status"] = "HARNESS TIMEOUT"
            write("result.json", result)
            window.close()
            app.quit()

    QTimer.singleShot(1500, begin)
    QTimer.singleShot(args.timeout_seconds * 1000, timeout)
    app.exec()
    return 0 if result["status"] == "DESIGN COMPLETED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
