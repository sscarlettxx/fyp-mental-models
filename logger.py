import csv
from datetime import datetime
from pathlib import Path
from typing import Optional


LOG_HEADER = [
    "timestamp",
    "exercise_id",
    "misconception",
    "raw_answer",
    "normalised_answer",
    "result",
    "wrong_key",
]


def ensure_log_file(path: str | Path) -> None:
    p = Path(path)
    if p.exists():
        return
    with p.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(LOG_HEADER)


def log_attempt(
    path: str | Path,
    exercise_id: str,
    misconception: str,
    raw_answer: str,
    normalised_answer: str,
    result: str,
    wrong_key: Optional[str],
) -> None:
    p = Path(path)
    ensure_log_file(p)
    with p.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().isoformat(timespec="seconds"),
            exercise_id,
            misconception,
            raw_answer,
            normalised_answer,
            result,
            wrong_key or "",
        ])