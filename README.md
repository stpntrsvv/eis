# EIS Solver Lab Journal

This README is the compact project journal. Future AI chats should read the
current operational brief in
[`docs/EIS Solver Vault/AI Handoff.md`](docs/EIS%20Solver%20Vault/AI%20Handoff.md)
before changing the inference engine.

## TL;DR For The Next Chat

This project analyzes electrochemical impedance spectroscopy (EIS) data, fits equivalent circuits with `impedance.models.circuits.CustomCircuit`, plots Nyquist curves, and saves fit reports.

Current baseline value: the EIS circuit optimizer. The old `cycling.py` file is legacy/scrap from the same repo and is not the foundation for the future app.

Current architecture direction:

- `eis_core.py` - clean fitting core: circuit lists, scale estimate, bounds/initial guess, fit loop, best-model selection.
- `eis_io.py` - active EIS file loading layer with SmartStat/generic text plus BioLogic `.mpr/.mpt` support through `galvani`.
- `eis_utils.py` - compatibility wrapper for old imports.
- `eis_cli.py` - CLI entrypoint.
- `eis_qt.py` - active desktop GUI entrypoint based on PySide6/Qt.
- `eis_app.py` - legacy launch wrapper that redirects old GUI launches to `eis_qt.py`.
- `eis.py` - legacy CLI script kept for behavior comparison.
- `eis_desktop.py` - removed customtkinter prototype.

## Run Commands

CLI:

```bash
.venv\Scripts\python.exe eis_cli.py "double very good eis.txt" --no-plot
.venv\Scripts\python.exe eis_cli.py "file.mpr" --channel Z1 --no-plot
.venv\Scripts\python.exe eis_cli.py sample_data --recursive --format jsonl --output artifacts\sample_batch
.venv\Scripts\python.exe eis_cli.py dataset.csv --preset interface --format json --output result.json
```

The headless CLI accepts one or more files/directories, continues after bad inputs by default, and supports `text`, `json`, `jsonl`, and `csv` output. JSONL output is appended after every completed file so interrupted batch runs keep partial results. The default `--preset auto` now routes each spectrum to physically plausible circuit families and records its evidence in `metadata.circuit_routing`; named presets and `--circuit` remain fixed and reproducible. Use `--mode parse` or `--mode kk` to isolate input and data-validity checks, and `--fail-fast` when early termination is desired.

GUI:

```bash
.venv\Scripts\python.exe eis_qt.py
python eis_qt.py
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Known environment note: global `python.exe` / `py -3` is broken on this machine, but the repo venv works. Prefer `.venv\Scripts\python.exe ...`.

Build Windows folder executable:

```bash
.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm eis_app.spec
```

Build output:

```text
dist\eis_qt\eis_qt.exe
```

## Obsidian Documentation

The long-form human documentation lives in:

```text
docs/EIS Solver Vault/
```

Open that folder in Obsidian as a vault. Start with `00 Start Here.md`.

The vault now has a Russian dashboard, an Obsidian Canvas map (`EIS Solver Map.canvas`), Mermaid diagrams, Dataview-friendly blocks, user workflows, architecture notes, scientific-model notes, export contracts, validation status, decision logs, physical/model-validity notes, and a future Chem Suite roadmap.

Scientific playbook pages:

- `11 EIS Physical Cookbook.md`
- `12 Fitting Math Notes.md`
- `13 Model Validity Checklist.md`
- `14 Known Failure Modes.md`
- `15 Parameter Meaning Library.md`
- `16 Decision Log.md`
- `17 Chem Suite Philosophy.md`
- `18 Теория - основы импедансной спектроскопии.md`
- `19 Nyquist и Bode - чтение спектров.md`
- `20 Реальные системы - CPE, Warburg и неоднозначность схем.md`
- `21 Экспериментальная практика и артефакты.md`
- `22 Transport Properties From EIS.md`
- `23 Kramers-Kronig Validation.md`
- `24 Глоссарий.md`
- `26 Где лежит истина - статистический вывод и иерархический EIS.md`

The source PDF `Introductory impedance spectroscopy.pdf` is treated as local reference material and is ignored by git. The notes are Russian project-oriented summaries, not a verbatim copy.

## Baseline Behavior

1. EIS files are loaded from the first three numeric columns:
   `frequency`, `Re(Z)`, `Im(Z)`.
2. If `Im(Z)` is mostly positive, its sign is flipped so `-Im(Z)` plots upward in the usual Nyquist view.
3. Dataset scale is estimated from geometry:
   `R0 = min(Re)`, `R_transfer = max(Re) - min(Re)`, `C` from the frequency at the largest arc height.
4. `initial_guess` and `bounds` are generated for every circuit.
5. Models are fitted with `CustomCircuit.fit(..., weight_by_modulus=True)`.
6. The selector rejects `BAD` when possible, finds the minimum BIC, treats `ΔBIC <= 2` as statistically comparable, and then prefers the simpler/better-status model.
7. BioLogic `.mpr` and `.mpt` files are loaded through `galvani`; only files containing EIS columns are accepted.
8. Model selection uses weighted residual diagnostics plus AIC/BIC. BIC evidence is evaluated before `OK/WARN`; status cannot overrule a decisively better BIC, but it breaks ties inside the `ΔBIC <= 2` support window.
9. Fit status is diagnostic, not absolute truth:
   `OK` means no current warnings, `WARN` means inspect flags/residuals, `BAD` means severe non-identifiability or invalid parameters.
10. Kramers-Kronig/Lin-KK consistency is checked on load. It is a data-quality gate (`PASS`, `WARN`, `FAIL`), not a replacement for equivalent-circuit fitting.

## Circuits

Circuit lists live in `eis_core.py`:

- `IDEAL_RC_CIRCUITS`
- `INTERFACE_CIRCUITS`
- `DIFFUSION_CIRCUITS`
- `SIMPLE_CIRCUITS`
- `ADVANCED_CIRCUITS`
- `BASIC_CIRCUITS`
- `INDUCTIVE_CIRCUITS`
- `DEFAULT_CIRCUITS`

Supported elements in `build_bounds_and_guess()`:

- `R`
- `C`
- `CPE`
- `W`
- `Wo`
- `Ws`
- `L`

`L` support was added in the new core because old GUI listed inductive circuits but did not provide guesses/bounds for inductors, so those fits could silently fail.

## Important Files

`eis_io.py`:

- Active parser layer.
- Returns `EisDataset(file_path, frequencies, z, source_format, columns, metadata)`.
- Supports `.mpr` BioLogic binaries via `galvani.BioLogic.MPRfile`.
- Supports `.mpt` BioLogic exports via `galvani.BioLogic.MPTfile` with encoding fallbacks.
- Supports generic SmartStat/text files as a fallback.
- Detects impedance channels such as `Z`, `Zce`, `Zstack`, `Zwe-ce`, `Z1`, and `Z2` when matching Re/Im columns exist.

`eis_core.py`:

- Main place for optimizer logic.
- Add circuit families here.
- Add or tune bounds here.
- Contains `lin_kk_check()` and `KramersKronigResult` for the `impedance.validation.linKK` data-validity gate.
- Keep GUI-independent.
- Circuit families are split into ideal RC, interface/charge-transfer, diffusion, inductive, advanced, and full auto-fit lists.

`eis_cli.py`:

- Headless single-file and batch interface over `eis_pipeline.py`.
- Accepts files and directories, recursive discovery, circuit presets/manual circuits, optimizer budgets, and parse/KK-only modes.
- Exports stable schema-versioned JSON/JSONL plus CSV summaries and returns explicit process exit codes.

`eis_pipeline.py`:

- GUI-independent orchestration layer for loading, Lin-KK, fitting, best-model selection, timing, and failures.
- Provides `AnalysisResult`, `analyze_file()`, input discovery, and JSON-safe serialization.
- Intended as the shared foundation for dataset stress tests, CLI automation, and future interfaces.

`eis_series.py`:

- First series-level layer over JSONL results: infers current LG/21700 series metadata, measures topology stability, KK/status distributions, and parameter trajectories over SOC.
- Pools candidate-model evidence across a series, selects a shared topology within a robust non-BAD coverage window, and smooths positive SOC parameter trajectories on a log scale.

`eis_joint.py`:

- Opt-in raw-spectrum joint fitting for an explicitly declared `file,soc` manifest; it preserves independent results and regularizes SOC parameter paths without changing single-file analysis.

`eis_uncertainty.py`:

- Opt-in centered complex residual bootstrap and weighted profile-likelihood intervals for a chosen spectrum/circuit.

`eis_drt.py`:

- Topology-independent non-negative ridge DRT with hidden-frequency regularization selection and measured-band peak flags.

`eis_resolution.py`:

- Synthetic frequency-window/noise resolution maps that distinguish a short measurement band from a localized repeatability or model-mismatch problem.

`eis_inference.py`:

- Unified `fast`/`reliable` decision engine returning separate statistical and reliable recommendations, resolved time regions, localized information gaps, and next-measurement advice.

`eis_inference_batch.py`:

- Streaming directory/file batch inference to compact or full JSONL and flat CSV; failures are persisted per file and do not stop the corpus by default.
- The compact v1 contract is frozen in `schemas/inference-summary-v1.schema.json`.
- Compact JSONL/CSV summaries expose nullable calibrated diffusion-gate
  status, thresholds, and the observed family ΔBIC without breaking schema v1.
- The desktop GUI can import a full reliable-inference JSON and display the
  calibrated family recommendation without reimplementing decision math.
- Parameter intervals are not yet coverage-calibrated: the first frozen
  truth-aware pilot measured substantial undercoverage, so parameter
  identification labels remain benchmark-only.
- This is diagnostic groundwork, not yet a hierarchical Bayesian fit.

`eis_qt.py`:

- Active GUI direction.
- PySide6/Qt shell over `eis_core.py`.
- Contains multi-file loading controls, a dataset summary table, an all-model fit table for the selected dataset, Nyquist and Bode plots, and a best-parameter table.
- Provides draggable horizontal and vertical splitters for resizing the control area, dataset/results tables, log, plot tabs, and Parser details.
- Includes a Residuals tab with Re/Im residuals and relative residual magnitude vs frequency.
- Includes a KK Check tab with Lin-KK RC reconstruction, relative error vs frequency, and PASS/WARN/FAIL status.
- Includes a Parser tab with source format, selected channel, selected columns, full column list, and parser metadata.
- Provides an impedance-channel dropdown when multiple channels are detected.
- Multi-analysis runs in a Qt worker thread with per-circuit progress and cooperative cancel controls. Cancel takes effect after the current circuit finishes.
- Provides two circuit preset menus: `Interface` for ideal RC/CPE/charge-transfer/two-arc models and `Transport` for Warburg/diffusion/inductive models.
- `Run selected` fits the chosen preset union; `Run auto-fit` still fits the full default circuit list for lazy/complete screening.
- The preset menus and manual circuit input live behind `Pro mode`; the default workflow only exposes file loading, auto-fit, cancel, and export.
- Manual circuit mode accepts one `impedance.py` circuit string and includes a `?` help button with syntax examples.
- Manual circuit mode can fill and edit `Initial`, `Lower`, and `Upper` parameter values before fitting.
- `Open folder` recursively loads supported `.mpr`, `.mpt`, `.txt`, `.csv`, and `.dat` files for batch analysis.
- Drag-and-drop accepts supported files and folders directly on the main window.
- Pro manual circuit/bounds presets are saved locally to the user's config folder, normally `%APPDATA%\EIS Solver\pro_presets.json` on Windows. If that is not writable, the app falls back to `.eis_solver_user/pro_presets.json`.
- `Export...` opens a type picker and writes CSV tables plus optional selected-report plots/text from one chosen base name.
- Export outputs include `_summary.csv`, `_all_results.csv`, `_best_parameters.csv`, `_parser_metadata.csv`, `_kk_check.csv`, optional `_workbook.xlsx`, and optional selected `_report.txt`, `_nyquist.png`, `_bode.png`, `_residuals.png`, `_kk_check.png`.
- `View -> Language` switches the main GUI between English and Russian. Data/export column names and circuit strings remain stable.
- `Help -> About / Guide` opens a workflow guide covering quick auto-fit, Pro mode, manual circuits, diagnostics, export, and supported file formats.

## Electrochemical Model Map

- Use ideal `C` only for a clean first-pass RC sanity check. Real porous/rough electrodes usually need `CPE`.
- `R0-p(R1,CPE0)` is the common Randles-like charge-transfer baseline: solution resistance plus double-layer/interface response.
- Two-arc models are for film/SEI/coating plus charge-transfer processes, or two time constants in the electrode.
- Warburg elements (`W`, `Wo`, `Ws`) are for diffusion/transport tails, especially low-frequency 45-degree behavior or finite-length diffusion.
- Inductive models (`L0-...`) are for low-frequency inductive loops or wiring/fixture artifacts; they should be used deliberately, not as the default explanation.

`eis_utils.py`:

- Compatibility wrapper for legacy imports.
- `load_any_eis_file()` now delegates to `eis_io.load_eis_file()`.

`cycling.py`:

- Legacy only.
- Do not start future EIS work from this file.

## Technical Debt

- `eis.py` duplicates old optimizer logic.
- `eis_app.py` is now only a legacy wrapper for `eis_qt.py`; the old customtkinter code below the wrapper is not executed.
- `eis_desktop.py` was removed after the PySide6 migration.
- `eis_utils.py` still contains old mojibake history, but its final definitions delegate to the new parser/core layer.
- `galvani` is GPL-3.0-or-later. Revisit licensing if this becomes a distributed closed-source executable.
- No formal automated test suite yet.
- Each nonlinear circuit fit has a production budget of 5,000 function evaluations with practical tolerances; the upstream `impedance.py` defaults (100,000 evaluations and `ftol=1e-13`) are intentionally not used.
- Parser cleaning rejects non-positive frequencies and median-aggregates exact duplicate frequencies while recording the operation in parser metadata.

## TODO Short List

1. Fully clean `eis_utils.py` or remove it after legacy imports are gone.
2. Convert `eis.py` into a thin wrapper around `eis_cli.py`, or remove it after behavior is confirmed.
3. Validate selectable impedance channels on real BioLogic files with Zce/Zstack/Zwe-ce/Z1/Z2 columns.
4. Expand Russian localization coverage for long help text and domain messages if needed.
5. Add parser and bounds-generation tests.
6. Add import/export for Pro preset JSON files if sharing presets between machines becomes useful.
7. Decide whether cycling/OCV analysis is needed; if yes, rebuild it as a separate module from scratch.
8. Extend the validated BioLogic `.mpr` coverage to additional instruments, channels, and multi-cycle files.

## Rules For Future AI Chats

1. Read this README first.
2. Then read `eis_core.py`.
3. Read `eis_cli.py` or `eis_qt.py` only if the task touches that entrypoint.
4. Do not begin with `cycling.py` unless the user explicitly asks for cycling analysis.
5. Treat the current fit approach as baseline working behavior.
6. Add new fitting logic to `eis_core.py`, not directly to GUI.
7. Do not hide fit errors with bare `except`; store the error text in `FitResult`.
8. Any circuit-list change starts in `DEFAULT_CIRCUITS` and `build_bounds_and_guess()`.
9. Treat `eis_qt.py` as the active GUI target. Do not reintroduce tkinter/customtkinter.

## Current Status

Journal date: 2026-07-15.

Open-data validation baseline (2026-07-17):

- added a reproducible `validation_data/` workspace with source manifest, licenses, checksums, ignored raw files/artifacts, and tracked reports;
- downloaded two CC BY 4.0 Zenodo corpora: 54 NMC811 21700 cells and 72 LG MJ1 cathode spectra across SOC;
- fixed named-CSV aliases and a dangerous pandas-style unnamed-index case that could silently shift frequency/Re/Im columns;
- parsed `126/126` real spectra;
- Lin-KK results: `84 PASS`, `36 WARN`, `6 FAIL`, median reconstruction RMSE about `1.502%`;
- completed 504 simple-family fits and 204 full-auto subset fits with zero optimizer failures or budget exhaustion;
- identified a model-ranking risk: BIC can recommend `WARN` candidates even when an `OK` candidate exists, because current selection only separates `BAD` from non-`BAD`;
- full report: `validation_data/reports/2026-07-17-open-datasets-baseline.md`.
- added `eis_synthetic.py` with known circuits/parameters, controlled noise/outliers, deterministic seeds, CSV spectra, and `truth.jsonl`;
- rejected a hard `OK > WARN` selector after it reduced topology recovery on synthetic data;
- calibrated conservative `ΔBIC <= 2` selection: 22/30 exact topologies on the first RC/CPE benchmark, including 10/10 ideal RC, 10/10 one-CPE, and 2/10 two-arc spectra;
- the two-arc result identifies multi-start fitting as the next core task; full report: `validation_data/reports/2026-07-17-synthetic-selector-baseline.md`.
- added deterministic bounded multi-start fitting with `--restarts` / `--restart-seed` and per-fit start metrics;
- four-start replay on the ten two-arc spectra improved the true model's RSS in 5/10 files (dramatically in four) but exact selected topology remained 2/10;
- multi-start median runtime was 3.54 s versus 1.01 s for one start; it remains opt-in while staged screening is designed;
- report: `validation_data/reports/2026-07-17-multistart-benchmark.md`.
- added the first series-level analyzer and applied it to LG charge/discharge plus 54 cells at fixed SOC;
- dominant topology stability was about 77.8% for both LG directions and 75.9% across the 21700 cells;
- report: `validation_data/reports/2026-07-17-series-diagnostics-baseline.md`.
- pooled series-model report: `validation_data/reports/2026-07-17-pooled-series-model.md`.
- joint raw-series smoke report: `validation_data/reports/2026-07-17-joint-raw-series-smoke.md`.
- held-out SOC cross-validation report: `validation_data/reports/2026-07-17-joint-soc-cross-validation.md`.
- full 36-spectrum charge-series CV found only a 0.11% gain from smoothing (below the 1% acceptance gate), so joint regularization remains opt-in and disabled by evidence.
- first bootstrap/profile report: `validation_data/reports/2026-07-17-bootstrap-profile-baseline.md`.
- first topology-selection bootstrap found no stable winner (66.7% maximum versus the 90% gate): `validation_data/reports/2026-07-17-topology-bootstrap-baseline.md`.
- first DRT baseline resolved two time regions while leaving topology undecided: `validation_data/reports/2026-07-17-drt-lg-soc50-baseline.md`.
- DRT stability map retained the high-frequency peak in at least 93.3% of perturbations but rejected the low-frequency peak as regularization-sensitive: `validation_data/reports/2026-07-17-drt-peak-stability.md`.
- first localized information-gap report found the 0.01 Hz floor sufficient and recommended repeating/checking stationarity specifically in 0.01-0.1 Hz: `validation_data/reports/2026-07-17-low-frequency-resolution-map.md`.
- unified inference report: `validation_data/reports/2026-07-17-unified-inference-lg-soc50.md`.
- batch inference pipeline report: `validation_data/reports/2026-07-17-batch-inference-pipeline.md`.
- external generalization round 2 added 52 usable spectra across Inspectrum/Zahner pouch datasets, a missing-frequency refusal corpus, and a DRT veto for unsupported bootstrap-stable topology: `validation_data/reports/2026-07-17-external-generalization-round-2.md`.
- two-tier adaptive routing converted the Li-polymer SOC result from `39/42 BAD` first to `42/42 WARN` by admitting inductance, then to `42/42 OK` by admitting `L + diffusion` only for coherent low-frequency residuals; mean fit error fell from 10.52% after tier 1 to 1.91% after tier 2: `validation_data/reports/2026-07-17-lipo-bad-diagnosis.md`.
- family-level inference now preserves `best`, exposes the BIC support window,
  and separates exact-topology from family bootstrap stability;
- a 20-sample competing-family bootstrap over all 42 Li-polymer spectra gave
  `840/840` wins to `inductive_diffusion` with zero refusals, while the exact
  `W/Wo/Ws` topology passed the 90% gate in only `23/42` spectra;
- unified and batch inference now default to the same two-tier `adaptive_v2`
  routing as the main CLI; report:
  `validation_data/reports/2026-07-17-diffusion-family-inference.md`.
- added `eis_family_benchmark.py` for truth-aware calibration of BIC top-K,
  topology bootstrap and family bootstrap;
- on a bounded 16-spectrum synthetic calibration, the 90% bootstrap gate
  still produced 3 false topology and 2 false family recommendations; 95%
  did not remove them, while 6 negative controls produced zero false-positive
  diffusion claims;
- therefore bootstrap stability remains conditional evidence rather than a
  calibrated correctness probability; report:
  `validation_data/reports/2026-07-17-synthetic-family-calibration.md`.
- added `eis_diffusion_map.py` and a 42-spectrum controlled observability grid;
  family recovery was `28/42`, exact topology `7/42`, and truth entered the
  BIC window in `10/42`;
- a benchmark-only positive gate combining family bootstrap >=90% with
  diffusion-vs-base ΔBIC >=10 made 4/4 correct family recommendations and
  7 refusals across strong cells plus negative controls; exact `W/Wo/Ws`
  remains unrecommended pending broader calibration;
- report: `validation_data/reports/2026-07-17-diffusion-observability-map.md`.

First soft refactor completed:

- added `eis_core.py`;
- added `eis_cli.py`;
- added `eis_qt.py` and migrated active GUI direction to PySide6;
- added `requirements.txt`;
- switched PyInstaller spec to `eis_qt.py`;
- removed `eis_desktop.py`;
- converted `eis_app.py` into a legacy wrapper for `eis_qt.py`.

Validation after venv discovery:

- `.venv\Scripts\python.exe -m py_compile eis_core.py eis_cli.py eis_qt.py eis_utils.py eis_app.py` passed;
- `.venv\Scripts\python.exe eis_cli.py "double very good eis.txt" --no-plot` passed;
- PySide6 offscreen smoke passed for empty window creation;
- PySide6 offscreen smoke passed for loading test data, fitting, populating result/parameter tables, and plotting;
- multi-file smoke passed with two loaded test files, two dataset rows, 17 circuit rows, and 7 best-parameter rows;
- best-circuit row highlight changed from yellow to pale green with dark bold text for readability.
- added `eis_io.py` parser layer;
- installed and added `galvani` for BioLogic `.mpr/.mpt` support;
- BioLogic `.mpt` smoke passed on public `galvani` `EIS_latin1.mpt` testdata;
- real laboratory BioLogic EIS `.mpr` files were loaded and fitted successfully;
- non-EIS BioLogic `.mpr` smoke correctly reports missing frequency/Re/Im EIS columns.
- added Bode tab: `|Z|` and `Phase(Z)` vs frequency, with fit overlay when available;
- report export now saves both `_nyquist.png` and `_bode.png`.
- added scoring/ranking pipeline: weighted RSS, AIC, BIC, parameter-count penalty, fit status, and physical warning flags;
- recommended model selection now uses BIC among non-BAD fits instead of raw mean fit error;
- added Residuals tab and `_residuals.png` export.
- added Parser tab and impedance-channel detection/selection foundation;
- CLI accepts `--channel` for BioLogic/multi-channel files.
- moved GUI multi-file fitting to a `QThread` worker;
- added progress bar and cooperative Cancel action/button;
- Qt worker smoke passed for two loaded files: progress `2/2`, two best fits, Run re-enabled, Cancel disabled, Save enabled.
- split circuit families into ideal RC, interface/charge-transfer, diffusion, inductive, advanced, and full auto-fit lists;
- added GUI preset controls: `Interface` menu, `Transport` menu, `Run selected`, and retained `Run auto-fit`;
- preset smoke passed with `Interface screening + Off`: 4 circuits fitted, best circuit `R0-p(R1,CPE0)-p(R2,CPE1)`.
- moved preset controls behind `Pro mode` so normal workflow defaults to auto-fit;
- added manual one-circuit fitting with a `?` syntax help dialog;
- manual smoke passed with `R0-p(R1,CPE0)-p(R2,CPE1)`: 1 circuit fitted and selected.
- replaced the old selected-only save entry with `Export...`;
- added export type picker for batch summary, all model results, best parameters, parser metadata, and selected report/plots;
- export smoke passed on two fitted files: 2 summary rows, 34 model-result rows, 14 best-parameter rows, parser metadata, and selected PNG/TXT outputs.
- added manual `Initial`/`Lower`/`Upper` bounds table behind `Pro mode`;
- manual-bounds smoke passed with `R0-p(R1,CPE0)-p(R2,CPE1)`: 7 editable parameters, 1 manual circuit fitted, mean fit error about `1.000%`;
- added recursive `Open folder` batch loader;
- folder/common-loader smoke passed with generic txt plus BioLogic `.mpt`.
- added drag-and-drop path collection for supported files/folders;
- installed and added `openpyxl`;
- added `_workbook.xlsx` export with Summary, All Results, Best Parameters, and Parser Metadata sheets;
- XLSX smoke passed with two fitted files and four workbook sheets;
- added local Pro preset save/load/delete for manual circuit and bounds;
- Pro preset smoke passed with fallback `.eis_solver_user/pro_presets.json` in sandbox.
- added `View -> Language` with English/Russian switching for the main GUI;
- localization smoke passed: menu/button/table/tab/export-dialog text switches RU -> EN.
- added `Help -> About / Guide` with English/Russian workflow guide;
- About/Guide smoke passed: Help menu and dialog titles switch RU -> EN, English guide body verified.
- added Kramers-Kronig/Lin-KK data-validity check in `eis_core.py`, CLI, GUI dataset table, KK Check tab, report plot, CSV export, and XLSX workbook;
- KK smoke on `double very good eis.txt`: `PASS`, RMSE about `0.689%`, max error about `3.003%`, `mu` about `0.804`, `M=14`.
- installed `pyinstaller` and built a folder executable with `eis_app.spec`;
- exe artifact: `dist\eis_qt\eis_qt.exe`, about 19 MB launcher and about 278 MB total folder;
- exe launch smoke passed: process started from `dist\eis_qt\eis_qt.exe` and stayed alive for 8 seconds.
- best test-data circuit: `R0-p(R1,CPE0)-p(R2,CPE1)`;
- mean fit error: about `1.000%`;
- max parameter error: about `12.18%`.

## Diffusion-family calibration

The frozen benchmark-only diffusion gate was replicated on 70 positive
synthetic spectra and 20 independent negative controls. It made 45 positive
family recommendations, all correct, and refused the remaining 45 cases. It
never recommends an exact `W/Wo/Ws` boundary condition.

The unchanged gate was then tested on 60 diverse independent negative controls.
It produced `0/60` false-positive recommendations, giving a one-sided 95%
upper bound of `4.87%`. The positive-only family gate is therefore enabled in
reliable inference; exact `W/Wo/Ws` topology and negative evidence remain
uncalibrated. See [the production calibration report](validation_data/reports/2026-07-17-diffusion-gate-production-calibration.md).
