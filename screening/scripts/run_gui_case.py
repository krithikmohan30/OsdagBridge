"""Drive real Qt design cases and preserve evidence without source edits.

Instrumentation: subclass the completion slot to snapshot the worker result before
the upstream slot updates the GUI; auto-dismiss recorded message boxes; replace
only the save-file chooser with a deterministic evidence path. Basic inputs use
QTest keyboard events and the real project-location dialog. Sequences use the
actual unlock button and confirm its transient-result reset. Optional reports
use the report API with live CAD captures, not the report dialog workflow.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import traceback
from unittest.mock import patch


def json_default(value):
    if is_dataclass(value):
        return asdict(value)
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
    parser.add_argument(
        "--cases", type=Path, help="Ordered JSON cases; one GUI session."
    )
    parser.add_argument(
        "--report", action="store_true", help="Exercise report API after each design."
    )
    parser.add_argument("--timeout-seconds", type=int, default=1200)
    parser.add_argument(
        "--record-video",
        action="store_true",
        help="Record only the application window with FFmpeg.",
    )
    args = parser.parse_args()
    out = args.output_dir.resolve()
    if out.exists():
        parser.error("Choose a new output directory; existing evidence is preserved.")
    out.mkdir(parents=True)
    session_root = out
    shutil.copy2(__file__, session_root / "driver.py")
    cases = (
        json.loads(args.cases.read_text(encoding="utf-8"))
        if args.cases
        else [{"id": "single", "span": args.span, "width": args.width}]
    )
    if not cases or not isinstance(cases, list):
        parser.error("Cases must be a nonempty JSON list.")
    case_index = 0
    session_results = []
    if args.cases:
        shutil.copy2(args.cases, session_root / "cases.json")
        out = session_root / cases[0]["id"]
        out.mkdir()

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
        "case": cases[0],
        "driver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
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
    from osdagbridge.desktop.ui.dialogs.material_properties import (
        MaterialPropertiesDialog,
    )

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
            if hasattr(self.backend, "material_props"):
                write("consumed-material-properties.json", self.backend.material_props)
            write("result.json", result)
            try:
                super()._on_design_done(exc_obj, err_trace, cancelled)
            except Exception:
                result["completion_slot_traceback"] = traceback.format_exc()
            QTimer.singleShot(2000, finish)

    window = EvidenceWindow("OsdagBridge", desktop.PlateGirderBridge)
    window.showMaximized()
    unlocking = False
    recorder = None
    video_log = None

    def start_recording():
        nonlocal recorder, video_log
        if not args.record_video:
            return
        executable = shutil.which("ffmpeg")
        if executable is None:
            result["video_error"] = "FFmpeg not found."
            return
        video_log = (session_root / "video-encoding.log").open("w", encoding="utf-8")
        recorder = subprocess.Popen(
            [
                executable,
                "-hide_banner",
                "-f",
                "gdigrab",
                "-framerate",
                "5",
                "-i",
                "title=" + window.windowTitle(),
                "-an",
                "-vf",
                "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-crf",
                "26",
                "-pix_fmt",
                "yuv420p",
                str(session_root / "workflow.mp4"),
            ],
            stdin=subprocess.PIPE,
            stdout=video_log,
            stderr=subprocess.STDOUT,
        )

    def stop_recording():
        nonlocal recorder
        if recorder is not None:
            try:
                recorder.communicate(b"q\n", timeout=20)
            except (BrokenPipeError, OSError):
                recorder.wait(timeout=20)
            except subprocess.TimeoutExpired:
                recorder.terminate()
                recorder.wait(timeout=10)
            result["video_recorder_exit"] = recorder.returncode
            recorder = None
        if video_log is not None:
            video_log.close()

    def handle_dialogs():
        for dialog in app.topLevelWidgets():
            if not isinstance(dialog, CustomMessageBox) or not dialog.isVisible():
                continue
            if dialog.property("evidence_recorded"):
                continue
            dialog.setProperty("evidence_recorded", True)
            index = len(result["dialogs"]) + 1
            texts = [w.text() for w in dialog.findChildren(QLabel) if w.text()]
            result["dialogs"].append(
                {"texts": texts, "screenshot": f"dialog-{index:02d}.png"}
            )
            screenshot(dialog, f"dialog-{index:02d}.png")
            write("result.json", result)
            buttons = dialog.findChildren(QPushButton)
            # Only confirm the requested test's unlock/reset of transient design results.
            if unlocking and "Clear Results" in texts:
                next(b for b in buttons if b.text() == "Continue").click()
                continue
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
            stop_recording()
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
            if result["status"] == "DESIGN COMPLETED":
                if not window.output_dock.isVisible():
                    window.output_dock_toggle()
                if not window.plots_view_active:
                    window.plots_view_toggle()
                QTimer.singleShot(1000, capture_plot_and_advance)
                return
        except Exception:
            fail()
            return
        close_session()

    def close_session():
        stop_recording()
        write("result.json", result)
        session_results.append(dict(result))
        (session_root / "session.json").write_text(
            json.dumps(
                session_results, indent=2, ensure_ascii=False, default=json_default
            ),
            encoding="utf-8",
        )
        print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)
        write("shutdown.json", {"phase": "calling window.close"})
        window.close()
        write("shutdown.json", {"phase": "window.close returned; calling app.quit"})
        app.quit()

    def capture_plot_and_advance():
        nonlocal case_index, out, result
        try:
            screenshot(window, "plot-window.png")
            plot = window.plots_widget
            write(
                "plot-state.json",
                {
                    "loadcase": plot._current_loadcase(),
                    "member": plot._current_member(),
                    "force_key": plot._current_force_key(),
                    "summary": plot._summary_data,
                },
            )
            plot._fig.savefig(out / "plot-figure.png", dpi=150)
            write("output-dock.json", widget_values(window.output_dock))
            if args.report or cases[case_index].get("report"):
                generate_report()
            write("result.json", result)
            if case_index + 1 == len(cases):
                close_session()
                return
            session_results.append(dict(result))
            (session_root / "session.json").write_text(
                json.dumps(
                    session_results, indent=2, ensure_ascii=False, default=json_default
                ),
                encoding="utf-8",
            )
            case_index += 1
            out = session_root / cases[case_index]["id"]
            out.mkdir()
            result = {
                "started_at": datetime.now().astimezone().isoformat(),
                "status": "STARTING",
                "case": cases[case_index],
                "python": sys.version,
                "pyside6": qt_binding_version,
                "instrumentation": __doc__,
                "dialogs": [],
            }
            write("result.json", result)
            QTimer.singleShot(500, begin)
        except Exception:
            fail()

    def generate_report():
        from osdagbridge.desktop.ui.dialogs.report_options import ReportOptionsDialog

        dialog = ReportOptionsDialog(parent=window)
        dialog.project_name.setText("Screening test " + cases[case_index]["id"])
        dialog.designer.setText("Krithik M")
        request = dialog.build_request(str(out / "application-report.pdf"))
        write("report-request.json", asdict(request))
        try:
            # Direct report API, with live CAD captures; report dialog interaction is untested.
            figures = window.cad_3d_widget.capture_for_report()
            report = window.backend.generate_design_report(
                request, {"figure_data": figures}
            )
            write("report-result.json", asdict(report))
            result["report_pdf_exists"] = bool(
                report.pdf_path and Path(report.pdf_path).is_file()
            )
        except Exception:
            result["report_traceback"] = traceback.format_exc()
            write("report-error.json", {"traceback": result["report_traceback"]})
        finally:
            dialog.deleteLater()

    def set_material(member, fields):
        def fill_dialog():
            try:
                dialog = next(
                    w
                    for w in app.topLevelWidgets()
                    if isinstance(w, MaterialPropertiesDialog) and w.isVisible()
                )
                typed = {}
                for key, value in fields.items():
                    widget = dialog.field_inputs[key]
                    widget.setFocus()
                    widget.selectAll()
                    QTest.keyClicks(widget, str(value))
                    QTest.keyClick(widget, Qt.Key_Tab)
                    typed[key] = {"requested": str(value), "displayed": widget.text()}
                write(f"{member}-typed.json", typed)
                write(
                    f"{member}-dialog-fields.json",
                    {k: w.text() for k, w in dialog.field_inputs.items()},
                )
                screenshot(dialog, f"{member}-dialog.png")
                dialog.findChild(QPushButton, "primary").click()
            except Exception:
                fail()

        combo = window.input_dock._material_combo_map[member]
        QTimer.singleShot(400, fill_dialog)
        from osdagbridge.desktop.ui.docks.input_dock import MATERIAL_CUSTOM_OPTION

        combo.setCurrentText(MATERIAL_CUSTOM_OPTION)

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
        nonlocal unlocking
        try:
            case = cases[case_index]
            if window.input_dock.is_locked:
                unlocking = True
                QTest.mouseClick(window.input_dock.lock_btn, Qt.LeftButton)
                unlocking = False
                if window.input_dock.is_locked:
                    raise RuntimeError("Unlock did not complete.")
                write(
                    "after-unlock.json",
                    {
                        "output_key_count": len(window.backend.output_dict),
                        "plot_dataset_cleared": window.plots_widget._ds_all is None,
                    },
                )
            set_text("geometry.span", str(case.get("span", args.span)))
            set_text("geometry.carriageway_width", str(case.get("width", args.width)))
            set_text("geometry.skew_angle", "0")
            if case_index == 0:
                QTimer.singleShot(500, set_location)
                window.input_dock.show_project_location_dialog()
            if not window.input_dict.get("project.location"):
                raise RuntimeError("Location was not saved.")
            for member, fields in case.get("materials", {}).items():
                set_material(member, fields)
            for member, grade in case.get("grades", {}).items():
                window.input_dock._material_combo_map[member].setCurrentText(grade)
            write("ui-input-before-save.json", window.input_dict)
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
    QTimer.singleShot(500, start_recording)
    QTimer.singleShot(args.timeout_seconds * 1000, timeout)
    app.exec()
    return (
        0
        if all(r["status"] == "DESIGN COMPLETED" for r in session_results)
        and session_results
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
