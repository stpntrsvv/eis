import unittest
from unittest.mock import patch

import numpy as np

from eis_core import DatasetScale, fit_circuit
from eis_io import EisDataset, clean_dataset


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


class FitSafetyTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
