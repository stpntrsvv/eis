# Scientific Model

This page documents the current electrochemical and mathematical assumptions.

## Fitting Engine

The fitting engine is `impedance.models.circuits.CustomCircuit`.

Current fit call:

```python
CustomCircuit.fit(..., weight_by_modulus=True)
```

This weights residuals by impedance modulus, which helps prevent high-impedance low-frequency points from dominating everything.

## Default Circuit Families

| Family | Purpose |
|---|---|
| `IDEAL_RC_CIRCUITS` | sanity-check ideal RC |
| `INTERFACE_CIRCUITS` | charge transfer, CPE, two arcs |
| `DIFFUSION_CIRCUITS` | Warburg and finite diffusion |
| `INDUCTIVE_CIRCUITS` | inductive loops or wiring/fixture effects |
| `DEFAULT_CIRCUITS` | full auto-fit list |

## Electrochemical Interpretation

```mermaid
flowchart LR
    R0[Solution / ohmic resistance R0] --> Interface[Interface response]
    Interface --> Rct[Rct]
    Interface --> CPE[Double-layer CPE]
    Interface --> Film[Film / SEI arc]
    Film --> Diffusion[Diffusion tail]
    Diffusion --> Warburg[W / Wo / Ws]
    Interface --> Inductive[Inductive loop if present]
```

## Why CPE Matters

Ideal capacitors are rarely enough for porous, rough, aged, coated, or chemically heterogeneous electrodes.

The app keeps ideal `C` as a sanity-check model, but most practical circuit families use `CPE`.

## Model Selection

The app does not choose the best model only by raw fit error.

Before model trust, the app also runs the `impedance.validation.linKK` Kramers-Kronig/Lin-KK consistency check on the loaded spectrum. This is a data-quality gate, not a circuit-selection score. Details live in [[23 Kramers-Kronig Validation]].

Current selection:

1. Fit all selected circuits.
2. Classify each result as `OK`, `WARN`, or `BAD`.
3. Prefer non-`BAD` candidates.
4. Choose the minimum BIC.
5. Tie-break by parameter count and mean fit error.

```mermaid
flowchart TD
    A[Fit circuits] --> B[Compute residual diagnostics]
    B --> C[Compute AIC / BIC]
    C --> D[Generate physical flags]
    D --> E{Any non-BAD?}
    E -->|Yes| F[Use non-BAD candidates]
    E -->|No| G[Use successful candidates]
    F --> H[Pick lowest BIC]
    G --> H
```

## Kramers-Kronig Gate

Current implementation:

- wrapper function: `lin_kk_check()` in `eis_core.py`;
- library method: `impedance.validation.linKK`;
- result object: `KramersKronigResult`;
- GUI: dataset `KK` column plus `KK Check` tab;
- CLI: `=== Kramers-Kronig check ===`;
- export: summary `kk_*` columns, `_kk_check.csv`, XLSX `KK Check` sheet, `_kk_check.png`.

The Lin-KK check reconstructs the spectrum with a fixed distribution of RC relaxation times and reports:

- reconstruction RMSE;
- maximum relative error;
- Schönleber `mu` criterion;
- `PASS`, `WARN`, or `FAIL` status.

## Fit Status

| Status | Meaning |
|---|---|
| `OK` | no current warning flags |
| `WARN` | useful candidate, but inspect flags/residuals |
| `BAD` | severe non-identifiability, bound issue, or impossible uncertainty |

## Current Limitations

- Kramers-Kronig validation uses the practical `impedance.py` Lin-KK implementation, not a full formal integral transform.
- No formal physical model priors beyond bounds and flags.
- No automatic rejection of all over-parameterized models beyond BIC/flags.
- BioLogic `.mpr` EIS needs real lab validation.
