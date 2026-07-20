import csv
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

import eis_cli
from eis_controller import ControllerPackageResult
from eis_core import DatasetScale, FitResult, KramersKronigResult
from eis_pipeline import AnalysisResult, discover_input_files, fit_result_dict
from eis_spice_export import SpicePackageResult


class _Model:
    parameters_ = np.array([2.0, 3.0, 4e-4])
    conf_ = np.array([0.2, 0.3, 4e-5])


def successful_result(file_path: str) -> AnalysisResult:
    fit = FitResult(
        circuit_string="R0-p(R1,C1)",
        success=True,
        model=_Model(),
        mean_fit_error=1.25,
        max_param_error=10.0,
        rss_weighted=0.5,
        aic=-10.0,
        bic=-8.0,
        n_params=3,
        status="OK",
    )
    return AnalysisResult(
        file_path=file_path,
        success=True,
        source_format="fixture",
        selected_channel="Z",
        point_count=12,
        scale=DatasetScale(2.0, 3.0, 4e-4),
        kk=KramersKronigResult(success=True, status="PASS", rmse_percent=0.5, max_error_percent=1.0, mu=0.8),
        fits=[fit],
        best=fit,
        stage="complete",
    )


class PipelineCliTests(unittest.TestCase):
    def test_auto_preset_defers_candidate_selection_to_pipeline(self):
        parser = eis_cli.build_parser()
        args = parser.parse_args(["fixture.csv"])

        self.assertIsNone(eis_cli.select_circuits(args))

    def test_explicit_preset_keeps_fixed_candidate_family(self):
        parser = eis_cli.build_parser()
        args = parser.parse_args(["fixture.csv", "--preset", "inductive"])

        self.assertTrue(eis_cli.select_circuits(args))

    def test_fit_result_is_json_safe_and_contains_parameters(self):
        payload = fit_result_dict(successful_result("x.csv").best, is_best=True)
        encoded = json.dumps(payload, allow_nan=False)
        self.assertIn('"R0"', encoded)
        self.assertEqual(payload["parameters"][0]["relative_error_percent"], 10.0)

    def test_discovery_is_recursive_deduplicated_and_filters_extensions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "a.csv").write_text("x", encoding="utf-8")
            (root / "ignore.md").write_text("x", encoding="utf-8")
            (root / "nested").mkdir()
            (root / "nested" / "b.mpr").write_text("x", encoding="utf-8")

            files = discover_input_files([str(root), str(root / "a.csv")], recursive=True)

            self.assertEqual(len(files), 2)
            self.assertTrue(files[0].endswith("a.csv"))
            self.assertTrue(files[1].endswith("b.mpr"))

    @patch("eis_cli.analyze_file")
    def test_batch_jsonl_continues_after_failed_file(self, analyze_mock):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = root / "a.csv"
            second = root / "b.csv"
            first.write_text("x", encoding="utf-8")
            second.write_text("x", encoding="utf-8")
            output = root / "artifacts"
            failed = AnalysisResult(file_path=str(first), stage="load", error_message="bad file")
            analyze_mock.side_effect = [failed, successful_result(str(second))]

            code = eis_cli.run([str(root), "--format", "jsonl", "--output", str(output), "--quiet"])

            self.assertEqual(code, eis_cli.EXIT_INPUT_FAILURE)
            lines = (output / "results.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 2)
            self.assertFalse(json.loads(lines[0])["success"])
            self.assertTrue(json.loads(lines[1])["success"])

    @patch("eis_cli.analyze_file")
    def test_fail_fast_persists_completed_jsonl_result(self, analyze_mock):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for name in ("a.csv", "b.csv"):
                (root / name).write_text("x", encoding="utf-8")
            output = root / "artifacts"
            analyze_mock.return_value = AnalysisResult(file_path="a.csv", stage="load", error_message="bad file")

            code = eis_cli.run([
                str(root), "--format", "jsonl", "--output", str(output), "--fail-fast", "--quiet"
            ])

            self.assertEqual(code, eis_cli.EXIT_INPUT_FAILURE)
            self.assertEqual(len((output / "results.jsonl").read_text(encoding="utf-8").splitlines()), 1)
            self.assertEqual(analyze_mock.call_count, 1)

    @patch("eis_cli.analyze_file")
    def test_csv_summary_is_machine_readable(self, analyze_mock):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "a.csv"
            source.write_text("x", encoding="utf-8")
            output = Path(temp_dir) / "summary.csv"
            analyze_mock.return_value = successful_result(str(source))

            code = eis_cli.run([str(source), "--format", "csv", "--output", str(output), "--quiet"])

            self.assertEqual(code, eis_cli.EXIT_OK)
            with output.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["best_circuit"], "R0-p(R1,C1)")
            self.assertEqual(rows[0]["kk_status"], "PASS")

    @patch("eis_cli.export_spice_package")
    @patch("eis_cli.load_eis_file")
    @patch("eis_cli.analyze_file")
    def test_single_file_spice_export_uses_validated_package_path(
        self,
        analyze_mock,
        load_mock,
        export_mock,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "a.csv"
            source.write_text("x", encoding="utf-8")
            target = Path(temp_dir) / "spice-package"
            analyze_mock.return_value = successful_result(str(source))
            load_mock.return_value = SimpleNamespace(frequencies=np.logspace(-1, 4, 12))
            export_mock.return_value = SpicePackageResult(
                str(target),
                str(target / "model.lib"),
                str(target / "passport.json"),
                12,
                "46",
            )

            code = eis_cli.run([
                str(source),
                "--spice-export",
                str(target),
                "--ngspice",
                "ngspice",
                "--quiet",
            ])

            self.assertEqual(code, eis_cli.EXIT_OK)
            export_mock.assert_called_once()

    @patch("eis_cli.analyze_file")
    def test_batch_spice_export_is_rejected_before_analysis(self, analyze_mock):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "a.csv").write_text("x", encoding="utf-8")
            (root / "b.csv").write_text("x", encoding="utf-8")

            code = eis_cli.run([
                str(root),
                "--spice-export",
                str(root / "package"),
                "--quiet",
            ])

            self.assertEqual(code, eis_cli.EXIT_ARGUMENT_ERROR)
            analyze_mock.assert_not_called()

    @patch("eis_cli.export_controller_package")
    @patch("eis_cli.load_eis_file")
    @patch("eis_cli.analyze_file")
    def test_single_file_controller_export_passes_scales(
        self,
        analyze_mock,
        load_mock,
        export_mock,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "a.csv"
            source.write_text("x", encoding="utf-8")
            target = Path(temp_dir) / "controller-package"
            analyze_mock.return_value = successful_result(str(source))
            load_mock.return_value = SimpleNamespace(frequencies=np.logspace(-1, 4, 12))
            export_mock.return_value = ControllerPackageResult(
                str(target),
                str(target / "eis_model_f32.h"),
                str(target / "eis_model_f32.c"),
                str(target / "eis_model_q31.h"),
                str(target / "eis_model_q31.c"),
                str(target / "passport.json"),
                12,
                8,
            )

            code = eis_cli.run([
                str(source),
                "--controller-export",
                str(target),
                "--sample-period-us",
                "100",
                "--current-full-scale-a",
                "20",
                "--controller-max-frequency-hz",
                "50",
                "--quiet",
            ])

            self.assertEqual(code, eis_cli.EXIT_OK)
            call = export_mock.call_args
            self.assertAlmostEqual(call.kwargs["sample_period_s"], 100e-6)
            self.assertEqual(call.kwargs["current_full_scale_a"], 20.0)
            self.assertEqual(call.kwargs["max_frequency_hz"], 50.0)

    @patch("eis_cli.analyze_file")
    def test_controller_export_requires_period_and_current_scale(self, analyze_mock):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "a.csv"
            source.write_text("x", encoding="utf-8")

            code = eis_cli.run([
                str(source),
                "--controller-export",
                str(Path(temp_dir) / "controller-package"),
                "--quiet",
            ])

            self.assertEqual(code, eis_cli.EXIT_ARGUMENT_ERROR)
            analyze_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
