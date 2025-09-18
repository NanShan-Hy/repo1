"""Excel export helpers for comparison and deduplication results."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from datacompare.compare.diff import DiffResult
from datacompare.dedup.dedup import DeduplicationResult


def _select_engine() -> str:
    for engine in ("openpyxl", "xlsxwriter"):
        try:
            __import__(engine)
        except ImportError:
            continue
        return engine
    raise RuntimeError(
        "No Excel writer engine found. Install 'openpyxl' or 'xlsxwriter' to enable Excel export."
    )


def export_to_excel(
    path: str | Path,
    diff_result: DiffResult,
    *,
    dedup_result: Optional[DeduplicationResult] = None,
    include_summary: bool = True,
) -> Path:
    """Export comparison and deduplication outputs to an Excel workbook."""

    engine = _select_engine()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(path, engine=engine) as writer:
        if include_summary:
            summary = pd.DataFrame(
                [
                    {"category": key, "count": value}
                    for key, value in diff_result.summary().items()
                ]
            )
            if dedup_result:
                summary = pd.concat(
                    [
                        summary,
                        pd.DataFrame(
                            [
                                {"category": key, "count": value}
                                for key, value in dedup_result.summary().items()
                            ]
                        ),
                    ],
                    ignore_index=True,
                )
            summary.to_excel(writer, sheet_name="摘要", index=False)

        diff_result.matched.to_excel(writer, sheet_name="匹配一致", index=False)
        diff_result.mismatched.to_excel(writer, sheet_name="匹配差异", index=False)
        diff_result.details.to_excel(writer, sheet_name="差异明细", index=False)
        diff_result.left_only.to_excel(writer, sheet_name="仅左存在", index=False)
        diff_result.right_only.to_excel(writer, sheet_name="仅右存在", index=False)

        if dedup_result:
            dedup_result.exact.unique.to_excel(writer, sheet_name="去重后数据", index=False)
            dedup_result.exact.groups.to_excel(writer, sheet_name="重复明细", index=False)
            dedup_result.approximate.pairs.to_excel(writer, sheet_name="近似重复候选", index=False)

        if hasattr(writer, "book"):
            # Freeze header rows for readability when engines support it.
            for sheet in writer.sheets.values():
                try:
                    sheet.freeze_panes = (1, 0)
                except AttributeError:
                    try:
                        sheet.freeze_panes(1, 0)
                    except Exception:
                        pass

    return path


__all__ = ["export_to_excel"]
