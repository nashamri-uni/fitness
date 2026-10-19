"""Business logic for sessions and personal records (FREQ-10, FREQ-11)."""
from django.db import transaction

from .models import PersonalRecord

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


def start_session(user, plan, name=None):
    """Create a session from a plan and copy the planned exercises into it (UC-18)."""
    from django.utils import timezone

    from .models import SessionExercise, WorkoutSession

    session = WorkoutSession.objects.create(
        user=user,
        plan=plan,
        name=name or plan.name,
        started_at=timezone.now(),
    )
    for plan_exercise in plan.exercises.all():
        SessionExercise.objects.create(
            session=session,
            exercise=plan_exercise.exercise,
            order=plan_exercise.order,
        )
    return session


def finish_session(session, notes="", rating=None):
    """Close a session and store the performance summary."""
    from django.utils import timezone

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
