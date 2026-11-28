"""Data for the unified dashboard. Performance uses actual sets from finished workouts."""
from calendar import monthrange
from collections import Counter
from datetime import date, timedelta

from django.core.paginator import Paginator
from django.db.models import Count, Exists, Max, Min, OuterRef, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.translation import gettext as _

from exercises.models import Exercise, ExerciseMuscleGroup, MuscleGroup
from exercises.tracking import exercise_kind
from plans.models import PlanExercise, WorkoutPlan
from workouts.models import PersonalRecord, SessionSet, WorkoutSession
from workouts.services import unfinished_sessions

from .services import _local_week_bounds, training_streak, weekly_goal_progress, workout_activity


def overview_data(user, mode, week):
    completed = WorkoutSession.objects.filter(user=user, ended_at__isnull=False)
    now = timezone.localtime()
    monday = now.date() - timedelta(days=now.weekday())
    this_start, _ = _local_week_bounds(monday)
    previous_start, _ = _local_week_bounds(monday - timedelta(weeks=1))
    this_week = Q(started_at__gte=this_start, started_at__lte=now)
    previous_week = Q(started_at__gte=previous_start, started_at__lte=now - timedelta(weeks=1))
    totals = completed.aggregate(
        count=Count("pk", filter=this_week),
        minutes=Coalesce(Sum("duration_minutes", filter=this_week), 0),
        previous_count=Count("pk", filter=previous_week),
        previous_minutes=Coalesce(Sum("duration_minutes", filter=previous_week), 0),
        first=Min("started_at"),
    )
    comparable = totals["first"] is not None and totals["first"] < this_start
    deltas = {
        "count": totals["count"] - totals["previous_count"],
        "minutes": totals["minutes"] - totals["previous_minutes"],
    } if comparable else {}
    recent = completed.annotate(
        exercise_count=Count("exercises", filter=Q(exercises__sets__isnull=False), distinct=True),
        set_count=Count("exercises__sets"),
    ).order_by("-ended_at", "-started_at", "-pk").first()
    active_session = unfinished_sessions(user).first()
    activity = workout_activity(user, weeks=8)
    weeks = activity["weeks"]
    current = weeks[-1]
    selected_week = next((item for item in weeks if item["start"] == week), current)
    goal = weekly_goal_progress(user)
    today = timezone.localdate().isoformat()
    goal_days = [
        {"date": date.fromisoformat(day), "status": "done" if count else "upcoming" if day > today else "rest"}
        for day, count in zip(current["days"], current["daily"])
    ]
    goal["remaining"] = max(goal["goal"] - goal["days"], 0) if goal["goal"] else None

    if mode == "weekly":
        rows = [
            {"date": date.fromisoformat(week["start"]), "end": date.fromisoformat(week["end"]),
             "sessions": sum(week["daily"]), "days": week["count"]}
            for week in weeks
        ]
        previous, latest = rows[-3:-1]
        delta = latest["sessions"] - previous["sessions"] if latest["sessions"] or previous["sessions"] else None
        activity_end = current["end"]
    else:
        rows = [
            {"date": date.fromisoformat(day), "sessions": count}
            for day, count in zip(selected_week["days"], selected_week["daily"])
        ]
        delta = None
        activity_end = selected_week["end"]

    return {
        "totals": totals, "weekly_deltas": deltas,
        "streak": training_streak(user),
        "record_count": PersonalRecord.objects.filter(user=user).count(),
        "recent": recent,
        "active_session": active_session,
        "plans": WorkoutPlan.objects.filter(user=user, program__user=user)
        .filter(Exists(PlanExercise.objects.filter(plan_id=OuterRef("pk"))))
        .select_related("program").order_by("program__name", "program_id", "program_order", "pk") if not active_session else (),
        "goal": goal,
        "goal_days": goal_days,
        "activity_mode": mode,
        "activity_week": selected_week["start"],
        "activity_weeks": [
            (item["start"], date.fromisoformat(item["start"]), date.fromisoformat(item["end"]))
            for item in reversed(weeks)
        ],
        "activity_rows": rows,
        "activity_start": rows[0]["date"],
        "activity_end": date.fromisoformat(activity_end),
        "activity_delta": delta,
    }


def range_options():
    return [
        ("1m", _("1 month")), ("3m", _("3 months")),
        ("6m", _("6 months")), ("all", _("All time")),
    ]


def range_start(period):
    months = {"1m": 1, "3m": 3, "6m": 6}.get(period)
    if months is None:
        return None
    today = timezone.localdate()
    year, month_index = divmod(today.year * 12 + today.month - 1 - months, 12)
    month = month_index + 1
    return today.replace(year=year, month=month, day=min(today.day, monthrange(year, month)[1]))


def completed_sets(user, period="all"):
    sets = SessionSet.objects.filter(
        session_exercise__session__user=user,
        session_exercise__session__ended_at__isnull=False,
    )
    start = range_start(period)
    if start is not None:
        sets = sets.filter(session_exercise__session__started_at__gte=_local_week_bounds(start)[0])
    return sets


def metric_options(exercise):
    kind = exercise_kind(exercise)
    if kind == "cardio":
        return [("duration", _("Total duration"), _("s"), _("Sum of logged exercise time per workout."))]
    if kind == "timed":
        return [("hold", _("Longest hold"), _("s"), _("Longest logged hold per workout."))]
    options = [
        ("weight", _("Maximum weight"), _("kg"), _("Heaviest logged set with completed reps per workout.")),
        ("reps", _("Maximum repetitions"), _("reps"), _("Most repetitions in a single set per workout.")),
    ]
    if kind == "resistance":
        options.append((
            "e1rm", _("Estimated one-rep max"), _("kg"),
            _("Highest Epley estimate per workout, using weighted sets of 1 to 10 reps."),
        ))
    return options if kind == "resistance" else list(reversed(options))


def performance_points(sets, exercise, metric):
    aggregates = {}
    rows = sets.filter(session_exercise__exercise=exercise).order_by(
        "session_exercise__session__started_at", "session_exercise__session_id", "pk",
    ).values_list(
        "session_exercise__session_id", "session_exercise__session__started_at",
        "weight_kg", "reps_completed", "duration_seconds",
    )
    for session_id, started_at, weight, reps, seconds in rows.iterator():
        observation = aggregates.setdefault(session_id, [started_at, None])
        if metric in {"duration", "hold"}:
            value = seconds if seconds > 0 else None
        elif metric == "weight":
            value = weight if reps > 0 else None
        elif metric == "reps":
            value = reps if reps > 0 else None
        else:
            value = weight if reps == 1 and weight > 0 else (
                weight * (1 + reps / 30) if weight > 0 and 2 <= reps <= 10 else None
            )
        if value is None:
            continue
        prior = observation[1]
        observation[1] = value if prior is None else (
            prior + value if metric == "duration" else max(prior, value)
        )
    points = []
    for session_id, (start, value) in aggregates.items():
        points.append({
            "session": session_id, "date": timezone.localtime(start).date(),
            "timestamp": int(start.timestamp() * 1000),
            "value": round(value, 2) if value is not None else None,
        })
    return points


def performance_summary(points):
    values = [point["value"] for point in points if point["value"] is not None]
    if not values:
        return {}
    first, latest = values[0], values[-1]
    return {
        "first": first, "latest": latest, "best": max(values),
        "delta": change(first, latest) if len(values) > 1 else None,
        "previous": change(values[-2], latest) if len(values) > 1 else None,
    }


def change(baseline, latest):
    delta = round(latest - baseline, 2)
    return {"value": delta, "percent": round(delta * 100 / baseline, 1) if baseline else None}


def distribution_data(sets):
    counts = dict(sets.order_by().values("session_exercise__exercise_id").annotate(
        count=Count("pk"),
    ).values_list("session_exercise__exercise_id", "count"))
    classifications = {}
    links = ExerciseMuscleGroup.objects.filter(
        exercise_id__in=counts, role=ExerciseMuscleGroup.Role.PRIMARY,
    ).select_related("muscle_group").order_by()
    for link in links:
        classifications.setdefault(link.exercise_id, []).append(link.muscle_group)

    shares = Counter()
    names = {None: _("Unclassified")}
    for exercise, count in counts.items():
        groups = classifications.get(exercise)
        if not groups:
            shares[None] += count
            continue
        for group in groups:
            names[group.pk] = group.display_name()
            shares[group.pk] += count / len(groups)
    total = sum(counts.values())
    return [
        {"name": names[key], "sets": round(value, 2), "percent": round(value * 100 / total, 2)}
        for key, value in sorted(shares.items(), key=lambda item: (-item[1], str(names[item[0]])))
    ], total


def selected_range(params, key):
    period = params.get(key, "3m")
    return period if period in {"1m", "3m", "6m", "all"} else "3m"


def positive_id(value):
    return int(value) if value and len(value) <= 18 and value.isascii() and value.isdecimal() else None


def progress_data(user, params):
    period = selected_range(params, "range")
    muscle_period = selected_range(params, "muscle_range")
    history = completed_sets(user)
    exercises = list(Exercise.objects.filter(
        pk__in=history.order_by().values("session_exercise__exercise_id"),
    ).prefetch_related("muscle_links__muscle_group", "equipment_links__equipment"))
    exercises.sort(key=lambda item: item.display_name().casefold())
    exercise_id = positive_id(params.get("exercise"))
    chosen = next((item for item in exercises if item.pk == exercise_id), None)
    chosen = chosen or next(iter(exercises), None)
    metrics = metric_options(chosen) if chosen else []
    selected = next((item for item in metrics if item[0] == params.get("metric")), None)
    selected = selected or next(iter(metrics), None)
    points = performance_points(completed_sets(user, period), chosen, selected[0]) if selected else []
    distribution, distribution_total = distribution_data(completed_sets(user, muscle_period))
    return {
        "exercises": exercises, "chosen": chosen, "metrics": metrics, "metric": selected,
        "period": period, "muscle_period": muscle_period, "ranges": range_options(),
        "points": points, "observations": [point for point in points if point["value"] is not None],
        "performance": performance_summary(points), "chart_timezone": timezone.get_current_timezone_name(),
        "distribution": distribution, "distribution_total": distribution_total,
    }


def records_data(user, params):
    records = PersonalRecord.objects.filter(user=user)
    scoped = records.select_related("exercise", "session_set__session_exercise__session").order_by("-achieved_at", "-pk")
    q = params.get("q", "").strip()[:120]
    group_id = positive_id(params.get("muscle"))
    kind = params.get("type", "")
    muscles = list(MuscleGroup.objects.filter(
        exercise_links__exercise__personal_records__user=user,
    ).distinct())
    muscles.sort(key=lambda group: group.display_name().casefold())
    group_id = group_id if any(group.pk == group_id for group in muscles) else None
    kind = kind if kind in PersonalRecord.RecordType.values else ""
    filtered = scoped
    for term in q.split():
        filtered = filtered.filter(Q(exercise__name__icontains=term) | Q(exercise__name_ar__icontains=term))
    if group_id:
        filtered = filtered.filter(exercise__muscle_links__muscle_group_id=group_id)
    if kind:
        filtered = filtered.filter(record_type=kind)

    bests = records.aggregate(count=Count("pk"), exercises=Count("exercise", distinct=True))
    exercise_ids = filtered.values("exercise_id").annotate(latest=Max("achieved_at")).order_by("-latest", "exercise_id")
    page = Paginator(exercise_ids, 8).get_page(params.get("page"))
    grouped = {row["exercise_id"]: [] for row in page}
    for record in filtered.filter(exercise_id__in=grouped):
        grouped[record.exercise_id].append(record)
    filters = params.copy()
    filters.pop("page", None)
    filters["tab"] = "records"
    return {
        "bests": bests, "recent_records": list(scoped[:3]), "record_page": page,
        "record_groups": [(group[0].exercise, group) for group in grouped.values() if group],
        "q": q, "muscle_id": group_id, "muscles": muscles, "record_type": kind,
        "record_types": PersonalRecord.RecordType.choices, "record_query": filters.urlencode(),
    }
