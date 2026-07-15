# Architecture

The architecture is deliberately simple: GUI, parser, fitting core, export.

## Module Map

```mermaid
flowchart TD
    CLI[eis_cli.py] --> IO[eis_io.py]
    GUI[eis_qt.py] --> IO
    GUI --> Core[eis_core.py]
    CLI --> Core
    IO --> Dataset[EisDataset]
    Core --> FitResult[FitResult]
    GUI --> Export[CSV / XLSX / TXT / PNG]
    GUI --> PresetStore[Local pro_presets.json]
```

## File Responsibilities

| File | Role |
|---|---|
| `eis_core.py` | Circuit families, guesses, bounds, fitting, AIC/BIC, flags |
| `eis_io.py` | Text/BioLogic parsing, channel detection, dataset cleaning |
| `eis_qt.py` | Production desktop GUI, threading, plots, export, localization |
| `eis_cli.py` | CLI smoke/debug entrypoint |
| `eis_utils.py` | Legacy compatibility wrapper |
| `eis_app.py` | Legacy launcher wrapper to `eis_qt.py` |
| `cycling.py` | Legacy scrap, not part of current EIS architecture |

## Core Data Types

```mermaid
classDiagram
    class EisDataset {
        file_path
        frequencies
        z
        source_format
        columns
        metadata
    }

    class DatasetScale {
        r0
        r_transfer
        capacitance
    }

    class FitResult {
        circuit_string
        success
        model
        mean_fit_error
        max_param_error
        rss_weighted
        aic
        bic
        n_params
        status
        flags
        error_message
    }

    class AnalysisCase {
        file_path
        frequencies
        z_experimental
        scale
        source_format
        metadata
        selected_channel
        results
        best_result
    }

    EisDataset --> AnalysisCase
    DatasetScale --> AnalysisCase
    FitResult --> AnalysisCase
```

## GUI Threading

Fitting is performed in a Qt worker thread so the GUI remains responsive during batch analysis.

```mermaid
sequenceDiagram
    participant User
    participant GUI as EisQtApp
    participant Worker as FitWorker/QThread
    participant Core as eis_core

    User->>GUI: Run auto-fit / selected / manual
    GUI->>Worker: start(cases, circuits, overrides)
    loop per file
        Worker->>Core: fit_circuits(...)
        Core-->>Worker: list[FitResult]
        Worker->>Core: choose_best_result(...)
        Worker-->>GUI: finished_case(index, results, best)
        Worker-->>GUI: progress(completed, total)
    end
    Worker-->>GUI: finished(cancelled)
```

## Local User Data

Pro presets are not stored in the repository.

Primary path on Windows:

```text
%APPDATA%\EIS Solver\pro_presets.json
```

Fallback path:

```text
.eis_solver_user/pro_presets.json
```

The fallback folder is ignored by git.

