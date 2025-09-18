import pandas as pd

from datacompare.dedup.dedup import (
    DeduplicationResult,
    deduplicate,
    find_approximate_duplicates,
    find_exact_duplicates,
)


def build_dataset() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": [1, 1, 2, 3, 4, 4],
            "name": [
                "Acme",
                "Acme",
                "Bravo",
                "Charlie",
                "Sichuan Grid",
                "Sichuan Main Grid",
            ],
            "value": [10, 10, 20, 30, 40, 41],
        }
    )


def test_find_exact_duplicates_groups_rows():
    df = build_dataset()
    result = find_exact_duplicates(df, subset=["id", "name"])
    assert len(result.duplicates) == 2
    assert "dedup_group_id" in result.groups.columns
    assert result.groups["is_primary"].sum() == 2


def test_find_approximate_duplicates_detects_similar_text():
    df = build_dataset()
    approx = find_approximate_duplicates(df, text_columns=["name"], numeric_columns=["value"], threshold=0.7)
    assert not approx.pairs.empty
    candidate = approx.pairs.iloc[0]
    assert candidate["score"] >= 0.7


def test_deduplicate_combines_results():
    df = build_dataset()
    result = deduplicate(df, subset=["id", "name"], text_columns=["name"], numeric_columns=["value"], threshold=0.7)
    assert isinstance(result, DeduplicationResult)
    summary = result.summary()
    assert "exact_duplicates" in summary and "approximate_pairs" in summary
