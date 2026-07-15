from dataclasses import dataclass, field
import os
import re
import warnings

import numpy as np


@dataclass
class EisDataset:
    file_path: str
    frequencies: np.ndarray
    z: np.ndarray
    source_format: str
    columns: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ImpedanceChannel:
    name: str
    frequency_column: str
    real_column: str
    imaginary_column: str
    imaginary_mode: str


def load_eis_file(file_path: str, channel: str | None = None) -> EisDataset:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".mpr":
        return load_biologic_mpr(file_path, channel=channel)
    if ext == ".mpt":
        return load_biologic_mpt(file_path, channel=channel)
    return load_text_eis_file(file_path, channel=channel)


def load_biologic_mpr(file_path: str, channel: str | None = None) -> EisDataset:
    try:
        from galvani import BioLogic
    except ImportError as exc:
        raise ImportError("BioLogic .mpr support requires the 'galvani' package.") from exc

    mpr_file = BioLogic.MPRfile(file_path)
    return dataset_from_structured_array(
        file_path=file_path,
        data=mpr_file.data,
        source_format="biologic_mpr",
        channel=channel,
        metadata={
            "galvani_data_version": getattr(mpr_file, "version", None),
            "startdate": str(getattr(mpr_file, "startdate", "")),
            "columns": [str(name) for name in mpr_file.data.dtype.names or []],
        },
    )


def load_biologic_mpt(file_path: str, channel: str | None = None) -> EisDataset:
    try:
        from galvani import BioLogic
    except ImportError as exc:
        raise ImportError("BioLogic .mpt support requires the 'galvani' package.") from exc

    last_error = None
    for encoding in ("ascii", "utf-8", "latin1", "cp1252"):
        try:
            data, comments = BioLogic.MPTfile(file_path, encoding=encoding)
            break
        except (UnicodeDecodeError, ValueError) as exc:
            last_error = exc
    else:
        raise ValueError(f"Could not read BioLogic .mpt file with supported encodings: {last_error}")

    return dataset_from_structured_array(
        file_path=file_path,
        data=data,
        source_format="biologic_mpt",
        channel=channel,
        metadata={
            "encoding": encoding,
            "comments": [
                comment.decode("utf-8", errors="replace") if isinstance(comment, bytes) else str(comment)
                for comment in comments
            ],
            "columns": [str(name) for name in data.dtype.names or []],
        },
    )


def dataset_from_structured_array(file_path: str, data, source_format: str, metadata=None, channel: str | None = None) -> EisDataset:
    names = list(data.dtype.names or [])
    if not names:
        raise ValueError(f"{source_format} reader returned no named columns.")

    channels = detect_impedance_channels(names)
    selected_channel = choose_impedance_channel(channels, channel)

    freq_col = selected_channel.frequency_column
    re_col = selected_channel.real_column
    im_col = selected_channel.imaginary_column
    im_mode = selected_channel.imaginary_mode

    frequencies = np.asarray(data[freq_col], dtype=float)
    re_values = np.asarray(data[re_col], dtype=float)
    im_values = np.asarray(data[im_col], dtype=float)
    z_imag = imaginary_to_z_imag(im_values, im_mode)

    return clean_dataset(
        EisDataset(
            file_path=file_path,
            frequencies=frequencies,
            z=re_values + 1j * z_imag,
            source_format=source_format,
            columns=names,
            metadata={
                **(metadata or {}),
                "frequency_column": freq_col,
                "real_column": re_col,
                "imaginary_column": im_col,
                "imaginary_mode": im_mode,
                "selected_channel": selected_channel.name,
                "available_channels": [detected.name for detected in channels],
            },
        )
    )


def load_text_eis_file(file_path: str, channel: str | None = None) -> EisDataset:
    table = try_load_named_text_table(file_path)
    if table is not None:
        return table

    data_lines = []
    with open(file_path, "r", encoding="utf-8", errors="replace") as file:
        for line in file:
            matches = re.findall(r"[-+]?\d*\.\d+(?:[eE][-+]?\d+)?|\b[-+]?\d+\b", line)
            if len(matches) >= 3:
                data_lines.append([float(value) for value in matches[:3]])

    if not data_lines:
        raise ValueError(f"Could not find three numeric columns in {file_path}")

    data = np.array(data_lines, dtype=float)
    z_imag = imaginary_to_z_imag(data[:, 2], "auto")
    return clean_dataset(
        EisDataset(
            file_path=file_path,
            frequencies=data[:, 0],
            z=data[:, 1] + 1j * z_imag,
            source_format="generic_numeric_text",
            columns=["frequency", "re", "im"],
            metadata={
                "imaginary_mode": "auto",
                "selected_channel": "Z",
                "available_channels": ["Z"],
            },
        )
    )


def try_load_named_text_table(file_path: str):
    for delimiter in ("\t", ",", ";", None):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                data = np.genfromtxt(
                    file_path,
                    names=True,
                    delimiter=delimiter,
                    dtype=float,
                    encoding="utf-8",
                    invalid_raise=False,
                    autostrip=True,
                )
        except Exception:
            continue

        names = list(data.dtype.names or [])
        if len(names) < 3:
            continue

        try:
            return dataset_from_structured_array(
                file_path=file_path,
                data=data,
                source_format="named_text_table",
                metadata={"delimiter": delimiter, "columns": names},
            )
        except Exception:
            continue
    return None


def detect_impedance_channels(names: list[str]) -> list[ImpedanceChannel]:
    channels = []
    try:
        freq_col = choose_column(names, FREQUENCY_ALIASES, kind="frequency")
    except ValueError:
        return []

    preferred_specs = [
        ("Z", REAL_ALIASES, NEG_IMAG_ALIASES, RAW_IMAG_ALIASES),
        ("Zce", aliases_for_real("zce"), aliases_for_negative_imag("zce"), aliases_for_raw_imag("zce")),
        ("Zstack", aliases_for_real("zstack"), aliases_for_negative_imag("zstack"), aliases_for_raw_imag("zstack")),
        ("Zwe-ce", aliases_for_real("zwe-ce"), aliases_for_negative_imag("zwe-ce"), aliases_for_raw_imag("zwe-ce")),
        ("Z1", aliases_for_real("z1"), aliases_for_negative_imag("z1"), aliases_for_raw_imag("z1")),
        ("Z2", aliases_for_real("z2"), aliases_for_negative_imag("z2"), aliases_for_raw_imag("z2")),
    ]

    for name, real_aliases, negative_imag_aliases, raw_imag_aliases in preferred_specs:
        try:
            real_col = choose_column(names, real_aliases, kind=f"{name} real impedance")
            imag_col, imag_mode = choose_imaginary_column_from_aliases(names, negative_imag_aliases, raw_imag_aliases)
        except ValueError:
            continue
        channels.append(ImpedanceChannel(name, freq_col, real_col, imag_col, imag_mode))

    return channels


def choose_impedance_channel(channels: list[ImpedanceChannel], requested: str | None) -> ImpedanceChannel:
    if not channels:
        raise ValueError("Could not detect any EIS impedance channel with frequency, Re(Z), and Im(Z) columns.")

    if requested:
        normalized_requested = normalize_column_name(requested)
        for channel in channels:
            if normalize_column_name(channel.name) == normalized_requested:
                return channel
        raise ValueError(
            f"Requested impedance channel '{requested}' is not available. "
            f"Available channels: {', '.join(channel.name for channel in channels)}"
        )

    for preferred in ("Z", "Z1", "Zwe-ce", "Zce", "Zstack", "Z2"):
        for channel in channels:
            if channel.name == preferred:
                return channel
    return channels[0]


def aliases_for_real(channel_key: str) -> tuple[str, ...]:
    return (f"re({channel_key})/ohm", f"re{channel_key}/ohm", f"re{channel_key}ohm", f"re{channel_key}")


def aliases_for_negative_imag(channel_key: str) -> tuple[str, ...]:
    return (
        f"-im({channel_key})/ohm",
        f"-im{channel_key}/ohm",
        f"-im{channel_key}ohm",
        f"minusim{channel_key}ohm",
    )


def aliases_for_raw_imag(channel_key: str) -> tuple[str, ...]:
    return (f"im({channel_key})/ohm", f"im{channel_key}/ohm", f"im{channel_key}ohm", f"im{channel_key}")


FREQUENCY_ALIASES = (
    "freq/hz",
    "frqhz",
    "frq/hz",
    "frequencyhz",
    "frequency/hz",
    "f/hz",
    "freq",
    "frequency",
)

REAL_ALIASES = (
    "re(z)/ohm",
    "rez/ohm",
    "rezohm",
    "reohm",
    "zre",
    "realz",
    "real",
    "re",
)

NEG_IMAG_ALIASES = (
    "-im(z)/ohm",
    "-imz/ohm",
    "-imzohm",
    "minusimzohm",
    "negimzohm",
    "-im",
)

RAW_IMAG_ALIASES = (
    "im(z)/ohm",
    "imz/ohm",
    "imzohm",
    "imohm",
    "zim",
    "imagz",
    "imaginary",
    "im",
)


def choose_column(names, aliases, kind: str) -> str:
    normalized = {normalize_column_name(name): name for name in names}
    for alias in aliases:
        normalized_alias = normalize_column_name(alias)
        if normalized_alias in normalized:
            return normalized[normalized_alias]

    alias_parts = [normalize_column_name(alias) for alias in aliases]
    for normalized_name, original_name in normalized.items():
        if any(len(alias) >= 4 and alias in normalized_name for alias in alias_parts):
            return original_name

    raise ValueError(f"Could not identify {kind} column. Available columns: {', '.join(names)}")


def choose_imaginary_column(names) -> tuple[str, str]:
    return choose_imaginary_column_from_aliases(names, NEG_IMAG_ALIASES, RAW_IMAG_ALIASES)


def choose_imaginary_column_from_aliases(names, negative_aliases, raw_aliases) -> tuple[str, str]:
    normalized = {normalize_column_name(name): name for name in names}
    for alias in negative_aliases:
        if alias in normalized:
            return normalized[alias], "negative_imaginary"
    for alias in raw_aliases:
        if alias in normalized:
            return normalized[alias], "raw_imaginary"

    negative_parts = [normalize_column_name(alias) for alias in negative_aliases]
    raw_parts = [normalize_column_name(alias) for alias in raw_aliases]
    for normalized_name, original_name in normalized.items():
        if any(alias in normalized_name for alias in negative_parts):
            return original_name, "negative_imaginary"
        if any(alias in normalized_name for alias in raw_parts):
            return original_name, "raw_imaginary"

    for normalized_name, original_name in normalized.items():
        if "im" in normalized_name:
            return original_name, "auto"

    raise ValueError(f"Could not identify imaginary impedance column. Available columns: {', '.join(names)}")


def normalize_column_name(name: str) -> str:
    normalized = str(name).strip().lower()
    normalized = normalized.replace("ω", "ohm")
    normalized = normalized.replace("Ω", "ohm")
    normalized = normalized.replace("Ω", "ohm")
    normalized = normalized.replace(" ", "")
    normalized = normalized.replace("_", "")
    normalized = normalized.replace("(", "")
    normalized = normalized.replace(")", "")
    normalized = normalized.replace("[", "")
    normalized = normalized.replace("]", "")
    return normalized


def imaginary_to_z_imag(values, mode: str):
    values = np.asarray(values, dtype=float)
    if mode == "negative_imaginary":
        return -values
    if mode == "raw_imaginary":
        return values

    mean_im = float(np.nanmean(values))
    return values if mean_im < 0 else -values


def clean_dataset(dataset: EisDataset) -> EisDataset:
    mask = np.isfinite(dataset.frequencies) & np.isfinite(dataset.z.real) & np.isfinite(dataset.z.imag)
    frequencies = np.asarray(dataset.frequencies[mask], dtype=float)
    z_values = np.asarray(dataset.z[mask], dtype=complex)

    if len(frequencies) == 0:
        raise ValueError(f"No finite EIS rows found in {dataset.file_path}")

    order = np.argsort(frequencies)[::-1]
    dataset.frequencies = frequencies[order]
    dataset.z = z_values[order]
    return dataset
