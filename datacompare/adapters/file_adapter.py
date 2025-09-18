"""Data adapters for loading tabular sources such as CSV/Excel/HTML.

This module focuses on the "即开即用" experience described in the product
blueprint.  It provides a single ``load_dataset`` entry point that hides file
format detection, applies basic sampling for preview, and returns rich
metadata that can be used by the downstream normalization and recommendation
layers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping, MutableMapping, Optional

import numpy as np
import pandas as pd


@dataclass
class SampledPreview:
    """Container for lightweight dataset previews.

    Attributes
    ----------
    head:
        First ``n`` rows of the dataset.
    tail:
        Last ``n`` rows of the dataset.
    random:
        Randomly sampled rows used to give the user a quick feel of the
        overall distribution while keeping the UI responsive for very large
        tables.
    """

    head: pd.DataFrame
    tail: pd.DataFrame
    random: pd.DataFrame


@dataclass
class AdapterResult:
    """Represents the outcome of loading a dataset from an arbitrary source."""

    data: pd.DataFrame
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    preview: Optional[SampledPreview] = None


_SUPPORTED_EXCEL_EXTENSIONS = {".xlsx", ".xls", ".xlsm"}
_SUPPORTED_CSV_EXTENSIONS = {".csv", ".txt"}
_SUPPORTED_HTML_EXTENSIONS = {".html", ".htm"}


class UnsupportedSourceError(ValueError):
    """Raised when ``load_dataset`` receives an unsupported source."""


def _normalise_source(source: Any) -> str:
    if hasattr(source, "name") and isinstance(source.name, str):
        return source.name
    if isinstance(source, (str, Path)):
        return str(source)
    raise UnsupportedSourceError(
        "Unsupported source type. Provide a path-like object or a buffer with a"
        " 'name' attribute."
    )


def _prepare_preview(df: pd.DataFrame, sample_size: int) -> Optional[SampledPreview]:
    if df.empty:
        return None

    sample_size = min(sample_size, len(df))
    head = df.head(sample_size)
    tail = df.tail(sample_size)

    if len(df) <= sample_size:
        random = head
    else:
        rng = np.random.default_rng(seed=42)
        indices = rng.choice(len(df), size=sample_size, replace=False)
        random = df.iloc[np.sort(indices)]

    return SampledPreview(head=head, tail=tail, random=random)


def load_dataset(
    source: Any,
    *,
    sheet: Optional[str] = None,
    html_table_index: int = 0,
    encoding: Optional[str] = None,
    preview_rows: int = 20,
    load_sampling: bool = True,
    read_csv_kwargs: Optional[Mapping[str, Any]] = None,
) -> AdapterResult:
    """Load data from ``source`` and return a structured :class:`AdapterResult`.

    Parameters
    ----------
    source:
        Path or buffer representing the dataset.
    sheet:
        Sheet name when loading Excel workbooks.  When ``None`` the first sheet
        is used.
    html_table_index:
        When reading HTML pages containing multiple ``<table>`` elements this
        index determines the table to extract.
    encoding:
        Optional file encoding hint for CSV/HTML sources.
    preview_rows:
        Number of rows to include in the sampled preview.
    load_sampling:
        Whether to prepare ``head/tail/random`` previews.  Disabling this is
        useful for automated batch processing.
    read_csv_kwargs:
        Extra options forwarded to :func:`pandas.read_csv`.
    """

    source_name = _normalise_source(source)
    path = Path(source_name)
    ext = path.suffix.lower()
    metadata: MutableMapping[str, Any] = {
        "source_name": source_name,
        "sheet": sheet,
    }

    if ext in _SUPPORTED_CSV_EXTENSIONS:
        df = pd.read_csv(
            source,
            encoding=encoding,
            **({} if read_csv_kwargs is None else dict(read_csv_kwargs)),
        )
        metadata.update({"format": "csv", "encoding": encoding})
    elif ext in _SUPPORTED_EXCEL_EXTENSIONS:
        df = pd.read_excel(source, sheet_name=sheet)
        metadata.update({"format": "excel", "sheet": sheet})
    elif ext in _SUPPORTED_HTML_EXTENSIONS:
        tables = pd.read_html(source, encoding=encoding)
        if not tables:
            raise UnsupportedSourceError("No tables found in the provided HTML source")
        if html_table_index >= len(tables):
            raise UnsupportedSourceError(
                f"Requested table index {html_table_index} but only {len(tables)} tables present"
            )
        df = tables[html_table_index]
        metadata.update(
            {
                "format": "html",
                "table_index": html_table_index,
                "table_count": len(tables),
            }
        )
    else:
        raise UnsupportedSourceError(
            f"Unsupported file extension '{ext}'. Supported formats: CSV, Excel, HTML."
        )

    preview = _prepare_preview(df, preview_rows) if load_sampling else None
    metadata.update({
        "row_count": int(df.shape[0]),
        "column_count": int(df.shape[1]),
        "columns": list(df.columns),
    })

    return AdapterResult(data=df, source=source_name, metadata=dict(metadata), preview=preview)


__all__ = ["AdapterResult", "SampledPreview", "UnsupportedSourceError", "load_dataset"]
