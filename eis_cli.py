import argparse
import os
from pprint import pformat
import warnings

os.environ.setdefault("MPLCONFIGDIR", os.path.join(os.path.dirname(__file__), ".matplotlib"))

import matplotlib.pyplot as plt
import numpy as np

from eis_core import (
    DEFAULT_CIRCUITS,
    choose_best_result,
    circuit_to_readable,
    estimate_dataset_scale,
    fit_circuits,
    lin_kk_check,
)
from eis_io import load_eis_file

warnings.filterwarnings("ignore")


def safe_console_text(value) -> str:
    text = pformat(value, compact=True, width=120)
    return text.encode("ascii", errors="backslashreplace").decode("ascii")


def main():
    parser = argparse.ArgumentParser(description="Run EIS equivalent-circuit auto fitting.")
    parser.add_argument("file", nargs="?", default="double very good eis.txt")
    parser.add_argument("--no-plot", action="store_true", help="Print fit results without opening a plot.")
    parser.add_argument("--channel", help="Impedance channel to load, e.g. Z, Z1, Z2, Zce, Zstack, Zwe-ce.")
    args = parser.parse_args()

    dataset = load_eis_file(args.file, channel=args.channel)
    frequencies = dataset.frequencies
    z_experimental = dataset.z
    scale = estimate_dataset_scale(frequencies, z_experimental)

    print("Dataset loaded")
    print(f"Source format: {dataset.source_format}")
    print(f"Columns: {', '.join(dataset.columns)}")
    if dataset.metadata:
        compact_metadata = {
            key: value
            for key, value in dataset.metadata.items()
            if key not in {"comments"}
        }
        print(f"Parser metadata: {safe_console_text(compact_metadata)}")
    print(
        f"Scale guess: R0 ~= {scale.r0:.1f} Ohm, "
        f"R_transfer ~= {scale.r_transfer:.1f} Ohm, C ~= {scale.capacitance:.2e} F"
    )

    kk = lin_kk_check(frequencies, z_experimental)
    print("\n=== Kramers-Kronig check ===")
    if kk.success:
        print(
            f"Status: {kk.status}; RMSE={kk.rmse_percent:.3f}%; "
            f"max={kk.max_error_percent:.3f}%; "
            f"mu={kk.mu:.3f}; "
            f"n_rc={kk.n_rc}"
        )
    else:
        print(f"Status: {kk.status}; {kk.error_message}")
    print(f"Flags: {', '.join(kk.flags) if kk.flags else '-'}")

    print("\n=== Circuit selector ===")

    results = fit_circuits(frequencies, z_experimental, DEFAULT_CIRCUITS)
    for result in results:
        if result.success:
            print(
                f"[{result.status:<4}] {result.circuit_string:40} "
                f"fit={result.mean_fit_error:.3f}% "
                f"bic={result.bic:.2f} "
                f"time={result.elapsed_seconds:.3f}s "
                f"max_param_error={result.max_param_error:.1f}% "
                f"flags={','.join(result.flags) if result.flags else '-'}"
            )
        else:
            print(
                f"[{result.status}] {result.circuit_string:40} "
                f"time={result.elapsed_seconds:.3f}s {result.error_message}"
            )

    best = choose_best_result(results)
    print("\n=== Best circuit ===")
    print(f"Circuit: {best.circuit_string}")
    print(f"Readable: {circuit_to_readable(best.circuit_string)}")
    print(f"Mean fit error: {best.mean_fit_error:.3f}%")
    print(f"Max parameter error: {best.max_param_error:.2f}%")
    print(f"AIC: {best.aic:.3f}")
    print(f"BIC: {best.bic:.3f}")
    print(f"Status: {best.status}")
    print(f"Flags: {', '.join(best.flags) if best.flags else '-'}")
    print(best.model)

    if args.no_plot:
        return

    f_grid = np.logspace(np.log10(frequencies.min()), np.log10(frequencies.max()), 500)
    z_best_pred = best.model.predict(f_grid)

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.plot(z_experimental.real, -z_experimental.imag, "o", color="royalblue", label="Experiment")
    ax.plot(z_best_pred.real, -z_best_pred.imag, "-", color="crimson", lw=2.5, label=f"Fit: {best.circuit_string}")
    ax.set_xlabel("Re(Z) [Ohm]")
    ax.set_ylabel("-Im(Z) [Ohm]")
    ax.set_title(f"Auto-fit for {args.file}", fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.axis("equal")
    ax.legend()
    plt.show()


if __name__ == "__main__":
    main()
