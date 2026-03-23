from flask import Flask, render_template, request, redirect, url_for, abort, session
from engine import load_exercises, index_by_id, check_answer, neighbours
from logger import log_attempt, ensure_log_file

APP_TITLE = "Mental Models Trainer"
EXERCISES_PATH = "exercises.json"
PRETEST_PATH = "pretest.json"
POSTTEST_PATH = "posttest.json"
LOG_PATH = "logs.csv"

app = Flask(__name__)
app.secret_key = "dev-secret-key"

# Load exercises once at the start
_exercises_list = load_exercises(EXERCISES_PATH)
_exercises_by_id = index_by_id(_exercises_list)
_exercise_ids = [ex["exercise_id"] for ex in _exercises_list]

_pretest_list = load_exercises(PRETEST_PATH)
_pretest_by_id = index_by_id(_pretest_list)
_pretest_ids = [ex["exercise_id"] for ex in _pretest_list]
_posttest_list = load_exercises(POSTTEST_PATH)
_posttest_by_id = index_by_id(_posttest_list)
_posttest_ids = [ex["exercise_id"] for ex in _posttest_list]

TRAINING_IDS = [
    "VAR_01",
    "VAR_06",
    "EQ_01",
    "EQ_02",
    "LOOP_01",
    "LOOP_04",
    "LOOP_05",
    "RET_01",
    "RET_02",
]

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
        current_mode=session.get("mode", "training"),
    )

@app.route("/topic/<category_key>")
def topic_page(category_key: str):
    session["mode"] = "training"
    session["training_sequence"] = False
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


@app.route("/pretest")
def start_pretest():
    session["mode"] = "pretest"
    if not _pretest_ids:
        return redirect(url_for("index"))
    return redirect(url_for("exercise_page", exercise_id=_pretest_ids[0]))


@app.route("/training")
def start_training():
    session["mode"] = "training"
    session["training_sequence"] = True
    first_training_id = TRAINING_IDS[0] if TRAINING_IDS else None
    if not first_training_id:
        return redirect(url_for("index"))
    return redirect(url_for("exercise_page", exercise_id=first_training_id))


@app.route("/posttest")
def start_posttest():
    session["mode"] = "posttest"
    if not _posttest_ids:
        return redirect(url_for("index"))
    return redirect(url_for("exercise_page", exercise_id=_posttest_ids[0]))

@app.route("/study")
def study_start():
    session["study_mode"] = True
    session["mode"] = "pretest"
    return render_template("study_intro.html", title=APP_TITLE)


@app.route("/study/pretest/start")
def study_pretest_start():
    session["study_mode"] = True
    session["mode"] = "pretest"
    if not _pretest_ids:
        return redirect(url_for("index"))
    return redirect(url_for("exercise_page", exercise_id=_pretest_ids[0]))


@app.route("/study/training_intro")
def study_training_intro():
    session["study_mode"] = True
    session["mode"] = "training"
    return render_template("training_intro.html", title=APP_TITLE)


@app.route("/study/training/start")
def study_training_start():
    session["study_mode"] = True
    session["mode"] = "training"
    session["training_sequence"] = True
    first_training_id = TRAINING_IDS[0] if TRAINING_IDS else None
    if not first_training_id:
        return redirect(url_for("index"))
    return redirect(url_for("exercise_page", exercise_id=first_training_id))


@app.route("/study/posttest_intro")
def study_posttest_intro():
    session["study_mode"] = True
    session["mode"] = "posttest"
    return render_template("posttest_intro.html", title=APP_TITLE)


@app.route("/study/posttest/start")
def study_posttest_start():
    session["study_mode"] = True
    session["mode"] = "posttest"
    first_posttest_id = _posttest_ids[0] if _posttest_ids else None
    if not first_posttest_id:
        return redirect(url_for("index"))
    return redirect(url_for("exercise_page", exercise_id=first_posttest_id))


@app.route("/exercise/<exercise_id>", methods=["GET", "POST"])
def exercise_page(exercise_id: str):
    mode = session.get("mode", "training")

    if mode == "pretest":
        ex = _pretest_by_id.get(exercise_id)
        current_ids = _pretest_ids
    elif mode == "posttest":
        ex = _posttest_by_id.get(exercise_id)
        current_ids = _posttest_ids
    else:
        ex = _exercises_by_id.get(exercise_id)
        if session.get("training_sequence", False):
            current_ids = TRAINING_IDS
        else:
            current_ids = _exercise_ids

    if ex is None:
        abort(404)

    prev_id, next_id = neighbours(current_ids, exercise_id)

    result = None
    if request.method == "POST":
        user_answer = request.form.get("answer", "")
        result = check_answer(ex, user_answer)

        if mode != "training":
            result["feedback"] = ""

        log_attempt(
            LOG_PATH,
            exercise_id=str(ex["exercise_id"]),
            misconception=str(ex["misconception"]),
            raw_answer=result["raw_answer"],
            normalised_answer=result["normalised_answer"],
            result=result["result"],
            wrong_key=result["wrong_key"],
        )

        study_mode = session.get("study_mode", False)
        if study_mode:
            if next_id is not None:
                return redirect(url_for("exercise_page", exercise_id=next_id))

            if mode == "pretest":
                return redirect(url_for("study_training_intro"))

            if mode == "training":
                return redirect(url_for("study_posttest_intro"))

            if mode == "posttest":
                return redirect(url_for("study_end"))

    return render_template(
        "exercise.html",
        title=APP_TITLE,
        exercise=ex,
        result=result,
        prev_id=prev_id,
        next_id=next_id,
        category_key=ex["misconception"],
        category_label=dict(CATEGORY_ORDER).get(ex["misconception"], ex["misconception"]),
        current_mode=mode,
        study_mode=session.get("study_mode", False),
    )


@app.route("/start")
def start():
    return redirect(url_for("index"))

@app.route("/study/end")
def study_end():
    session.pop("training_sequence", None)
    session.pop("study_mode", None)
    session.pop("mode", None)
    return render_template("study_end.html", title=APP_TITLE)


if __name__ == "__main__":
    app.run(debug=True)