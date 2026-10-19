"""Analytics dashboard views (UC-21, UC-23, UC-26, UC-27)."""
import json

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .services import exercise_progress, recent_personal_records, summary, weekly_volume


@login_required
def dashboard(request):
    """UC-26/UC-27: analytics dashboard with progress charts and trends."""
    stats = summary(request.user)
    chart = weekly_volume(request.user, weeks=12)
    progress = exercise_progress(request.user)
    records = recent_personal_records(request.user)

    from workouts.models import WorkoutSession

    recent_sessions = WorkoutSession.objects.filter(user=request.user).select_related("plan")[:8]

    context = {
        "stats": stats,
        "chart": chart,
        "chart_json": json.dumps(chart),
        "progress": progress,
        "records": records,
        "recent_sessions": recent_sessions,
    }
    return render(request, "analytics/dashboard.html", context)


@login_required
def progress(request):
    """UC-21/UC-23: per-exercise progress over time and improvement metrics."""
    context = {
        "progress": exercise_progress(request.user, limit=20),
        "chart_json": json.dumps(weekly_volume(request.user, weeks=12)),
        "chart": weekly_volume(request.user, weeks=12),
    }
    return render(request, "analytics/progress.html", context)
