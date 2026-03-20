from flask import Flask, render_template, request, redirect, url_for, abort
from engine import load_exercises, index_by_id, check_answer, neighbours
from logger import log_attempt, ensure_log_file

APP_TITLE = "Mental Models Trainer"
EXERCISES_PATH = "exercises.json"
LOG_PATH = "logs.csv"

app = Flask(__name__)

# Load exercises once at the start
_exercises_list = load_exercises(EXERCISES_PATH)
_exercises_by_id = index_by_id(_exercises_list)
_exercise_ids = [ex["exercise_id"] for ex in _exercises_list]

CATEGORY_ORDER = [
    ("variable_reassignment", "Variables and Reassignment"),
    ("assignment_vs_equality", "Assignment vs Equality"),
    ("loop_boundaries", "Loop Boundaries"),
    ("return_vs_print_and_scope", "Return, Print and Scope"),
]

CATEGORY_DESCRIPTIONS = {
    "variable_reassignment": "In this section, focus on how variables change over time. Work through reassignment step by step and pay attention to how updated values are used in later lines.",
    "assignment_vs_equality": "In this section, focus on the difference between assigning a value and checking whether two values are equal.",
    "loop_boundaries": "In this section, focus on where loops start and stop. Pay close attention to whether the final number is included and how many times the loop actually runs.",
    "return_vs_print_and_scope": "In this section, focus on what a function returns, what it only prints, and which variables are local to a function rather than outside it.",
}

CATEGORY_EXERCISES = {}
for category_key, _category_label in CATEGORY_ORDER:
    CATEGORY_EXERCISES[category_key] = [
        ex for ex in _exercises_list if ex["misconception"] == category_key
    ]

ensure_log_file(LOG_PATH)

@app.route("/")
def index():
    categories = []
    for category_key, category_label in CATEGORY_ORDER:
        items = CATEGORY_EXERCISES.get(category_key, [])
        categories.append({
            "key": category_key,
            "label": category_label,
            "description": CATEGORY_DESCRIPTIONS.get(category_key, ""),
            "count": len(items),
            "first_exercise_id": items[0]["exercise_id"] if items else None,
        })

    return render_template(
        "index.html",
        title=APP_TITLE,
        categories=categories,
    )

@app.route("/topic/<category_key>")
def topic_page(category_key: str):
    category_label = dict(CATEGORY_ORDER).get(category_key)
    if category_label is None:
        abort(404)

    exercises = CATEGORY_EXERCISES.get(category_key, [])

    return render_template(
        "topic.html",
        title=APP_TITLE,
        category_key=category_key,
        category_label=category_label,
        category_description=CATEGORY_DESCRIPTIONS.get(category_key, ""),
        exercises=exercises,
    )


@app.route("/exercise/<exercise_id>", methods=["GET", "POST"])
def exercise_page(exercise_id: str):
    ex = _exercises_by_id.get(exercise_id)
    if ex is None:
        abort(404)

    prev_id, next_id = neighbours(_exercise_ids, exercise_id)

    result = None
    if request.method == "POST":
        user_answer = request.form.get("answer", "")
        result = check_answer(ex, user_answer)

        log_attempt(
            LOG_PATH,
            exercise_id=str(ex["exercise_id"]),
            misconception=str(ex["misconception"]),
            raw_answer=result["raw_answer"],
            normalised_answer=result["normalised_answer"],
            result=result["result"],
            wrong_key=result["wrong_key"],
        )

    return render_template(
        "exercise.html",
        title=APP_TITLE,
        exercise=ex,
        result=result,
        prev_id=prev_id,
        next_id=next_id,
        category_key=ex["misconception"],
        category_label=dict(CATEGORY_ORDER).get(ex["misconception"], ex["misconception"]),
    )


@app.route("/start")
def start():
    first_category_key = CATEGORY_ORDER[0][0] if CATEGORY_ORDER else None
    if not first_category_key:
        return redirect(url_for("index"))
    return redirect(url_for("topic_page", category_key=first_category_key))

if __name__ == "__main__":
    # For local development
    app.run(debug=True)