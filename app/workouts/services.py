"""Business logic for sessions and personal records (FREQ-10, FREQ-11)."""
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from exercises.tracking import exercise_kind

from .models import PersonalRecord, SessionExercise, SessionSet, WorkoutSession

# Metric name -> function that extracts the value from a logged set.
RECORD_METRICS = {
    PersonalRecord.RecordType.MAX_WEIGHT: lambda s: s.weight_kg,
    PersonalRecord.RecordType.MAX_REPS: lambda s: float(s.reps_completed),
    PersonalRecord.RecordType.MAX_VOLUME: lambda s: s.volume,
    PersonalRecord.RecordType.MAX_DURATION: lambda s: float(s.duration_seconds),
}


@transaction.atomic
def evaluate_personal_record(session_set):
    """Compare a logged set against the user's best values for that exercise.

    Updates (or creates) the personal record rows and flags the set itself as a
    personal record when at least one metric improved. Returns the list of
    record types that were beaten.
    """
    user = session_set.session.user
    exercise = session_set.exercise
    beaten = []

    for record_type, metric in RECORD_METRICS.items():
        value = metric(session_set)
        if value <= 0:
            continue

        record = PersonalRecord.objects.filter(
            user=user, exercise=exercise, record_type=record_type
        ).first()

        if record is None:
            PersonalRecord.objects.create(
                user=user,
                exercise=exercise,
                record_type=record_type,
                value=value,
                session_set=session_set,
                achieved_at=session_set.logged_at,
            )
            beaten.append(record_type)
        elif value > record.value:
            record.value = value
            record.session_set = session_set
            record.achieved_at = session_set.logged_at
            record.save()
            beaten.append(record_type)

    if beaten:
        session_set.is_personal_record = True
        session_set.save(update_fields=["is_personal_record"])

    return beaten


@transaction.atomic
def start_session(user, plan, name=None):
    """Create a session from a plan and copy the planned exercises into it (UC-18)."""
    from .models import SessionExercise, WorkoutSession

    session = WorkoutSession.objects.create(
        user=user,
        plan=plan,
        name=name or plan.name,
        started_at=timezone.now(),
    )
    for plan_exercise in plan.exercises.select_related("exercise").prefetch_related(
        "sets", "exercise__equipment_links__equipment"
    ):
        SessionExercise.objects.create(
            session=session,
            exercise=plan_exercise.exercise,
            order=plan_exercise.order,
            notes=plan_exercise.notes,
            targets={
                "kind": exercise_kind(plan_exercise.exercise),
                "rest_seconds": plan_exercise.rest_seconds,
                "sets": [
                    {
                        "set_number": number,
                        "reps_completed": item.reps,
                        "duration_seconds": item.duration_seconds,
                        "weight_kg": item.weight_kg,
                    }
                    for number, item in enumerate(plan_exercise.sets.all(), start=1)
                ],
            },
        )
    return session


def finish_session(session, notes="", rating=None):
    """Close a session and store the performance summary."""
    session.ended_at = timezone.now()
    session.duration_minutes = max(
        1, int((session.ended_at - session.started_at).total_seconds() // 60)
    )
    if notes:
        session.notes = notes
    if rating:
        session.rating = rating
    session.save()
    return session


def lock_active_session(session_id, user):
    """Acquire a write lock before reading mutable session data, including on SQLite."""
    if not WorkoutSession.objects.filter(
        pk=session_id, user=user, ended_at__isnull=True
    ).update(name=F("name")):
        return None
    # Serializes record updates for the same lifter across distinct sessions.
    get_user_model().objects.select_for_update().get(pk=user.pk)
    return WorkoutSession.objects.get(pk=session_id)


def recalculate_personal_records(entry, edited=None, removed=None):
    """Repair best values after an edit/undo without erasing historical PR flags."""
    scope = {"user_id": entry.session.user_id, "exercise_id": entry.exercise_id}
    rows = list(
        SessionSet.objects.filter(
            session_exercise__session__user_id=scope["user_id"],
            session_exercise__exercise_id=scope["exercise_id"],
        ).exclude(pk=removed).order_by("logged_at", "pk")
    )
    records = {record.record_type: record for record in PersonalRecord.objects.filter(**scope)}
    beaten = []
    new_best = False
    for record_type, metric in RECORD_METRICS.items():
        record = records.get(record_type)
        best = max(rows, key=metric, default=None)
        if edited is not None:
            edited_value = metric(edited)
            earlier = (
                row for row in rows
                if (row.logged_at, row.pk) < (edited.logged_at, edited.pk)
            )
            threshold = record.value if record and record.session_set_id is None else 0
            if edited_value > max(threshold, max((metric(row) for row in earlier), default=0)):
                beaten.append(record_type)
            if best and best.pk == edited.pk and edited_value > (record.value if record else 0):
                new_best = True
        # Historical imports may have a best value without a linked set.
        if record and record.session_set_id is None and (best is None or record.value >= metric(best)):
            continue
        if best is None or metric(best) <= 0:
            if record:
                record.delete()
        elif record is None:
            PersonalRecord.objects.create(
                **scope, record_type=record_type, value=metric(best),
                session_set=best, achieved_at=best.logged_at,
            )
        elif record.session_set_id != best.pk or record.value != metric(best):
            record.session_set = best
            record.value = metric(best)
            record.achieved_at = best.logged_at
            record.save(update_fields=["session_set", "value", "achieved_at"])
    if edited is not None:
        edited.is_personal_record = bool(beaten)
        edited.save(update_fields=["is_personal_record"])
    return new_best
