"""Command line interface for the data comparison toolkit."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd

from datacompare.adapters.file_adapter import AdapterResult, load_dataset
from datacompare.compare.diff import ColumnMapping, ComparisonConfig, DiffResult, compute_diff
from datacompare.dedup.dedup import DeduplicationResult, deduplicate
from datacompare.export.excel_exporter import export_to_excel
from datacompare.normalize.columns import ColumnNormalizationResult, normalise_column_names
from datacompare.normalize.types import infer_column_types
from datacompare.recommend.key_recommender import recommend_join_keys
from datacompare.recommend.mapping_recommender import recommend_mappings
from datacompare.recommend.rules_recommender import suggest_rules


def _normalise_column_name(name: str, normalisation: ColumnNormalizationResult) -> str:
    return normalisation.mapping.get(name, name)


def _parse_column_list(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _normalise_list(names: List[str], normalisation: ColumnNormalizationResult) -> List[str]:
    return [_normalise_column_name(name, normalisation) for name in names]


def _parse_mappings(value: Optional[str], left_norm: ColumnNormalizationResult, right_norm: ColumnNormalizationResult) -> List[ColumnMapping]:
    if not value:
        return []
    mappings: List[ColumnMapping] = []
    for pair in value.split(","):
        if not pair.strip():
            continue
        if ":" not in pair:
            raise ValueError(f"Invalid mapping '{pair}'. Expected format left:right")
        left_name, right_name = pair.split(":", 1)
        left_key = _normalise_column_name(left_name.strip(), left_norm)
        right_key = _normalise_column_name(right_name.strip(), right_norm)
        mappings.append(ColumnMapping(left=left_key, right=right_key, alias=right_key))
    return mappings


def _auto_select_keys(
    left_norm: ColumnNormalizationResult,
    right_norm: ColumnNormalizationResult,
    limit: int = 3,
) -> List[str]:
    left_df = left_norm.data
    candidates = recommend_join_keys(left_df, top_n=limit)
    for candidate in candidates:
        if all(column in right_norm.data.columns for column in candidate.columns):
            return list(candidate.columns)
    raise SystemExit("Unable to automatically determine join keys. Please provide --keys explicitly.")


def _auto_mappings(
    left_norm: ColumnNormalizationResult,
    right_norm: ColumnNormalizationResult,
    *,
    threshold: float,
) -> List[ColumnMapping]:
    left_types = infer_column_types(left_norm.data).as_mapping()
    right_types = infer_column_types(right_norm.data).as_mapping()
    suggestions = recommend_mappings(
        left_norm.data,
        right_norm.data,
        left_types=left_types,
        right_types=right_types,
        per_column=3,
    )
    used_right: set[str] = set()
    mappings: List[ColumnMapping] = []
    for left_col, candidates in suggestions.items():
        if not candidates:
            continue
        top = candidates[0]
        if top.score < threshold:
            continue
        if top.right in used_right:
            continue
        used_right.add(top.right)
        mappings.append(ColumnMapping(left=left_col, right=top.right, alias=top.right))
    return mappings


def _load_and_normalise(path: str | Path) -> tuple[AdapterResult, ColumnNormalizationResult]:
    adapter_result = load_dataset(path)
    normalised = normalise_column_names(adapter_result.data)
    return adapter_result, normalised


def _print_preview(result: AdapterResult) -> None:
    print(f"Loaded {result.source}: {result.metadata['row_count']} rows × {result.metadata['column_count']} columns")
    if result.preview:
        print("Head preview:")
        print(result.preview.head.to_string(index=False))


def _display_mappings(mappings: List[ColumnMapping]) -> None:
    table = [{"left": mapping.left, "right": mapping.right, "alias": mapping.alias} for mapping in mappings]
    if table:
        print("Using column mappings:")
        print(pd.DataFrame(table).to_string(index=False))
    else:
        print("No column mappings were generated; comparison may not yield results.")


def run_compare(args: argparse.Namespace) -> DiffResult:
    left_result, left_norm = _load_and_normalise(args.left)
    right_result, right_norm = _load_and_normalise(args.right)

    if args.show_preview:
        _print_preview(left_result)
        _print_preview(right_result)

    keys = _parse_column_list(args.keys)
    if not keys:
        keys = _auto_select_keys(left_norm, right_norm)
        print(f"Auto-selected join keys: {', '.join(keys)}")
    else:
        keys = _normalise_list(keys, left_norm)

    mappings = _parse_mappings(args.mappings, left_norm, right_norm)
    if not mappings:
        mappings = _auto_mappings(left_norm, right_norm, threshold=args.auto_map_threshold)
        print(f"Auto-generated {len(mappings)} column mappings using threshold {args.auto_map_threshold}")
    _display_mappings(mappings)

    config = ComparisonConfig(
        treat_zero_as_null=args.zero_equals_null,
        absolute_tolerance=args.tolerance,
        relative_tolerance=args.relative_tolerance,
        case_insensitive=args.case_insensitive,
        strip_whitespace=not args.keep_whitespace,
        datetime_tolerance=args.datetime_tolerance,
    )

    diff_result = compute_diff(
        left_norm.data,
        right_norm.data,
        join_keys=keys,
        mappings=mappings,
        config=config,
    )

    print("Comparison summary:")
    print(pd.DataFrame([diff_result.summary()]).to_string(index=False))

    dedup_result: Optional[DeduplicationResult] = None
    if args.dedup:
        dedup_subset = (
            keys
            if args.dedup_subset is None
            else _normalise_list(_parse_column_list(args.dedup_subset), left_norm)
        )
        dedup_result = deduplicate(
            left_norm.data,
            subset=dedup_subset or None,
            text_columns=_normalise_list(_parse_column_list(args.dedup_text_columns), left_norm),
            numeric_columns=_normalise_list(
                _parse_column_list(args.dedup_numeric_columns), left_norm
            ),
            threshold=args.dedup_threshold,
        )
        print("Deduplication summary:")
        print(pd.DataFrame([dedup_result.summary()]).to_string(index=False))

    if args.suggest_rules:
        rules = suggest_rules(left_norm.data, right_norm.data)
        print("Suggested comparison rules:")
        print(
            json.dumps(
                {
                    "zero_equals_null": rules.zero_equals_null,
                    "numeric_tolerance": rules.numeric_tolerance,
                    "candidate_columns": rules.candidate_columns,
                    "notes": rules.notes,
                },
                ensure_ascii=False,
                indent=2,
            )
        )

    if args.export:
        export_path = export_to_excel(args.export, diff_result, dedup_result=dedup_result)
        print(f"Exported workbook to {export_path}")

    return diff_result


def run_dedup(args: argparse.Namespace) -> DeduplicationResult:
    result, norm = _load_and_normalise(args.source)
    if args.show_preview:
        _print_preview(result)
    dedup_result = deduplicate(
        norm.data,
        subset=_normalise_list(_parse_column_list(args.subset), norm) or None,
        text_columns=_normalise_list(_parse_column_list(args.text_columns), norm),
        numeric_columns=_normalise_list(_parse_column_list(args.numeric_columns), norm),
        threshold=args.threshold,
    )
    print("Deduplication summary:")
    print(pd.DataFrame([dedup_result.summary()]).to_string(index=False))
    if args.export:
        path = Path(args.export)
        path.parent.mkdir(parents=True, exist_ok=True)
        with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
            dedup_result.exact.unique.to_excel(writer, sheet_name="去重后数据", index=False)
            dedup_result.exact.groups.to_excel(writer, sheet_name="重复明细", index=False)
            dedup_result.approximate.pairs.to_excel(writer, sheet_name="近似重复候选", index=False)
        print(f"Deduplication report saved to {path}")
    return dedup_result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Data comparison and deduplication toolkit")
    subparsers = parser.add_subparsers(dest="command")

    compare_parser = subparsers.add_parser("compare", help="Run dataset comparison")
    compare_parser.add_argument("left", help="Left dataset path (CSV/Excel/HTML)")
    compare_parser.add_argument("right", help="Right dataset path (CSV/Excel/HTML)")
    compare_parser.add_argument("--keys", help="Comma separated list of join keys")
    compare_parser.add_argument("--mappings", help="Comma separated column mappings in left:right format")
    compare_parser.add_argument("--auto-map-threshold", type=float, default=0.6, help="Minimum score for auto mappings")
    compare_parser.add_argument("--tolerance", type=float, default=0.0, help="Absolute numeric tolerance")
    compare_parser.add_argument(
        "--relative-tolerance",
        type=float,
        default=0.0,
        help="Relative numeric tolerance expressed as a proportion",
    )
    compare_parser.add_argument("--datetime-tolerance", help="Datetime tolerance, e.g. '1D' or '15min'")
    compare_parser.add_argument("--zero-equals-null", action="store_true", help="Treat 0 as equivalent to null")
    compare_parser.add_argument("--case-insensitive", action="store_true", help="Case insensitive string comparison")
    compare_parser.add_argument("--keep-whitespace", action="store_true", help="Disable trimming whitespace")
    compare_parser.add_argument("--show-preview", action="store_true", help="Display dataset previews")
    compare_parser.add_argument("--suggest-rules", action="store_true", help="Show rule suggestions")
    compare_parser.add_argument("--export", help="Excel export path")
    compare_parser.add_argument("--dedup", action="store_true", help="Run deduplication on the left dataset")
    compare_parser.add_argument("--dedup-subset", help="Subset columns for deduplication")
    compare_parser.add_argument("--dedup-text-columns", help="Text columns for approximate dedup")
    compare_parser.add_argument("--dedup-numeric-columns", help="Numeric columns for approximate dedup")
    compare_parser.add_argument("--dedup-threshold", type=float, default=0.85, help="Approximate dedup threshold")
    compare_parser.set_defaults(func=run_compare)

    dedup_parser = subparsers.add_parser("dedup", help="Run standalone deduplication")
    dedup_parser.add_argument("source", help="Dataset path")
    dedup_parser.add_argument("--subset", help="Subset columns for exact deduplication")
    dedup_parser.add_argument("--text-columns", help="Text columns for approximate dedup")
    dedup_parser.add_argument("--numeric-columns", help="Numeric columns for approximate dedup")
    dedup_parser.add_argument("--threshold", type=float, default=0.85, help="Approximate dedup threshold")
    dedup_parser.add_argument("--export", help="Excel file to store dedup results")
    dedup_parser.add_argument("--show-preview", action="store_true", help="Display dataset preview")
    dedup_parser.set_defaults(func=run_dedup)

    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    try:
        args.func(args)
    except Exception as exc:  # noqa: BLE001 - surface to CLI
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
