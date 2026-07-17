import unittest
from unittest.mock import patch

import numpy as np

from eis_core import (
    INDUCTIVE_CIRCUITS,
    DatasetScale,
    FitResult,
    build_bounds_and_guess,
    build_multistart_guesses,
    choose_best_result,
    fit_circuit,
    resistance_lower_bound,
    route_circuit_candidates,
    route_residual_candidates,
)
from eis_io import load_text_eis_file
from eis_io import EisDataset, clean_dataset, load_text_eis_file


class _SuccessfulCircuit:
    last_fit_kwargs = None

    def __init__(self, circuit_string, initial_guess):
        self.parameters_ = np.array(initial_guess, dtype=float)
        self.conf_ = np.ones(len(initial_guess), dtype=float) * 1e-9

    def fit(self, frequencies, z_data, **kwargs):
        type(self).last_fit_kwargs = kwargs

    def predict(self, frequencies):
        return np.ones(len(frequencies), dtype=complex)


class _BudgetExhaustedCircuit(_SuccessfulCircuit):
    def fit(self, frequencies, z_data, **kwargs):
        raise RuntimeError("The maximum number of function evaluations is exceeded.")


class _PredictionModel:
    def __init__(self, predicted):
        self.predicted = np.asarray(predicted, dtype=complex)

    def predict(self, frequencies):
        return self.predicted


class FitSafetyTests(unittest.TestCase):
    def test_embedded_vendor_header_is_used_instead_of_metadata_numbers(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vendor.csv"
            path.write_text(
                "serial number,hardware revision\n123,4\n\nimpedance spectrum\n"
                "frequency,real impedance,imaginary impedance\n"
                "10,2,-1\n1,3,-2\n",
                encoding="utf-8",
            )
            dataset = load_text_eis_file(path)
            self.assertEqual(dataset.source_format, "embedded_named_text_table")
            self.assertEqual(dataset.frequencies.tolist(), [10.0, 1.0])
            self.assertEqual(dataset.z.tolist(), [2-1j, 3-2j])

    def test_generic_fallback_rejects_numeric_readme(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "README.txt"
            path.write_text(
                "sample 1 35 5\nrange 0.5 1000000 5\ncycles 1 3 5\n"
                "cycles 4 6 15\ncycles 7 9 25\ncycles 10 12 35\n"
                "cycles 13 15 45\ncycles 16 18 55\ncycles 19 21 65\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "README/metadata"):
                load_text_eis_file(path)
    def setUp(self):
        self.frequencies = np.array([100.0, 10.0, 1.0])
        self.z_data = np.ones(3, dtype=complex)
        self.scale = DatasetScale(r0=1.0, r_transfer=10.0, capacitance=1e-4)

    @patch("eis_core.CustomCircuit", _SuccessfulCircuit)
    def test_fit_passes_finite_optimizer_budget(self):
        result = fit_circuit(
            self.frequencies,
            self.z_data,
            "R0-p(R1,C1)",
            self.scale,
            max_fit_evaluations=123,
            fit_tolerance=1e-7,
        )

        self.assertTrue(result.success)
        self.assertEqual(_SuccessfulCircuit.last_fit_kwargs["maxfev"], 123)
        self.assertEqual(_SuccessfulCircuit.last_fit_kwargs["ftol"], 1e-7)
        self.assertEqual(_SuccessfulCircuit.last_fit_kwargs["xtol"], 1e-7)
        self.assertEqual(_SuccessfulCircuit.last_fit_kwargs["gtol"], 1e-7)

    @patch("eis_core.CustomCircuit", _BudgetExhaustedCircuit)
    def test_exhausted_budget_has_distinct_status(self):
        result = fit_circuit(
            self.frequencies,
            self.z_data,
            "R0-p(R1,C1)",
            self.scale,
            max_fit_evaluations=1,
        )

        self.assertFalse(result.success)
        self.assertEqual(result.status, "LIMIT")
        self.assertIn("LIMIT:optimization_budget_exhausted", result.flags)

    def test_clean_dataset_rejects_bad_frequencies_and_aggregates_duplicates(self):
        dataset = EisDataset(
            file_path="fixture",
            frequencies=np.array([10.0, 10.0, 1.0, 0.0, np.nan]),
            z=np.array([1 + 2j, 3 + 4j, 5 + 6j, 7 + 8j, 9 + 10j]),
            source_format="fixture",
        )

        cleaned = clean_dataset(dataset)

        np.testing.assert_allclose(cleaned.frequencies, [10.0, 1.0])
        np.testing.assert_allclose(cleaned.z, [2 + 3j, 5 + 6j])
        self.assertEqual(cleaned.metadata["aggregated_duplicate_points"], 1)
        self.assertEqual(cleaned.metadata["dropped_nonpositive_frequency_points"], 1)
        self.assertEqual(cleaned.metadata["dropped_nonfinite_points"], 1)

    def test_named_csv_accepts_frequency_real_imag_ohm_headers(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "keysight.csv"
            path.write_text(
                "Frequency_Hz,Real_Ohm,Imag_Ohm\n100,2,-3\n10,4,-5\n",
                encoding="utf-8",
            )
            dataset = load_text_eis_file(str(path))

        np.testing.assert_allclose(dataset.frequencies, [100, 10])
        np.testing.assert_allclose(dataset.z, [2 - 3j, 4 - 5j])

    def test_pandas_index_column_does_not_become_frequency(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "indexed.csv"
            path.write_text(
                ",f,abs,phase,Zreal,-Zimag\n0,100,2,-0.1,1.5,0.5\n1,10,3,-0.2,2.0,1.0\n",
                encoding="utf-8",
            )
            dataset = load_text_eis_file(str(path))

        np.testing.assert_allclose(dataset.frequencies, [100, 10])
        np.testing.assert_allclose(dataset.z, [1.5 - 0.5j, 2.0 - 1.0j])

    def test_selector_prefers_ok_when_warn_is_inside_bic_window(self):
        ok = FitResult("R0-p(R1,C1)", True, bic=10.0, n_params=3, status="OK")
        warn = FitResult("R0-p(R1,CPE0)", True, bic=5.0, n_params=4, status="WARN")

        self.assertIs(choose_best_result([warn, ok], bic_window=6.0), ok)

    def test_selector_keeps_warn_when_bic_evidence_is_decisive(self):
        ok = FitResult("R0-p(R1,C1)", True, bic=10.0, n_params=3, status="OK")
        warn = FitResult("R0-p(R1,CPE0)", True, bic=-100.0, n_params=4, status="WARN")

        self.assertIs(choose_best_result([warn, ok]), warn)

    def test_selector_uses_simpler_model_inside_bic_window(self):
        simple = FitResult("R0-p(R1,C1)", True, bic=10.0, n_params=3, status="OK")
        complex_model = FitResult("R0-p(R1,CPE0)-p(R2,CPE1)", True, bic=5.0, n_params=7, status="OK")

        self.assertIs(choose_best_result([complex_model, simple], bic_window=6.0), simple)
        self.assertIs(choose_best_result([complex_model, simple], bic_window=2.0), complex_model)

    def test_selector_can_refuse_all_bad_results(self):
        bad = FitResult("R0-p(R1,C1)", True, bic=1.0, n_params=3, status="BAD")

        with self.assertRaisesRegex(ValueError, "No reliable"):
            choose_best_result([bad], allow_bad_fallback=False)

    def test_multistart_guesses_are_deterministic_bounded_and_distinct(self):
        first = build_multistart_guesses([10.0, 1e-4], [1e-3, 1e-10], [1e8, 10.0], starts=4, seed=42)
        second = build_multistart_guesses([10.0, 1e-4], [1e-3, 1e-10], [1e8, 10.0], starts=4, seed=42)

        self.assertEqual(first, second)
        self.assertEqual(len(first), 4)
        self.assertEqual(len({tuple(item) for item in first}), 4)
        self.assertTrue(all(1e-3 <= item[0] <= 1e8 for item in first))
        self.assertTrue(all(1e-10 <= item[1] <= 10.0 for item in first))

    def test_router_adds_inductive_family_for_stable_high_frequency_loop(self):
        frequencies = np.logspace(-2, 4, 60)
        z = 0.002 + 1j * np.linspace(-0.004, 0.007, 60)

        routing = route_circuit_candidates(frequencies, z)

        self.assertIn("inductive", routing.families)
        self.assertNotIn("diffusion", routing.families)
        self.assertTrue(set(INDUCTIVE_CIRCUITS).issubset(routing.circuits))
        self.assertTrue(routing.features["high_frequency_inductive"])

    def test_router_does_not_add_inductance_for_capacitive_spectrum(self):
        frequencies = np.logspace(-2, 4, 60)
        z = 0.002 - 1j * np.linspace(0.007, 0.0001, 60)

        routing = route_circuit_candidates(frequencies, z)

        self.assertNotIn("inductive", routing.families)
        self.assertFalse(routing.features["high_frequency_inductive"])

    def test_resistance_bounds_follow_milliohm_dataset_scale(self):
        scale = DatasetScale(r0=3e-4, r_transfer=7e-4, capacitance=1.0)

        low, _, guess = build_bounds_and_guess("R0-p(R1,C1)", scale)

        self.assertLess(resistance_lower_bound(scale), 1e-5)
        self.assertEqual(low[:2], [3e-8, 3e-8])
        self.assertTrue(all(value > low[index] for index, value in enumerate(guess[:2])))

    def test_second_tier_promotes_inductive_diffusion_for_coherent_low_frequency_residual(self):
        frequencies = np.logspace(-2, 4, 60)
        measured = np.ones(60, dtype=complex)
        predicted = measured.copy()
        predicted[:12] = 0.8 - 0.2j
        fitted = FitResult("L0-R0-p(R1,CPE0)", True, model=_PredictionModel(predicted), status="WARN")

        routing = route_residual_candidates(frequencies, measured, fitted, ("simple", "inductive"))

        self.assertIn("inductive_diffusion", routing.families)
        self.assertTrue(routing.features["structured_low_frequency_residual"])
        self.assertEqual(len(routing.circuits), 3)

    def test_second_tier_rejects_incoherent_low_frequency_residual(self):
        frequencies = np.logspace(-2, 4, 60)
        measured = np.ones(60, dtype=complex)
        predicted = measured.copy()
        predicted[:12:2] = 0.8 - 0.2j
        predicted[1:12:2] = 1.2 + 0.2j
        fitted = FitResult("L0-R0-p(R1,CPE0)", True, model=_PredictionModel(predicted), status="WARN")

        routing = route_residual_candidates(frequencies, measured, fitted, ("simple", "inductive"))

        self.assertFalse(routing.features["structured_low_frequency_residual"])
        self.assertEqual(routing.circuits, ())

    @patch("eis_core.CustomCircuit", _SuccessfulCircuit)
    def test_fit_records_multistart_metrics(self):
        result = fit_circuit(
            self.frequencies,
            self.z_data,
            "R0-p(R1,C1)",
            self.scale,
            fit_restarts=3,
            restart_seed=7,
        )

        self.assertEqual(result.starts_attempted, 3)
        self.assertEqual(result.starts_succeeded, 3)
        self.assertIn(result.best_start_index, range(3))


if __name__ == "__main__":
    unittest.main()
