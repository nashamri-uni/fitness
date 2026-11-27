"""Routes for the unified training dashboard."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from .dashboard import overview_data, progress_data, records_data


@login_required
def dashboard(request):
    tab = request.GET.get("tab", "overview")
    if tab == "progress":
        context = progress_data(request.user, request.GET)
    elif tab == "records":
        context = records_data(request.user, request.GET)
    else:
        tab = "overview"
        activity = "weekly" if request.GET.get("activity") == "weekly" else "daily"
        context = overview_data(request.user, activity, request.GET.get("week"))
    return render(request, "analytics/dashboard.html", {"tab": tab, **context})


@login_required
def progress(request):
    """Keep saved links to the former progress page working."""
    params = request.GET.copy()
    params["tab"] = "progress"
    return redirect(f"{reverse('analytics:dashboard')}?{params.urlencode()}")
