"""Command-line interface for single-file inspection and batch EIS analysis."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import sys

os.environ["MPLCONFIGDIR"] = os.path.join(os.path.dirname(__file__), ".matplotlib")

from eis_core import (
    DEFAULT_CIRCUITS,
    DIFFUSION_CIRCUITS,
    INDUCTIVE_CIRCUITS,
    INTERFACE_CIRCUITS,
    SIMPLE_CIRCUITS,
)
from eis_pipeline import AnalysisResult, analyze_file, discover_input_files, dumps_result
from eis_io import load_eis_file
from eis_version import __version__
from eis_controller import ControllerExportRefused, export_controller_package
from eis_spice_export import SpiceExportRefused, export_spice_package


EXIT_OK = 0
EXIT_INTERNAL_ERROR = 1
EXIT_ARGUMENT_ERROR = 2
EXIT_INPUT_FAILURE = 3
EXIT_FIT_FAILURE = 4
EXIT_EXPORT_FAILURE = 5

PRESETS = {
    "auto": None,
    "simple": SIMPLE_CIRCUITS,
    "interface": INTERFACE_CIRCUITS,
    "diffusion": DIFFUSION_CIRCUITS,
    "inductive": INDUCTIVE_CIRCUITS,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze one EIS file or a batch of files without the GUI.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"EIS Solver {__version__}")
    parser.add_argument("inputs", nargs="*", help="Files or directories to analyze.")
    parser.add_argument("--recursive", action="store_true", help="Search input directories recursively.")
    parser.add_argument("--channel", help="Impedance channel: Z, Z1, Z2, Zce, Zstack or Zwe-ce.")
    parser.add_argument("--preset", choices=sorted(PRESETS), default="auto", help="Circuit family to fit.")
    parser.add_argument("--circuit", action="append", help="Fit this circuit; repeat for multiple circuits.")
    parser.add_argument("--circuits-file", help="Text file containing one circuit per non-empty line.")
    parser.add_argument("--mode", choices=("analyze", "parse", "kk"), default="analyze")
    parser.add_argument("--max-evaluations", type=int, default=5_000, help="Optimizer budget per circuit.")
    parser.add_argument("--tolerance", type=float, default=1e-9, help="Optimizer ftol/xtol/gtol.")
    parser.add_argument("--restarts", type=int, default=1, help="Deterministic starts per circuit.")
    parser.add_argument("--restart-seed", type=int, default=0, help="Seed for multi-start guesses.")
    parser.add_argument("--format", choices=("text", "json", "jsonl", "csv"), default="text")
    parser.add_argument("--output", help="Output file, or output directory for batch artifacts.")
    parser.add_argument(
        "--spice-export",
        help="Atomically create a validated SPICE package directory for one input file.",
    )
    parser.add_argument(
        "--ngspice",
        help="Path to the ngspice console executable used by --spice-export.",
    )
    parser.add_argument(
        "--controller-export",
        help="Atomically create a validated C package with float32 and Q31 implementations.",
    )
    parser.add_argument(
        "--sample-period-us",
        type=float,
        help="Controller sample period in microseconds.",
    )
    parser.add_argument(
        "--current-full-scale-a",
        type=float,
        help="Current represented by full scale in amperes.",
    )
    parser.add_argument(
        "--controller-max-frequency-hz",
        type=float,
        help="Optional upper validation frequency for the controller model.",
    )
    parser.add_argument("--summary-only", action="store_true", help="Omit all-fit details from JSON/JSONL.")
    parser.add_argument("--fail-fast", action="store_true", help="Stop after the first failed input.")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress messages on stderr.")
    parser.add_argument("--no-plot", action="store_true", help=argparse.SUPPRESS)  # legacy compatibility
    return parser


def select_circuits(args) -> list[str] | None:
    circuits = list(args.circuit or [])
    if args.circuits_file:
        with open(args.circuits_file, encoding="utf-8") as handle:
            circuits.extend(line.strip() for line in handle if line.strip() and not line.lstrip().startswith("#"))
    if not circuits:
        preset = PRESETS[args.preset]
        if preset is None:
            return None
        circuits = list(preset)
    return list(dict.fromkeys(circuits))


def human_result(result: AnalysisResult) -> str:
    lines = [f"[{('OK' if result.success else 'ERROR')}] {result.file_path}"]
    if result.error_message:
        lines.append(f"  stage={result.stage} error={result.error_message}")
        return "\n".join(lines)
    lines.append(
        f"  format={result.source_format} channel={result.selected_channel or '-'} points={result.point_count}"
    )
    if result.kk:
        lines.append(
            f"  KK={result.kk.status} rmse={result.kk.rmse_percent:.3f}% "
            f"max={result.kk.max_error_percent:.3f}% mu={result.kk.mu:.3f}"
        )
    if result.best:
        lines.append(
            f"  best={result.best.circuit_string} status={result.best.status} "
            f"fit={result.best.mean_fit_error:.3f}% bic={result.best.bic:.3f}"
        )
        for parameter in result.to_dict(include_all_fits=False)["best"]["parameters"]:
            lines.append(
                f"    {parameter['name']}={parameter['value']} confidence={parameter['confidence']}"
            )
    lines.append(f"  fits={len(result.fits)} elapsed={result.elapsed_seconds:.3f}s")
    return "\n".join(lines)


def resolve_output_path(output: str | None, fmt: str, batch: bool) -> Path | None:
    if not output:
        return None
    path = Path(output)
    if batch or path.is_dir() or not path.suffix:
        path.mkdir(parents=True, exist_ok=True)
        name = "results.jsonl" if fmt in {"json", "jsonl"} else "summary.csv" if fmt == "csv" else "results.txt"
        return path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_results(results: list[AnalysisResult], fmt: str, output: Path | None, summary_only: bool) -> None:
    if fmt == "text":
        content = "\n\n".join(human_result(result) for result in results) + "\n"
    elif fmt == "json" and len(results) == 1:
        content = json.dumps(results[0].to_dict(include_all_fits=not summary_only), ensure_ascii=False, indent=2) + "\n"
    elif fmt in {"json", "jsonl"}:
        content = "\n".join(dumps_result(result, include_all_fits=not summary_only) for result in results) + "\n"
    else:
        rows = [result.summary_row() for result in results]
        if output is None:
            handle = sys.stdout
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["file"])
            writer.writeheader()
            writer.writerows(rows)
            return
        with output.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["file"])
            writer.writeheader()
            writer.writerows(rows)
        return

    if output is None:
        sys.stdout.write(content)
    else:
        output.write_text(content, encoding="utf-8")


def run(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.inputs:
        # Preserve the old convenient default when the repository sample exists.
        default_sample = "double very good eis.txt"
        if os.path.exists(default_sample):
            args.inputs = [default_sample]
        else:
            parser.error("at least one input file or directory is required")
    if args.max_evaluations < 1 or args.tolerance <= 0 or args.restarts < 1:
        parser.error("--max-evaluations, --tolerance and --restarts must be positive")

    try:
        files = discover_input_files(args.inputs, recursive=args.recursive)
        circuits = select_circuits(args)
    except (OSError, ValueError) as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return EXIT_INPUT_FAILURE
    if not files:
        print("Input error: no supported EIS files found.", file=sys.stderr)
        return EXIT_INPUT_FAILURE
    engineering_export = args.spice_export or args.controller_export
    if engineering_export and len(files) != 1:
        print("Engineering export error: exactly one input file is required.", file=sys.stderr)
        return EXIT_ARGUMENT_ERROR
    if engineering_export and args.mode != "analyze":
        print("Engineering export error: --mode must be analyze.", file=sys.stderr)
        return EXIT_ARGUMENT_ERROR
    if args.controller_export and (
        args.sample_period_us is None
        or args.sample_period_us <= 0
        or args.current_full_scale_a is None
        or args.current_full_scale_a <= 0
        or (
            args.controller_max_frequency_hz is not None
            and args.controller_max_frequency_hz <= 0
        )
    ):
        print(
            "Controller export error: positive --sample-period-us and "
            "--current-full-scale-a are required; the optional maximum "
            "frequency must also be positive.",
            file=sys.stderr,
        )
        return EXIT_ARGUMENT_ERROR

    output = resolve_output_path(args.output, args.format, batch=len(files) > 1)
    stream_jsonl = args.format == "jsonl" and output is not None
    if stream_jsonl:
        output.write_text("", encoding="utf-8")

    results: list[AnalysisResult] = []
    for index, file_path in enumerate(files, start=1):
        if not args.quiet:
            print(f"[{index}/{len(files)}] {file_path}", file=sys.stderr)
        result = analyze_file(
            file_path,
            channel=args.channel,
            circuits=circuits,
            max_fit_evaluations=args.max_evaluations,
            fit_tolerance=args.tolerance,
            fit_restarts=args.restarts,
            restart_seed=args.restart_seed,
            mode=args.mode,
        )
        results.append(result)
        if stream_jsonl:
            with output.open("a", encoding="utf-8") as handle:
                handle.write(dumps_result(result, include_all_fits=not args.summary_only) + "\n")
        if args.fail_fast and not result.success:
            break

    try:
        if not stream_jsonl:
            write_results(results, args.format, output, args.summary_only)
    except OSError as exc:
        print(f"Output error: {exc}", file=sys.stderr)
        return EXIT_INTERNAL_ERROR

    failures = [result for result in results if not result.success]
    if failures:
        return EXIT_FIT_FAILURE if all(result.stage == "fit" for result in failures) else EXIT_INPUT_FAILURE
    dataset = None
    if engineering_export:
        try:
            dataset = load_eis_file(files[0], channel=args.channel)
        except (OSError, ValueError) as exc:
            print(f"Engineering export refused: {exc}", file=sys.stderr)
            return EXIT_EXPORT_FAILURE
    if args.spice_export:
        try:
            package = export_spice_package(
                results[0],
                dataset.frequencies,
                args.spice_export,
                source_file=files[0],
                ngspice_executable=args.ngspice,
            )
        except (OSError, ValueError, SpiceExportRefused) as exc:
            print(f"SPICE export refused: {exc}", file=sys.stderr)
            return EXIT_EXPORT_FAILURE
        if not args.quiet:
            print(
                f"SPICE package validated: {package.package_directory}",
                file=sys.stderr,
            )
    if args.controller_export:
        try:
            package = export_controller_package(
                results[0],
                dataset.frequencies,
                args.controller_export,
                sample_period_s=args.sample_period_us * 1e-6,
                current_full_scale_a=args.current_full_scale_a,
                max_frequency_hz=args.controller_max_frequency_hz,
                source_file=files[0],
            )
        except (OSError, ValueError, ControllerExportRefused) as exc:
            print(f"Controller export refused: {exc}", file=sys.stderr)
            return EXIT_EXPORT_FAILURE
        if not args.quiet:
            print(
                f"Controller C package validated: {package.package_directory}",
                file=sys.stderr,
            )
    return EXIT_OK


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
