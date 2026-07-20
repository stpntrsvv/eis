import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PySide6.QtWidgets import QApplication

from eis_controller import ControllerPackageResult
from eis_core import DatasetScale, FitResult, KramersKronigResult
from eis_qt import AnalysisCase, EisQtApp, ReliableInferenceWorker
from eis_spice_export import SpiceExportRefused, SpicePackageResult


def fitted_case(source: Path):
    best = FitResult(
        circuit_string="R0-p(R1,C1)",
        success=True,
        model=SimpleNamespace(
            parameters_=np.array([1.0, 2.0, 1e-3]),
            conf_=np.array([0.1, 0.2, 1e-4]),
        ),
        mean_fit_error=0.2,
        bic=-10.0,
        status="OK",
    )
    return AnalysisCase(
        file_path=str(source),
        frequencies=np.logspace(-1, 4, 20),
        z_experimental=np.ones(20, dtype=complex),
        scale=DatasetScale(1.0, 2.0, 1e-3),
        source_format="fixture",
        columns=["frequency", "z_real", "z_imag"],
        metadata={},
        selected_channel="Z",
        available_channels=["Z"],
        kk_result=KramersKronigResult(success=True, status="PASS"),
        results=[best],
        best_result=best,
    )


class QtSpiceExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        preset_patch = patch.object(EisQtApp, "load_user_presets", lambda _self: None)
        preset_patch.start()
        self.addCleanup(preset_patch.stop)
        self.window = EisQtApp()
        self.addCleanup(self.window.close)

    def install_case(self, source):
        self.window.cases = [fitted_case(source)]
        self.window.current_case_index = 0

    def test_auto_fit_uses_shared_adaptive_contract(self):
        with patch.object(self.window, "run_fit") as run_fit:
            self.window.run_auto_fit()

        run_fit.assert_called_once_with(None, "Auto-fit")

    def test_reliable_button_is_available_for_loaded_case(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.install_case(Path(temp_dir) / "source.csv")
            self.window.set_fit_controls_running(False)
            self.window.set_language("ru")

            self.assertTrue(self.window.run_reliable_button.isEnabled())
            self.assertEqual(
                self.window.run_reliable_button.text(),
                "Рассчитать надёжный вывод",
            )

    @patch("eis_qt.run_inference")
    def test_reliable_worker_uses_selected_channel(self, run_inference_mock):
        payload = {"decision": {"verdict": "recommended"}}
        run_inference_mock.return_value = payload
        worker = ReliableInferenceWorker(2, "source.mpr", "Z2")
        received = []
        worker.result_ready.connect(lambda index, result: received.append((index, result)))

        worker.run()

        run_inference_mock.assert_called_once_with(
            "source.mpr",
            mode="reliable",
            channel="Z2",
        )
        self.assertEqual(received, [(2, payload)])

    def test_spice_action_is_hidden_outside_pro_mode(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.install_case(Path(temp_dir) / "source.csv")

            self.assertFalse(self.window.spice_export_action.isVisible())
            self.assertFalse(self.window.controller_export_action.isVisible())
            self.assertFalse(self.window.spice_separator_action.isVisible())
            self.window.pro_toggle_button.setChecked(True)
            self.assertTrue(self.window.spice_export_action.isVisible())
            self.assertTrue(self.window.controller_export_action.isVisible())
            self.assertTrue(self.window.spice_separator_action.isVisible())
            self.assertTrue(self.window.spice_export_action.isEnabled())
            self.assertTrue(self.window.controller_export_action.isEnabled())
            self.window.pro_toggle_button.setChecked(False)
            self.assertFalse(self.window.spice_export_action.isVisible())
            self.assertFalse(self.window.controller_export_action.isVisible())
            self.assertFalse(self.window.spice_separator_action.isVisible())

    @patch("eis_qt.QMessageBox.information")
    @patch("eis_qt.QFileDialog.getOpenFileName")
    @patch("eis_qt.QFileDialog.getSaveFileName")
    @patch("eis_qt.export_spice_package")
    def test_toolbar_action_delegates_to_shared_exporter(
        self,
        export_mock,
        save_dialog,
        open_dialog,
        information,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.csv"
            source.write_text("fixture", encoding="utf-8")
            target = root / "package"
            self.install_case(source)
            self.window.pro_toggle_button.setChecked(True)
            save_dialog.return_value = (str(target), "")
            open_dialog.return_value = ("ngspice.exe", "")
            export_mock.return_value = SpicePackageResult(
                str(target),
                str(target / "model.lib"),
                str(target / "passport.json"),
                16,
                "46",
            )

            self.window.export_spice_package_for_active_case()

            export_mock.assert_called_once()
            analysis = export_mock.call_args.args[0]
            self.assertEqual(analysis.best.circuit_string, "R0-p(R1,C1)")
            self.assertEqual(export_mock.call_args.kwargs["ngspice_executable"], "ngspice.exe")
            information.assert_called_once()
            self.assertTrue(self.window.spice_export_action.isEnabled())

    @patch("eis_qt.QMessageBox.critical")
    @patch("eis_qt.QFileDialog.getOpenFileName", return_value=("ngspice.exe", ""))
    @patch("eis_qt.QFileDialog.getSaveFileName", return_value=("package", ""))
    @patch("eis_qt.export_spice_package")
    def test_refusal_is_shown_and_action_recovers(
        self,
        export_mock,
        _save_dialog,
        _open_dialog,
        critical,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source.csv"
            source.write_text("fixture", encoding="utf-8")
            self.install_case(source)
            self.window.pro_toggle_button.setChecked(True)
            export_mock.side_effect = SpiceExportRefused("gate failed")

            self.window.export_spice_package_for_active_case()

            critical.assert_called_once()
            self.assertTrue(self.window.spice_export_action.isEnabled())

    @patch("eis_qt.QMessageBox.information")
    @patch("eis_qt.QInputDialog.getDouble")
    @patch("eis_qt.QFileDialog.getSaveFileName")
    @patch("eis_qt.export_controller_package")
    def test_controller_action_exports_both_variants_with_selected_scales(
        self,
        export_mock,
        save_dialog,
        get_double,
        information,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.csv"
            source.write_text("fixture", encoding="utf-8")
            target = root / "controller-package"
            self.install_case(source)
            self.window.pro_toggle_button.setChecked(True)
            save_dialog.return_value = (str(target), "")
            get_double.side_effect = [(250.0, True), (20.0, True)]
            export_mock.return_value = ControllerPackageResult(
                str(target),
                str(target / "eis_model_f32.h"),
                str(target / "eis_model_f32.c"),
                str(target / "eis_model_q31.h"),
                str(target / "eis_model_q31.c"),
                str(target / "passport.json"),
                16,
                12,
            )

            self.window.export_controller_package_for_active_case()

            export_mock.assert_called_once()
            self.assertAlmostEqual(
                export_mock.call_args.kwargs["sample_period_s"],
                250e-6,
            )
            self.assertEqual(
                export_mock.call_args.kwargs["current_full_scale_a"],
                20.0,
            )
            information.assert_called_once()
            self.assertTrue(self.window.controller_export_action.isEnabled())


if __name__ == "__main__":
    unittest.main()
