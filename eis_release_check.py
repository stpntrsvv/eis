"""Воспроизводимая приёмочная проверка кандидата EIS Solver v1."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import time

from eis_version import RELEASE_CHANNEL, __version__


ROOT = Path(__file__).resolve().parent
DEFAULT_SAMPLE = ROOT / "double very good eis.txt"
DEFAULT_BIOLOGIC_SAMPLE = ROOT / "sample_data" / "EIS_latin1.mpt"
DEFAULT_CIRCUIT = "R0-p(R1,CPE0)-p(R2,CPE1)"
RELEASE_FILES = (
    "LICENSE",
    "README.md",
    "CITATION.cff",
    "CITATION.md",
    "THIRD_PARTY_NOTICES.md",
)


@dataclass
class CheckResult:
    name: str
    status: str
    seconds: float
    details: dict


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _run_process(command, *, env=None, timeout=300) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(item) for item in command],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _process_check(name, command, *, env=None, timeout=300, inspect=None):
    started = time.monotonic()
    try:
        completed = _run_process(command, env=env, timeout=timeout)
        details = {
            "command": [str(item) for item in command],
            "return_code": completed.returncode,
            "stdout_tail": completed.stdout[-2000:],
            "stderr_tail": completed.stderr[-2000:],
        }
        passed = completed.returncode == 0
        if passed and inspect is not None:
            extra = inspect(completed)
            if extra:
                details.update(extra)
        return CheckResult(
            name=name,
            status="passed" if passed else "failed",
            seconds=time.monotonic() - started,
            details=details,
        )
    except Exception as exc:
        return CheckResult(
            name=name,
            status="failed",
            seconds=time.monotonic() - started,
            details={"error": str(exc), "command": [str(item) for item in command]},
        )


def _discover_ngspice(explicit: str | None) -> str | None:
    if explicit:
        return explicit
    found = shutil.which("ngspice_con") or shutil.which("ngspice")
    if found:
        return found
    candidates = (
        ROOT.parent / ".runtime" / "ngspice-46" / "Spice64" / "bin" / "ngspice_con.exe",
        ROOT / ".runtime" / "ngspice-46" / "Spice64" / "bin" / "ngspice_con.exe",
    )
    return str(next((path for path in candidates if path.is_file()), "")) or None


def _discover_gcc(explicit: str | None) -> str | None:
    if explicit:
        return explicit
    return shutil.which("gcc")


def _release_files_check(name: str, root: Path, *, recursive: bool = False) -> CheckResult:
    started = time.monotonic()
    found = {}
    for filename in RELEASE_FILES:
        if recursive:
            match = next((path for path in root.rglob(filename) if path.is_file()), None)
        else:
            candidate = root / filename
            match = candidate if candidate.is_file() else None
        found[filename] = str(match) if match else None
    missing = [filename for filename, path in found.items() if path is None]
    return CheckResult(
        name=name,
        status="failed" if missing else "passed",
        seconds=time.monotonic() - started,
        details={"root": str(root), "files": found, "missing": missing},
    )


def _packaged_metadata_root(packaged_exe: Path) -> Path:
    """Return the folder that owns bundled release metadata."""
    executable_dir = packaged_exe.parent
    contents_dir = executable_dir.parent
    app_bundle = contents_dir.parent
    if (
        executable_dir.name == "MacOS"
        and contents_dir.name == "Contents"
        and app_bundle.suffix == ".app"
    ):
        return app_bundle
    return executable_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the EIS Solver v1 release-candidate acceptance checks."
    )
    parser.add_argument("--sample", default=str(DEFAULT_SAMPLE))
    parser.add_argument("--ngspice")
    parser.add_argument("--gcc")
    parser.add_argument("--packaged-exe")
    parser.add_argument("--biologic-sample", default=str(DEFAULT_BIOLOGIC_SAMPLE))
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--require-spice", action="store_true")
    parser.add_argument("--require-gcc", action="store_true")
    parser.add_argument("--require-packaged", action="store_true")
    parser.add_argument("--output", help="Write the strict JSON release passport here.")
    return parser


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    sample = Path(args.sample).resolve()
    if not sample.is_file():
        print(f"Release check error: sample not found: {sample}", file=sys.stderr)
        return 2

    python = Path(sys.executable)
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["QT_QPA_PLATFORM"] = "offscreen"
    checks: list[CheckResult] = []

    checks.append(_release_files_check("release_metadata", ROOT))

    if not args.skip_tests:
        checks.append(_process_check(
            "automated_tests",
            [python, "-m", "unittest", "discover", "-s", "tests"],
            env=environment,
            timeout=900,
        ))

    checks.append(_process_check(
        "gui_offscreen_start",
        [
            python,
            "-c",
            (
                "from PySide6.QtWidgets import QApplication;"
                "from eis_qt import EisQtApp;"
                "app=QApplication([]);window=EisQtApp();"
                "assert window.windowTitle().startswith('EIS Solver ');"
                "window.close();print('gui-ok')"
            ),
        ],
        env=environment,
        timeout=120,
    ))

    packaged_exe = Path(args.packaged_exe).resolve() if args.packaged_exe else None
    if packaged_exe and packaged_exe.is_file():
        checks.append(_release_files_check(
            "packaged_release_metadata",
            _packaged_metadata_root(packaged_exe),
            recursive=True,
        ))
        checks.append(_process_check(
            "packaged_generic_smoke",
            [packaged_exe, "--release-smoke", sample],
            timeout=120,
        ))
        biologic_sample = Path(args.biologic_sample).resolve()
        if biologic_sample.is_file():
            checks.append(_process_check(
                "packaged_biologic_smoke",
                [packaged_exe, "--release-smoke", biologic_sample],
                timeout=120,
            ))
        else:
            checks.append(CheckResult(
                name="packaged_biologic_smoke",
                status="failed" if args.require_packaged else "skipped",
                seconds=0.0,
                details={"reason": f"BioLogic sample not found: {biologic_sample}"},
            ))
    else:
        checks.append(CheckResult(
            name="packaged_application",
            status="failed" if args.require_packaged else "skipped",
            seconds=0.0,
            details={"reason": "packaged executable not provided or not found"},
        ))

    with tempfile.TemporaryDirectory(prefix="eis-release-check-") as temp_dir:
        temporary = Path(temp_dir)
        analysis_json = temporary / "analysis.json"
        checks.append(_process_check(
            "cli_single_file_analysis",
            [
                python,
                ROOT / "eis_cli.py",
                sample,
                "--circuit",
                DEFAULT_CIRCUIT,
                "--format",
                "json",
                "--output",
                analysis_json,
                "--quiet",
            ],
            env=environment,
            timeout=300,
            inspect=lambda _completed: {
                "analysis": {
                    key: value
                    for key, value in json.loads(
                        analysis_json.read_text(encoding="utf-8")
                    ).items()
                    if key in {"success", "stage", "point_count", "kk", "best"}
                }
            },
        ))

        controller_package = temporary / "controller-package"
        controller_check = _process_check(
            "controller_package",
            [
                python,
                ROOT / "eis_cli.py",
                sample,
                "--circuit",
                DEFAULT_CIRCUIT,
                "--controller-export",
                controller_package,
                "--sample-period-us",
                "100",
                "--current-full-scale-a",
                "1",
                "--quiet",
            ],
            env=environment,
            timeout=300,
            inspect=lambda _completed: {
                "files": sorted(path.name for path in controller_package.iterdir()),
                "passport_status": json.loads(
                    (controller_package / "passport.json").read_text(encoding="utf-8")
                )["status"],
            },
        )
        checks.append(controller_check)

        gcc = _discover_gcc(args.gcc)
        if gcc and controller_check.status == "passed":
            for source in ("eis_model_f32.c", "eis_model_q31.c"):
                checks.append(_process_check(
                    f"compile_{source.removesuffix('.c')}",
                    [
                        gcc,
                        "-std=c99",
                        "-Wall",
                        "-Wextra",
                        "-Werror",
                        "-c",
                        controller_package / source,
                        "-o",
                        temporary / f"{source}.o",
                    ],
                    timeout=120,
                ))
        else:
            checks.append(CheckResult(
                name="controller_c_compiler",
                status="failed" if args.require_gcc else "skipped",
                seconds=0.0,
                details={"reason": "gcc not found" if not gcc else "package failed"},
            ))

        ngspice = _discover_ngspice(args.ngspice)
        if ngspice:
            spice_package = temporary / "spice-package"
            checks.append(_process_check(
                "spice_package",
                [
                    python,
                    ROOT / "eis_cli.py",
                    sample,
                    "--circuit",
                    DEFAULT_CIRCUIT,
                    "--spice-export",
                    spice_package,
                    "--ngspice",
                    ngspice,
                    "--quiet",
                ],
                env=environment,
                timeout=300,
                inspect=lambda _completed: {
                    "files": sorted(path.name for path in spice_package.iterdir()),
                    "passport_status": json.loads(
                        (spice_package / "passport.json").read_text(encoding="utf-8")
                    )["status"],
                    "model_sha256": _sha256(spice_package / "model.lib"),
                },
            ))
        else:
            checks.append(CheckResult(
                name="spice_package",
                status="failed" if args.require_spice else "skipped",
                seconds=0.0,
                details={"reason": "ngspice not found"},
            ))

    failed = [check.name for check in checks if check.status == "failed"]
    passport = {
        "schema_version": 1,
        "artifact_type": "eis_solver_release_acceptance",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "version": __version__,
        "release_channel": RELEASE_CHANNEL,
        "status": "passed" if not failed else "failed",
        "environment": {
            "python": sys.version,
            "executable": str(python),
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "source": {
            "sample": str(sample),
            "sample_sha256": _sha256(sample),
        },
        "checks": [asdict(check) for check in checks],
        "failed_checks": failed,
    }
    encoded = json.dumps(passport, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if not failed else 1


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
