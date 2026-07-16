import contextlib
from dataclasses import dataclass
import io
import re
import time
from typing import Iterable, Optional

import numpy as np
from impedance.models.circuits import CustomCircuit
from impedance import validation as impedance_validation

impedance_validation.circuit_elements.setdefault("np", np)


# impedance.py otherwise defaults to 100,000 function evaluations and a very
# strict ftol=1e-13. A difficult/non-identifiable circuit can therefore occupy a
# workstation for minutes. These are deliberate production budgets, not merely
# optimizer hints.
DEFAULT_MAX_FIT_EVALUATIONS = 5_000
DEFAULT_FIT_TOLERANCE = 1e-9


IDEAL_RC_CIRCUITS = [
    "R0-p(R1,C1)",
]

INTERFACE_CIRCUITS = [
    "R0-p(R1,CPE0)",
    "R0-p(R1,CPE0)-p(R2,CPE1)",
    "R0-p(R1-p(R2,CPE1),CPE0)",
]

DIFFUSION_CIRCUITS = [
    "R0-p(R1,CPE0)-W0",
    "R0-p(R1,CPE0)-Wo0",
    "R0-p(R1,CPE0)-Ws0",
    "R0-p(R1-W0,CPE0)",
    "R0-p(R1-Wo0,CPE0)",
    "R0-p(R1-Ws0,CPE0)",
    "R0-p(R1,CPE0)-p(R2,CPE1)-W0",
    "R0-p(R1,CPE0)-p(R2,CPE1)-Wo0",
    "R0-p(R1,CPE0)-p(R2,CPE1)-Ws0",
    "R0-p(R1-p(R2,CPE1)-W0,CPE0)",
]

INDUCTIVE_CIRCUITS = [
    "L0-R0-p(R1,CPE0)",
    "L0-R0-p(R1,CPE0)-p(R2,CPE1)",
    "L0-R0-p(R1-p(R2,CPE1),CPE0)",
]

SIMPLE_CIRCUITS = IDEAL_RC_CIRCUITS + INTERFACE_CIRCUITS
ADVANCED_CIRCUITS = DIFFUSION_CIRCUITS + INDUCTIVE_CIRCUITS
BASIC_CIRCUITS = SIMPLE_CIRCUITS + DIFFUSION_CIRCUITS
DEFAULT_CIRCUITS = SIMPLE_CIRCUITS + ADVANCED_CIRCUITS

# Backward-compatible aliases for older imports during the refactor.
GAVRIK_CIRCUITS = SIMPLE_CIRCUITS
WARBURG_CIRCUITS = DIFFUSION_CIRCUITS


@dataclass(frozen=True)
class DatasetScale:
    r0: float
    r_transfer: float
    capacitance: float


@dataclass
class FitResult:
    circuit_string: str
    success: bool
    model: Optional[CustomCircuit] = None
    mean_fit_error: float = np.inf
    max_param_error: float = np.inf
    rss_weighted: float = np.inf
    aic: float = np.inf
    bic: float = np.inf
    n_params: int = 0
    status: str = "FAIL"
    flags: tuple[str, ...] = ()
    error_message: str = ""
    elapsed_seconds: float = 0.0


@dataclass
class KramersKronigResult:
    success: bool
    status: str = "FAIL"
    rmse_percent: float = np.inf
    max_error_percent: float = np.inf
    mu: float = np.inf
    n_rc: int = 0
    frequencies: np.ndarray | None = None
    z_fit: np.ndarray | None = None
    residual_real: np.ndarray | None = None
    residual_imag: np.ndarray | None = None
    relative_error_percent: np.ndarray | None = None
    flags: tuple[str, ...] = ()
    error_message: str = ""


def circuit_to_readable(circuit_string: str) -> str:
    return circuit_string.replace("p(", "(").replace(",", " || ").replace("-", " + ")


def circuit_to_latex(circuit_string: str) -> str:
    return circuit_string.replace("p(", "(").replace(",", r" \parallel ").replace("-", " + ")


def extract_circuit_elements(circuit_string: str) -> list[str]:
    clean = re.sub(r"[p()\s,]", "-", circuit_string)
    return [element for element in clean.split("-") if element]


def parameter_names(circuit_string: str) -> list[str]:
    names = []
    for element in extract_circuit_elements(circuit_string):
        if element.startswith(("CPE", "Wo", "Ws")):
            names.extend([f"{element}_0", f"{element}_1"])
        else:
            names.append(element)
    return names


def estimate_dataset_scale(frequencies, z_data) -> DatasetScale:
    re_parts = z_data.real
    im_parts = -z_data.imag

    r0 = float(np.min(re_parts))
    r_max = float(np.max(re_parts))
    r_transfer = float(r_max - r0) if r_max > r0 else 100.0

    idx_mid = int(np.argmax(np.abs(im_parts)))
    f_mid = float(frequencies[idx_mid])
    capacitance = float(1.0 / (2 * np.pi * f_mid * r_transfer)) if r_transfer > 0 else 1e-4

    return DatasetScale(r0=r0, r_transfer=r_transfer, capacitance=capacitance)


def build_bounds_and_guess(circuit_string: str, scale: DatasetScale):
    low_bounds = []
    high_bounds = []
    initial_guess = []
    r_idx = 0
    cpe_idx = 0

    for element in extract_circuit_elements(circuit_string):
        match = re.match(r"([a-zA-Z]+)", element)
        if not match:
            raise ValueError(f"Unknown circuit element: {element}")

        element_type = match.group(1)

        if element_type == "R":
            value = scale.r0 if r_idx == 0 else scale.r_transfer / max(1, r_idx)
            initial_guess.append(value)
            low_bounds.append(1e-3)
            high_bounds.append(1e8)
            r_idx += 1
        elif element_type == "CPE":
            q_value = scale.capacitance * (10 ** cpe_idx)
            initial_guess.extend([q_value, 0.75])
            low_bounds.extend([1e-10, 0.501])
            high_bounds.extend([10.0, 1.0])
            cpe_idx += 1
        elif element_type == "C":
            initial_guess.append(scale.capacitance)
            low_bounds.append(1e-10)
            high_bounds.append(10.0)
        elif element_type in {"Wo", "Ws"}:
            initial_guess.extend([scale.r_transfer * 1.5, 5.0])
            low_bounds.extend([1e-2, 1e-3])
            high_bounds.extend([1e7, 1e5])
        elif element_type == "W":
            initial_guess.append(scale.r_transfer * 0.5)
            low_bounds.append(1e-2)
            high_bounds.append(1e7)
        elif element_type == "L":
            initial_guess.append(1e-6)
            low_bounds.append(1e-12)
            high_bounds.append(1.0)
        else:
            raise ValueError(f"Unsupported circuit element type: {element_type}")

    return low_bounds, high_bounds, initial_guess


def apply_parameter_overrides(circuit_string: str, low_bounds, high_bounds, initial_guess, parameter_overrides=None):
    if not parameter_overrides:
        return low_bounds, high_bounds, initial_guess

    names = parameter_names(circuit_string)
    low_bounds = list(low_bounds)
    high_bounds = list(high_bounds)
    initial_guess = list(initial_guess)

    for index, name in enumerate(names):
        override = parameter_overrides.get(name)
        if not override:
            continue

        guess = float(override.get("initial", initial_guess[index]))
        low = float(override.get("lower", low_bounds[index]))
        high = float(override.get("upper", high_bounds[index]))
        if not np.isfinite([guess, low, high]).all():
            raise ValueError(f"Non-finite bounds/guess for {name}.")
        if low >= high:
            raise ValueError(f"Lower bound must be below upper bound for {name}.")

        initial_guess[index] = guess
        low_bounds[index] = low
        high_bounds[index] = high

    return low_bounds, high_bounds, initial_guess


def fit_circuit(
    frequencies,
    z_data,
    circuit_string: str,
    scale: DatasetScale,
    parameter_overrides=None,
    max_fit_evaluations: int = DEFAULT_MAX_FIT_EVALUATIONS,
    fit_tolerance: float = DEFAULT_FIT_TOLERANCE,
) -> FitResult:
    started_at = time.monotonic()
    try:
        low_bounds, high_bounds, guess = build_bounds_and_guess(circuit_string, scale)
        low_bounds, high_bounds, guess = apply_parameter_overrides(
            circuit_string, low_bounds, high_bounds, guess, parameter_overrides
        )
        safe_guess = np.clip(
            guess,
            np.array(low_bounds, dtype=float) + 1e-12,
            np.array(high_bounds, dtype=float) - 1e-12,
        ).tolist()

        circuit = CustomCircuit(circuit_string, initial_guess=safe_guess)
        circuit.fit(
            frequencies,
            z_data,
            bounds=(low_bounds, high_bounds),
            weight_by_modulus=True,
            maxfev=int(max_fit_evaluations),
            ftol=float(fit_tolerance),
            xtol=float(fit_tolerance),
            gtol=float(fit_tolerance),
        )

        z_predicted = circuit.predict(frequencies)
        relative_residuals = np.abs(z_data - z_predicted) / np.maximum(np.abs(z_data), 1e-30)
        mean_fit_error = float(np.mean(relative_residuals) * 100)
        rss_weighted = float(np.sum(relative_residuals ** 2))
        n_params = len(circuit.parameters_)
        aic, bic = information_criteria(rss_weighted, n_observations=2 * len(frequencies), n_params=n_params)

        param_errors = []
        for value, confidence in zip(circuit.parameters_, circuit.conf_):
            if value != 0 and confidence is not None:
                param_errors.append(abs(confidence / value) * 100)
            else:
                param_errors.append(np.inf)

        max_param_error = float(np.max(param_errors)) if param_errors else np.inf
        flags = physical_flags(
            circuit_string=circuit_string,
            parameters=circuit.parameters_,
            confidences=circuit.conf_,
            low_bounds=low_bounds,
            high_bounds=high_bounds,
            max_param_error=max_param_error,
        )
        status = classify_fit(flags)
        return FitResult(
            circuit_string=circuit_string,
            success=True,
            model=circuit,
            mean_fit_error=mean_fit_error,
            max_param_error=max_param_error,
            rss_weighted=rss_weighted,
            aic=aic,
            bic=bic,
            n_params=n_params,
            status=status,
            flags=tuple(flags),
            elapsed_seconds=time.monotonic() - started_at,
        )
    except Exception as exc:
        message = str(exc)
        budget_exhausted = any(
            marker in message.lower()
            for marker in ("maximum number of function evaluations", "maxfev", "optimal parameters not found")
        )
        if budget_exhausted:
            message = f"Optimization budget exhausted ({max_fit_evaluations} evaluations): {message}"
        return FitResult(
            circuit_string=circuit_string,
            success=False,
            status="LIMIT" if budget_exhausted else "FAIL",
            flags=("LIMIT:optimization_budget_exhausted",) if budget_exhausted else (),
            error_message=message,
            elapsed_seconds=time.monotonic() - started_at,
        )


def fit_circuits(
    frequencies,
    z_data,
    circuits: Iterable[str] = DEFAULT_CIRCUITS,
    parameter_overrides_by_circuit=None,
    max_fit_evaluations: int = DEFAULT_MAX_FIT_EVALUATIONS,
    fit_tolerance: float = DEFAULT_FIT_TOLERANCE,
    on_result=None,
    should_cancel=None,
) -> list[FitResult]:
    scale = estimate_dataset_scale(frequencies, z_data)
    overrides = parameter_overrides_by_circuit or {}
    results = []
    for circuit_string in circuits:
        if should_cancel is not None and should_cancel():
            break
        result = fit_circuit(
            frequencies,
            z_data,
            circuit_string,
            scale,
            parameter_overrides=overrides.get(circuit_string),
            max_fit_evaluations=max_fit_evaluations,
            fit_tolerance=fit_tolerance,
        )
        results.append(result)
        if on_result is not None:
            on_result(result)
    return results


def lin_kk_check(
    frequencies,
    z_data,
    n_rc: int | None = None,
    cutoff_mu: float = 0.85,
    max_rc: int = 50,
    fit_type: str = "complex",
) -> KramersKronigResult:
    """Run the impedance.py Lin-KK consistency check from Schoenleber et al.

    This is a practical Kramers-Kronig validity test for finite EIS spectra, not a
    formal integral transform over the ideal 0..infinity frequency range.
    """
    try:
        frequencies = np.asarray(frequencies, dtype=float)
        z_data = np.asarray(z_data, dtype=complex)
        mask = np.isfinite(frequencies) & np.isfinite(z_data.real) & np.isfinite(z_data.imag) & (frequencies > 0)
        frequencies = frequencies[mask]
        z_data = z_data[mask]
        if len(frequencies) < 8:
            return KramersKronigResult(
                success=False,
                status="FAIL",
                flags=("FAIL:kk_too_few_points",),
                error_message="Kramers-Kronig check needs at least 8 valid frequency points.",
            )

        order = np.argsort(frequencies)
        frequencies = frequencies[order]
        z_data = z_data[order]
        unique_frequencies, unique_index = np.unique(frequencies, return_index=True)
        frequencies = unique_frequencies
        z_data = z_data[unique_index]
        if len(frequencies) < 8:
            return KramersKronigResult(
                success=False,
                status="FAIL",
                flags=("FAIL:kk_too_few_unique_frequencies",),
                error_message="Kramers-Kronig check needs at least 8 unique frequency points.",
            )

        max_m = int(n_rc) if n_rc is not None else int(max_rc)
        cutoff = None if n_rc is not None else float(cutoff_mu)
        with contextlib.redirect_stdout(io.StringIO()):
            n_rc, mu, z_fit, residual_real, residual_imag = impedance_validation.linKK(
                frequencies,
                z_data,
                c=cutoff,
                max_M=max_m,
                fit_type=fit_type,
            )
        residual = z_data - z_fit
        relative_error = np.abs(residual) / np.maximum(np.abs(z_data), 1e-30) * 100
        rmse_percent = float(np.sqrt(np.mean(relative_error**2)))
        max_error_percent = float(np.max(relative_error))

        flags = []
        if rmse_percent > 5.0:
            flags.append("FAIL:kk_rmse_gt_5pct")
        elif rmse_percent > 2.0:
            flags.append("WARN:kk_rmse_gt_2pct")
        if max_error_percent > 20.0:
            flags.append("FAIL:kk_max_error_gt_20pct")
        elif max_error_percent > 10.0:
            flags.append("WARN:kk_max_error_gt_10pct")
        if cutoff is not None and mu > cutoff_mu and n_rc >= max_rc:
            flags.append("WARN:kk_mu_cutoff_not_reached")

        status = "PASS"
        if any(flag.startswith("FAIL:") for flag in flags):
            status = "FAIL"
        elif flags:
            status = "WARN"

        return KramersKronigResult(
            success=True,
            status=status,
            rmse_percent=rmse_percent,
            max_error_percent=max_error_percent,
            mu=float(mu),
            n_rc=n_rc,
            frequencies=frequencies,
            z_fit=z_fit,
            residual_real=residual_real,
            residual_imag=residual_imag,
            relative_error_percent=relative_error,
            flags=tuple(flags),
        )
    except Exception as exc:
        return KramersKronigResult(success=False, status="FAIL", flags=("FAIL:kk_error",), error_message=str(exc))


def choose_best_result(results: Iterable[FitResult], max_param_error: float = 40.0) -> FitResult:
    successful = [result for result in results if result.success]
    if not successful:
        raise ValueError("No circuit fits succeeded.")

    candidates = [result for result in successful if result.status != "BAD"]
    if not candidates:
        candidates = [result for result in successful if result.max_param_error < max_param_error]
    if not candidates:
        candidates = successful

    return min(candidates, key=lambda result: (result.bic, result.n_params, result.mean_fit_error))


def information_criteria(rss: float, n_observations: int, n_params: int) -> tuple[float, float]:
    safe_rss = max(float(rss), 1e-300)
    n = max(int(n_observations), 1)
    k = max(int(n_params), 1)
    log_likelihood_term = n * np.log(safe_rss / n)
    return float(log_likelihood_term + 2 * k), float(log_likelihood_term + k * np.log(n))


def physical_flags(
    circuit_string: str,
    parameters,
    confidences,
    low_bounds,
    high_bounds,
    max_param_error: float,
) -> list[str]:
    flags = []
    names = parameter_names(circuit_string)

    if not np.isfinite(max_param_error):
        flags.append("BAD:nonfinite_confidence")
    elif max_param_error > 200:
        flags.append("BAD:param_uncertainty_gt_200pct")
    elif max_param_error > 40:
        flags.append("WARN:param_uncertainty_gt_40pct")

    for name, value, confidence, low, high in zip(names, parameters, confidences, low_bounds, high_bounds):
        if not np.isfinite(value):
            flags.append(f"BAD:{name}_nonfinite")
            continue

        if is_near_lower_bound(value, low, high):
            flags.append(f"WARN:{name}_near_lower_bound")
        if is_near_upper_bound(value, low, high):
            flags.append(f"WARN:{name}_near_upper_bound")

        if name.startswith("CPE") and name.endswith("_1"):
            if value < 0.55:
                flags.append(f"WARN:{name}_alpha_near_lower_limit")
            elif value < 0.70:
                flags.append(f"WARN:{name}_alpha_low")
            elif value > 0.995:
                flags.append(f"WARN:{name}_alpha_near_ideal")

        if confidence is not None and value != 0 and np.isfinite(confidence):
            relative_confidence = abs(confidence / value) * 100
            if relative_confidence > 200:
                flags.append(f"BAD:{name}_uncertainty_gt_200pct")
            elif relative_confidence > 40:
                flags.append(f"WARN:{name}_uncertainty_gt_40pct")

    return deduplicate_flags(flags)


def classify_fit(flags: Iterable[str]) -> str:
    flags = tuple(flags)
    if any(flag.startswith("BAD:") for flag in flags):
        return "BAD"
    if any(flag.startswith("WARN:") for flag in flags):
        return "WARN"
    return "OK"


def is_near_lower_bound(value: float, low: float, high: float) -> bool:
    if low > 0 and high > low and value > 0:
        log_span = np.log10(high) - np.log10(low)
        if log_span > 2:
            return (np.log10(value) - np.log10(low)) / log_span < 0.02
    span = max(abs(high - low), 1e-300)
    return abs(value - low) / span < 1e-4


def is_near_upper_bound(value: float, low: float, high: float) -> bool:
    if low > 0 and high > low and value > 0:
        log_span = np.log10(high) - np.log10(low)
        if log_span > 2:
            return (np.log10(high) - np.log10(value)) / log_span < 0.02
    span = max(abs(high - low), 1e-300)
    return abs(high - value) / span < 1e-4


def deduplicate_flags(flags: Iterable[str]) -> list[str]:
    seen = set()
    result = []
    for flag in flags:
        if flag not in seen:
            seen.add(flag)
            result.append(flag)
    return result
