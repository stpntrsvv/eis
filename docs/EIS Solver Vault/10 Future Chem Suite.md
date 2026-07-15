# Future Chem Suite

EIS Solver is the first brick of a broader Chem Suite.

The key design principle: keep each scientific workflow as a strong standalone module, but share infrastructure where it makes sense.

## Possible Suite Modules

```mermaid
mindmap
  root((Chem Suite))
    EIS Solver
      Equivalent circuits
      Nyquist/Bode
      Batch export
    Cycling
      Capacity
      Coulombic efficiency
      Retention
    CV
      Peak analysis
      Integration
      Scan-rate studies
    OCV
      Relaxation
      Drift
    GITT/PITT
      Diffusion coefficients
      Step analysis
    Reports
      Batch summaries
      Figures
      XLSX/PDF
```

## What To Reuse

From EIS Solver:

- PySide6 app shell.
- Drag/drop and folder loading patterns.
- Export dialog pattern.
- English/Russian localization approach.
- Local user preset storage.
- Worker-thread pattern.
- README plus Obsidian vault documentation style.

## What To Avoid

- Do not revive `cycling.py` directly as production code.
- Do not put domain logic directly in GUI.
- Do not make export columns depend on UI language.
- Do not make shared modules before two modules truly need the same abstraction.

## Suggested Long-Term Architecture

```mermaid
flowchart TD
    Suite[Chem Suite Shell] --> EIS[EIS Module]
    Suite --> Cycling[Cycling Module]
    Suite --> CV[CV Module]
    Suite --> Reports[Report Module]
    EIS --> SharedIO[Shared IO Utilities]
    Cycling --> SharedIO
    CV --> SharedIO
    EIS --> SharedExport[Shared Export]
    Cycling --> SharedExport
    Reports --> SharedExport
```

## EIS Module Boundary

EIS Solver should remain independently runnable even if Chem Suite becomes a larger app.

That means:

- `eis_core.py` stays GUI-independent;
- `eis_io.py` stays testable;
- `eis_qt.py` can either stay standalone or become embedded later;
- exports remain usable outside the suite.

