import pandas as pd
import pytest

from datacompare.compare.diff import ColumnMapping, ComparisonConfig, ComparisonError, compute_diff


def build_frames():
    left = pd.DataFrame(
        {
            "id": [1, 2, 3, 4],
            "value": [10.0, 20.0, 30.0, 0.0],
            "text": ["Alpha", "Beta", "Gamma", "Delta"],
            "timestamp": pd.to_datetime(
                ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"]
            ),
        }
    )
    right = pd.DataFrame(
        {
            "id": [1, 2, 3, 5],
            "value": [10.0, 20.05, 29.5, 40.0],
            "text": ["alpha", "Beta", "GAMMA", "Epsilon"],
            "timestamp": pd.to_datetime(
                ["2024-01-01", "2024-01-02", "2024-01-02", "2024-01-04"]
            ),
        }
    )
    return left, right


def test_compute_diff_detects_mismatches():
    left, right = build_frames()
    mappings = [ColumnMapping(left="value", right="value", alias="value")]
    result = compute_diff(left, right, join_keys=["id"], mappings=mappings)
    assert len(result.mismatched) == 1
    mismatch_row = result.mismatched.iloc[0]
    assert mismatch_row["id"] == 3
    assert not result.details.empty
    assert set(result.summary().keys()) == {"matched", "mismatched", "left_only", "right_only", "differences"}


def test_compute_diff_with_tolerance_and_case_insensitive():
    left, right = build_frames()
    config = ComparisonConfig(absolute_tolerance=0.1, case_insensitive=True)
    mappings = [ColumnMapping(left="value", right="value", alias="value"), ColumnMapping(left="text", right="text")]
    result = compute_diff(left, right, join_keys=["id"], mappings=mappings, config=config)
    # Value mismatch should be tolerated; text should be case insensitive
    assert len(result.mismatched) == 0
    assert len(result.left_only) == 1
    assert len(result.right_only) == 1


def test_compute_diff_zero_equals_null_and_datetime_tolerance():
    left, right = build_frames()
    right.loc[right["id"] == 4, "value"] = pd.NA
    config = ComparisonConfig(treat_zero_as_null=True, datetime_tolerance="1D")
    mappings = [ColumnMapping(left="value", right="value"), ColumnMapping(left="timestamp", right="timestamp")]
    result = compute_diff(left, right, join_keys=["id"], mappings=mappings, config=config)
    assert len(result.mismatched) == 0


def test_compute_diff_duplicate_keys_raise_error():
    left, right = build_frames()
    left = pd.concat([left, pd.DataFrame({"id": [1], "value": [99], "text": ["Dup"], "timestamp": [pd.Timestamp("2024-01-01")]})])
    with pytest.raises(ComparisonError):
        compute_diff(left, right, join_keys=["id"], mappings=[ColumnMapping(left="value", right="value")])


def test_relative_tolerance_applies():
    left = pd.DataFrame({"id": [1], "value": [100.0]})
    right = pd.DataFrame({"id": [1], "value": [101.0]})
    config = ComparisonConfig(relative_tolerance=0.02)
    result = compute_diff(left, right, join_keys=["id"], mappings=[ColumnMapping(left="value", right="value")], config=config)
    assert len(result.mismatched) == 0
