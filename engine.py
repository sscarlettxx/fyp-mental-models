import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def load_exercises(path: str | Path) -> List[Dict[str, Any]]:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("exercises.json must be a JSON list (top-level []).")

    required = {"exercise_id", "misconception", "prompt", "correct_answer", "wrong_answers"}
    for ex in data:
        if not isinstance(ex, dict):
            raise ValueError("Each exercise must be a JSON object.")
        missing = required - set(ex.keys())
        if missing:
            raise ValueError(f"Exercise missing keys {missing}: {ex}")

        if not isinstance(ex["wrong_answers"], dict):
            raise ValueError(f'Exercise {ex.get("exercise_id")} wrong_answers must be an object.')

    return data


def index_by_id(exercises: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    by_id: Dict[str, Dict[str, Any]] = {}
    for ex in exercises:
        ex_id = str(ex["exercise_id"])
        if ex_id in by_id:
            raise ValueError(f"Duplicate exercise_id: {ex_id}")
        by_id[ex_id] = ex
    return by_id


def normalise_answer(s: str) -> str:
    """
    - get rid of outer whitespace
    - collapse inner whitespace
    - replace commas with spaces (helps '2,2' vs '2 2')
    - remove spaces around  operators (+-*/=<>)
    - treat 'syntaxerror' non case sensitive
    """
    s = (s or "").strip()

    s = s.replace(",", " ")
    s = re.sub(r"\s+", " ", s)

    # Remove spaces around operators
    s = re.sub(r"\s*([+\-*/=<>])\s*", r"\1", s)

    if s.lower() == "syntaxerror":
        return "SyntaxError"

    return s


def _accepted_correct(exercise: Dict[str, Any]) -> List[str]:
    """
    Allows either a single correct_answer or a list of accepted_correct variants.
    """
    accepted = []

    # Canonical correct answer
    accepted.append(str(exercise.get("correct_answer", "")))

    # Optional variants
    variants = exercise.get("accepted_correct")
    if isinstance(variants, list):
        accepted.extend(str(v) for v in variants)

    # Normalise all
    return [normalise_answer(x) for x in accepted if str(x).strip() != ""]


def check_answer(
    exercise: Dict[str, Any],
    user_input: str
) -> Dict[str, Any]:
    """
    Returns a structured result the UI can display.
    """
    raw = user_input or ""
    norm = normalise_answer(raw)

    accepted = _accepted_correct(exercise)
    if norm in accepted:
        return {
            "result": "correct",
            "raw_answer": raw,
            "normalised_answer": norm,
            "wrong_key": None,
            "feedback": exercise.get("feedback_correct") or "Correct.",
            "correct_answer": str(exercise.get("correct_answer", "")),
        }

    wrong_answers: Dict[str, str] = exercise.get("wrong_answers", {}) or {}
    # Match against normalised keys
    for wrong_key, meaning in wrong_answers.items():
        if norm == normalise_answer(str(wrong_key)):
            # If you later add rich feedback, you can store it here instead of 'meaning'
            return {
                "result": "known_wrong",
                "raw_answer": raw,
                "normalised_answer": norm,
                "wrong_key": str(wrong_key),
                "feedback": meaning,
                "correct_answer": str(exercise.get("correct_answer", "")),
            }

    return {
        "result": "other_wrong",
        "raw_answer": raw,
        "normalised_answer": norm,
        "wrong_key": None,
        "feedback": "Incorrect.",
        "correct_answer": str(exercise.get("correct_answer", "")),
    }


def neighbours(exercise_ids: List[str], current_id: str) -> Tuple[Optional[str], Optional[str]]:
    if current_id not in exercise_ids:
        return None, None
    i = exercise_ids.index(current_id)
    prev_id = exercise_ids[i - 1] if i > 0 else None
    next_id = exercise_ids[i + 1] if i < len(exercise_ids) - 1 else None
    return prev_id, next_id