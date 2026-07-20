from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from eis_core import FitResult
from eis_pipeline import fit_spectrum


def fitted(circuit: str, bic: float) -> FitResult:
    return FitResult(
        circuit_string=circuit,
        success=True,
        model=object(),
        mean_fit_error=1.0,
        rss_weighted=0.1,
        aic=bic - 1.0,
        bic=bic,
        n_params=3,
        status="OK",
    )


class SharedFittingTests(unittest.TestCase):
    @patch("eis_pipeline.route_residual_candidates")
    @patch("eis_pipeline.route_circuit_candidates")
    @patch("eis_pipeline.fit_circuits")
    def test_adaptive_contract_runs_both_tiers_and_records_routing(
        self,
        fit_mock,
        first_route,
        residual_route,
    ):
        first = fitted("R0-p(R1,CPE0)", -10.0)
        second = fitted("R0-p(R1,CPE0)-Wo0", -30.0)
        first_route.return_value = SimpleNamespace(
            circuits=(first.circuit_string,),
            families=("simple",),
            features={"inductive": False},
        )
        residual_route.return_value = SimpleNamespace(
            circuits=(first.circuit_string, second.circuit_string),
            families=("simple", "diffusion"),
            features={"coherent_low_frequency_residual": True},
        )
        fit_mock.side_effect = [[first], [second]]
        planned = []

        outcome = fit_spectrum(
            np.logspace(-1, 4, 20),
            np.ones(20, dtype=complex),
            circuits=None,
            on_tier=lambda tier, circuits, _metadata: planned.append(
                (tier, tuple(circuits))
            ),
        )

        self.assertEqual(outcome.best.circuit_string, second.circuit_string)
        self.assertEqual(outcome.routing_metadata["mode"], "adaptive_v2")
        self.assertEqual(outcome.routing_metadata["candidate_count"], 2)
        self.assertEqual(
            outcome.routing_metadata["families"],
            ["simple", "diffusion"],
        )
        self.assertEqual(planned, [
            (1, (first.circuit_string,)),
            (2, (second.circuit_string,)),
        ])
        self.assertEqual(fit_mock.call_args_list[1].kwargs["restart_seed"], 10_000)

    @patch("eis_pipeline.route_residual_candidates")
    @patch("eis_pipeline.fit_circuits")
    def test_explicit_contract_never_adds_residual_candidates(
        self,
        fit_mock,
        residual_route,
    ):
        result = fitted("R0-p(R1,C1)", -10.0)
        fit_mock.return_value = [result]
        overrides = {"R0-p(R1,C1)": {"R0": {"initial": 1.0}}}

        outcome = fit_spectrum(
            np.logspace(-1, 4, 20),
            np.ones(20, dtype=complex),
            circuits=[result.circuit_string],
            parameter_overrides_by_circuit=overrides,
        )

        self.assertEqual(outcome.routing_metadata["mode"], "explicit")
        self.assertEqual(outcome.best, result)
        self.assertIs(
            fit_mock.call_args.kwargs["parameter_overrides_by_circuit"],
            overrides,
        )
        residual_route.assert_not_called()

    @patch("eis_pipeline.fit_circuits")
    def test_cancelled_contract_does_not_start_second_tier(self, fit_mock):
        fit_mock.return_value = []

        outcome = fit_spectrum(
            np.logspace(-1, 4, 20),
            np.ones(20, dtype=complex),
            circuits=["R0-p(R1,C1)"],
            should_cancel=lambda: True,
        )

        self.assertTrue(outcome.cancelled)
        self.assertIsNone(outcome.best)


if __name__ == "__main__":
    unittest.main()
