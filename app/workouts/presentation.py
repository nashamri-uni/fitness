"""Data for the active logging screen and the read-only workout summary."""

from exercises.tracking import exercise_kind

from .models import SessionExercise


def set_values(item):
    return {
        "id": item.pk,
        "set_number": item.set_number,
        "reps_completed": item.reps_completed,
        "weight_kg": item.weight_kg,
        "duration_seconds": item.duration_seconds,
        "rpe": item.rpe,
        "record": item.is_personal_record,
    }


def previous_performance(entry, session):
    previous = (
        SessionExercise.objects.filter(
            exercise_id=entry.exercise_id,
            session__user_id=session.user_id,
            session__ended_at__lte=session.started_at,
            sets__isnull=False,
        )
        .order_by("-session__ended_at", "-session_id", "-pk")
        .prefetch_related("sets")
        .first()
    )
    return {item.set_number: set_values(item) for item in previous.sets.all()} if previous else {}


def active_exercise(entry, session):
    exercise = entry.exercise
    targets = entry.targets or {}
    kind = targets.get("kind") or exercise_kind(exercise)
    previous = previous_performance(entry, session)
    rows = {
        item["set_number"]: {"key": str(item["set_number"]), "target": item, "logged": None}
        for item in targets.get("sets", [])
    }
    legacy_rows = []
    for item in entry.sets.all():
        row = rows.setdefault(item.set_number, {
            "key": str(item.set_number), "target": None, "logged": None,
        })
        if row["logged"]:
            legacy_rows.append({"key": f"legacy-{item.pk}", "target": None, "logged": set_values(item)})
        else:
            row["logged"] = set_values(item)
    muscle_names = [muscle.display_name() for muscle in exercise.primary_muscles()]
    secondary = [muscle.display_name() for muscle in exercise.secondary_muscles()]
    return {
        "id": entry.pk,
        "name": exercise.display_name(),
        "kind": kind,
        "weighted": kind == "resistance" or (
            kind == "bodyweight" and any(
                item and item["weight_kg"] > 0
                for item in [*previous.values(), *(row["target"] for row in rows.values()),
                             *(row["logged"] for row in rows.values())]
            )
        ),
        "rest": targets.get("rest_seconds", 0),
        "muscles": muscle_names or secondary,
        "all_muscles": list(dict.fromkeys([*muscle_names, *secondary])),
        "equipment": [item.display_name() for item in exercise.equipment_list()],
        "thumbnail": exercise.local_thumbnail_url,
        "animation": exercise.local_image_url,
        "instructions": exercise.instructions or exercise.description,
        "previous": previous,
        "rows": [*(rows[number] for number in sorted(rows)), *legacy_rows],
    }


def workout_summary(session):
    entries = list(session.exercises.all())
    logged = [item for entry in entries for item in entry.sets.all()]
    completed = [
        entry for entry in entries
        if entry.sets.all()
        and {target["set_number"] for target in (entry.targets or {}).get("sets", [])}
        <= {item.set_number for item in entry.sets.all()}
    ]
    return {
        "exercises": len(completed),
        "sets": len(logged),
        "volume": round(sum(item.volume for item in logged), 1),
        "seconds": sum(item.duration_seconds for item in logged),
        "average_rpe": session.average_rpe(),
        "records": [item for item in logged if item.is_personal_record],
    }
