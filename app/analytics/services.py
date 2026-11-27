"""Analytics and improvement metrics (FREQ-9, FREQ-10, FREQ-12)."""
from datetime import datetime, time, timedelta

from django.db.models import Avg, Count
from django.utils import timezone

from accounts.models import UserProfile, WeeklyWorkoutGoalHistory
from plans.models import WorkoutPlan
from workouts.models import PersonalRecord, SessionSet, WorkoutSession


def _local_week_bounds(monday):
    current_timezone = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(monday, time.min), current_timezone)
    end = timezone.make_aware(datetime.combine(monday + timedelta(weeks=1), time.min), current_timezone)
    return start, end


def weekly_goal_progress(user, week_start=None):
    """Return completed sessions and unique active days for a user's local week."""
    today = timezone.localdate()
    current_monday = today - timedelta(days=today.weekday())
    monday = current_monday if week_start is None else week_start - timedelta(days=week_start.weekday())
    start, end = _local_week_bounds(monday)

    profile = UserProfile.objects.filter(user=user).only("weekly_workout_goal").first()
    if monday == current_monday:
        goal = profile.weekly_workout_goal if profile else None
    else:
        history = (
            WeeklyWorkoutGoalHistory.objects
            .filter(user=user, effective_at__lt=start)
            .order_by("-effective_at", "-pk")
            .first()
        )
        goal = history.goal_days if history else None

    started_at_values = list(
        WorkoutSession.objects.filter(
            user=user,
            ended_at__isnull=False,
            started_at__gte=start,
            started_at__lt=end,
        ).values_list("started_at", flat=True)
    )
    active_days = {
        timezone.localtime(started_at).date()
        for started_at in started_at_values
    }
    configured = goal is not None and 1 <= goal <= 7

    return {
        "week_start": monday,
        "sessions": len(started_at_values),
        "days": len(active_days),
        "goal": goal if configured else None,
        "percentage": min(round(len(active_days) * 100 / goal), 100) if configured else 0,
    }


def completed_sessions_this_week(user):
    """Return a user's completed sessions in the current local calendar week."""
    today = timezone.localdate()
    monday = today - timedelta(days=today.weekday())
    start, end = _local_week_bounds(monday)
    return (
        WorkoutSession.objects
        .filter(
            user=user,
            ended_at__isnull=False,
            started_at__gte=start,
            started_at__lt=end,
        )
        .select_related("plan")
        .order_by("-started_at")
    )


def summary(user, weeks=12):
    """Headline numbers for the analytics dashboard."""
    sessions = WorkoutSession.objects.filter(user=user, ended_at__isnull=False)
    sets = SessionSet.objects.filter(session_exercise__session__user=user)
    goal_progress = weekly_goal_progress(user)

    start = timezone.now() - timedelta(weeks=weeks)
    recent = sessions.filter(started_at__gte=start)

    return {
        "total_sessions": sessions.count(),
        "recent_sessions": recent.count(),
        "sessions_this_week": goal_progress["sessions"],
        "workout_plans": WorkoutPlan.objects.filter(user=user).count(),
        "total_sets": sets.count(),
        "total_volume_kg": round(sum(s.volume for s in sets), 1),
        "avg_session_minutes": round(sessions.aggregate(a=Avg("duration_minutes"))["a"] or 0, 1),
        "avg_rpe": round(sets.filter(rpe__isnull=False).aggregate(a=Avg("rpe"))["a"] or 0, 1),
        "personal_records": PersonalRecord.objects.filter(user=user).count(),
        "distinct_exercises": sets.aggregate(
            c=Count("session_exercise__exercise", distinct=True)
        )["c"],
        "avg_rating": round(sessions.filter(rating__isnull=False).aggregate(a=Avg("rating"))["a"] or 0, 1),
        "streak_weeks": training_streak(user),
        "weekly_goal_days": goal_progress["goal"],
        "weekly_goal_completed_days": goal_progress["days"],
        "weekly_goal_percent": goal_progress["percentage"],
    }


def weekly_volume(user, weeks=12):
    """Training volume grouped by ISO week for the progress chart."""
    start = timezone.now() - timedelta(weeks=weeks)
    rows = (
        SessionSet.objects
        .filter(
            session_exercise__session__user=user,
            session_exercise__session__ended_at__isnull=False,
            session_exercise__session__started_at__gte=start,
        )
        .values("session_exercise__session__started_at", "weight_kg", "reps_completed")
    )

    buckets = {}
    for row in rows:
        started = row["session_exercise__session__started_at"]
        year, week, _ = started.isocalendar()
        key = (year, week)
        if key not in buckets:
            buckets[key] = {"label": f"{year}-W{week:02d}", "volume": 0.0, "sets": 0}
        buckets[key]["volume"] += row["weight_kg"] * row["reps_completed"]
        buckets[key]["sets"] += 1

    ordered = [buckets[key] for key in sorted(buckets)]
    for item in ordered:
        item["volume"] = round(item["volume"], 1)
    return {
        "labels": [item["label"] for item in ordered],
        "volume": [item["volume"] for item in ordered],
        "sets": [item["sets"] for item in ordered],
        "rows": ordered,
    }


def workout_activity(user, weeks=12):
    """Completed workout days grouped by local calendar week and day."""
    today = timezone.localdate()
    current_monday = today - timedelta(days=today.weekday())
    first_monday = current_monday - timedelta(weeks=weeks - 1)
    next_monday = current_monday + timedelta(weeks=1)
    current_timezone = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(first_monday, time.min), current_timezone)
    end = timezone.make_aware(datetime.combine(next_monday, time.min), current_timezone)

    activity_by_week = {}
    for week_number in range(weeks):
        monday = first_monday + timedelta(weeks=week_number)
        activity_by_week[monday] = {}

    sessions = WorkoutSession.objects.filter(
        user=user,
        ended_at__isnull=False,
        started_at__gte=start,
        started_at__lt=end,
    ).values_list("started_at", flat=True)
    for started_at in sessions:
        local_date = timezone.localtime(started_at).date()
        monday = local_date - timedelta(days=local_date.weekday())
        daily_activity = activity_by_week[monday]
        daily_activity[local_date] = daily_activity.get(local_date, 0) + 1

    chart_weeks = []
    for monday, daily_activity in activity_by_week.items():
        days = [monday + timedelta(days=day) for day in range(7)]
        chart_weeks.append({
            "start": monday.isoformat(),
            "end": days[-1].isoformat(),
            "count": len(daily_activity),
            "days": [day.isoformat() for day in days],
            "daily": [daily_activity.get(day, 0) for day in days],
        })

    return {
        "current_week": current_monday.isoformat(),
        "has_activity": any(week["count"] for week in chart_weeks),
        "weeks": chart_weeks,
    }


def exercise_progress(user, limit=10):
    """Per-exercise improvement metrics: first logged value vs. current best (FREQ-10)."""
    best = {}
    for record in PersonalRecord.objects.filter(
        user=user, record_type=PersonalRecord.RecordType.MAX_WEIGHT
    ).select_related("exercise"):
        best[record.exercise_id] = {
            "id": record.exercise_id,
            "name": record.exercise.display_name(),
            "current": record.value,
        }

    # First weight the user logged for each exercise.
    first_values = {}
    rows = (
        SessionSet.objects
        .filter(session_exercise__session__user=user, weight_kg__gt=0)
        .order_by("logged_at")
        .values("session_exercise__exercise_id", "weight_kg")
    )
    for row in rows:
        first_values.setdefault(row["session_exercise__exercise_id"], row["weight_kg"])

    results = []
    for exercise_id, info in best.items():
        first = first_values.get(exercise_id)
        change = round((info["current"] - first) / first * 100, 1) if first else 0.0
        results.append(
            {
                "id": exercise_id,
                "name": info["name"],
                "first": first,
                "current": info["current"],
                "change_pct": change,
            }
        )

    results.sort(key=lambda item: item["current"], reverse=True)
    return results[:limit]


def recent_personal_records(user, limit=10):
    return PersonalRecord.objects.filter(user=user).select_related("exercise")[:limit]


def training_streak(user, weeks=None):
    """Consecutive local calendar weeks with at least one completed session."""
    today = timezone.localdate()
    current_monday = today - timedelta(days=today.weekday())
    _, end = _local_week_bounds(current_monday)
    sessions = WorkoutSession.objects.filter(
        user=user,
        ended_at__isnull=False,
        started_at__lt=end,
    )
    if weeks is not None:
        first_monday = current_monday - timedelta(weeks=weeks - 1)
        start, _ = _local_week_bounds(first_monday)
        sessions = sessions.filter(started_at__gte=start)

    streak = 0
    cursor = current_monday
    current_week_active = False
    for started_at in sessions.order_by("-started_at").values_list("started_at", flat=True).iterator():
        local_started = timezone.localtime(started_at).date()
        active_week = local_started - timedelta(days=local_started.weekday())
        if active_week == cursor:
            current_week_active = True
            streak = max(streak, 1)
        elif not current_week_active:
            break
        elif active_week == cursor - timedelta(weeks=1):
            streak += 1
            cursor = active_week
        elif active_week < cursor - timedelta(weeks=1):
            break
    return streak
