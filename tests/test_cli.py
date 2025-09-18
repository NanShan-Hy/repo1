from pathlib import Path

import pandas as pd

import cli


def write_csv(path: Path, df: pd.DataFrame) -> Path:
    df.to_csv(path, index=False)
    return path


def test_cli_compare_runs_successfully(tmp_path):
    left = pd.DataFrame({"id": [1, 2, 3], "value": [10, 20, 30]})
    right = pd.DataFrame({"id": [1, 2, 4], "value": [10, 21, 40]})
    left_path = write_csv(tmp_path / "left.csv", left)
    right_path = write_csv(tmp_path / "right.csv", right)
    exit_code = cli.main(["compare", str(left_path), str(right_path)])
    assert exit_code == 0


def test_cli_dedup_runs_successfully(tmp_path):
    data = pd.DataFrame({"id": [1, 1, 2], "value": [10, 10, 20]})
    path = write_csv(tmp_path / "data.csv", data)
    exit_code = cli.main(["dedup", str(path), "--subset", "id,value"])
    assert exit_code == 0
