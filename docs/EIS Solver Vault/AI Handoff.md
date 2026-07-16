# AI Handoff

Use this page to quickly orient a future AI chat.

## First Things To Know

- The current production GUI is `eis_qt.py`.
- The fitting core is `eis_core.py`.
- Kramers-Kronig/Lin-KK validation is in `eis_core.py` as `lin_kk_check()`, wrapping `impedance.validation.linKK`.
- The parser layer is `eis_io.py`.
- `cycling.py` is legacy scrap and should not be used as a foundation.
- `README.md` is the compact journal.
- This Obsidian vault is the human-readable knowledge base.

## Current App Status

The app is a release-candidate EIS tool for text and BioLogic `.mpt` workflows.

It includes:

- PySide6 GUI;
- auto-fit;
- Pro mode;
- manual circuit and bounds;
- local Pro presets;
- drag/drop and folder batch loading;
- Nyquist/Bode/residual plots;
- KK Check tab and CLI/export KK diagnostics;
- CSV/XLSX/TXT/PNG export;
- English/Russian UI switch;
- built-in About/Guide.

## Main Open Risk

One real single-sweep BioLogic EIS `.mpr` with channel `Z` has been validated. Broader validation remains pending for multi-cycle files and channels `Zce/Zstack/Zwe-ce/Z1/Z2`.

Each circuit fit is capped at 5,000 function evaluations. GUI progress and cooperative cancel operate between individual circuits.

## Run Commands

```powershell
.\.venv\Scripts\python.exe eis_cli.py "double very good eis.txt" --no-plot
.\.venv\Scripts\python.exe eis_qt.py
.\.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm eis_app.spec
```

Built folder executable:

```text
dist\eis_qt\eis_qt.exe
```

## Smoke Test Anchors

Known best circuit on `double very good eis.txt`:

```text
R0-p(R1,CPE0)-p(R2,CPE1)
```

Known mean fit error:

```text
about 1.000%
```

Known default circuit count:

```text
17 circuits, no duplicates
```

Known KK smoke on `double very good eis.txt`:

```text
PASS; RMSE about 0.689%; max error about 3.003%; mu about 0.804; M=14
```

Known packaged exe smoke:

```text
dist\eis_qt\eis_qt.exe starts and stays alive for at least 8 seconds.
```

## Development Rules

1. Add fitting logic to `eis_core.py`, not GUI.
2. Add parser logic to `eis_io.py`.
3. Keep data-validity diagnostics such as KK in `eis_core.py`, then expose them in CLI/GUI/export.
4. Keep exports stable and language-independent.
5. Preserve the normal workflow: open -> auto-fit -> inspect -> export.
6. Hide advanced controls behind Pro mode.
7. Keep user presets local unless explicit import/export is added.
