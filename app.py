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

ensure_log_file(LOG_PATH)


@app.route("/")
def index():
    return render_template(
        "index.html",
        title=APP_TITLE,
        exercises=_exercises_list,
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
    )


@app.route("/start")
def start():
    # Convenience: go to first exercise
    if not _exercise_ids:
        return redirect(url_for("index"))
    return redirect(url_for("exercise_page", exercise_id=_exercise_ids[0]))


if __name__ == "__main__":
    # For local development
    app.run(debug=True)