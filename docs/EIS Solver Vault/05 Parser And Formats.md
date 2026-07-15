# Parser And Formats

Parsing lives in `eis_io.py`.

The parser returns an `EisDataset`:

```text
file_path
frequencies
z
source_format
columns
metadata
```

## Supported Inputs

| Format | Status |
|---|---|
| generic text/txt/csv/dat | working |
| SmartStat-like first three numeric columns | working |
| BioLogic `.mpt` | working through `galvani` |
| BioLogic `.mpr` | loader present through `galvani`, needs real EIS validation |

## Parser Flow

```mermaid
flowchart TD
    A[load_eis_file(path)] --> B{Extension}
    B -->|.mpr| C[galvani BioLogic.MPRfile]
    B -->|.mpt| D[galvani BioLogic.MPTfile]
    B -->|txt/csv/dat/other| E[Text parser]
    C --> F[structured array]
    D --> F
    E --> G{Named columns?}
    G -->|Yes| F
    G -->|No| H[first three numeric columns]
    F --> I[Detect frequency / Re / Im columns]
    I --> J[Detect impedance channels]
    J --> K[Clean finite, positive frequency, sort]
    K --> L[EisDataset]
```

## Channel Detection

The parser looks for impedance channels such as:

- `Z`
- `Zce`
- `Zstack`
- `Zwe-ce`
- `Z1`
- `Z2`

If multiple channels are available, the GUI exposes a channel dropdown.

## Imaginary Sign Convention

For generic text fallback:

- the first three numeric columns are treated as `frequency`, `Re(Z)`, `Im(Z)`;
- if `Im(Z)` is mostly positive, sign is flipped so the usual Nyquist view plots `-Im(Z)` upward.

For named columns:

- the parser tries to identify whether the column is raw imaginary impedance or already negative imaginary impedance.

## What Needs Lab Data

The missing validation item is a real EIS `.mpr` from BioLogic.

Questions to answer with that file:

- Are frequency columns named as expected?
- Are Re/Im columns named as expected?
- Are channels exposed as `Z`, `Z1`, `Z2`, `Zce`, etc.?
- Are units and signs consistent?
- Does galvani expose all required arrays cleanly?

