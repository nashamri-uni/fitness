"""Workout session views (UC-18, UC-19, UC-20, UC-25)."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
from django.urls import reverse

from plans.models import WorkoutPlan

from .forms import CompleteSessionForm, SessionSetForm
from .models import SessionExercise, WorkoutSession
from .presentation import active_exercise, set_values, workout_summary
from .services import (
    evaluate_personal_record, finish_session, lock_active_session,
    recalculate_personal_records, start_or_resume_session,
)


@login_required
def session_list(request):
    """UC-19: view workout history."""
    sessions = WorkoutSession.objects.filter(user=request.user).select_related("plan")
    return render(request, "workouts/session_list.html", {"sessions": sessions})


@login_required
def session_detail(request, pk):
    """UC-20: review the performance metrics of a session."""
    session = get_object_or_404(
        WorkoutSession.objects.filter(user=request.user).prefetch_related("exercises__exercise", "exercises__sets"),
        pk=pk,
    )
    return render(request, "workouts/session_detail.html", {"session": session, "summary": workout_summary(session)})


@login_required
def start_session_view(request, plan_pk):
    """UC-18: begin a tracked session from a saved plan (UC-15 reuse)."""
    if request.method != "POST":
        return redirect("plans:detail", pk=plan_pk)

    plan = get_object_or_404(WorkoutPlan, pk=plan_pk, user=request.user)
    if not plan.exercises.exists():
        messages.error(request, _("This plan has no exercises yet. Add exercises before starting a session."))
        return redirect("plans:detail", pk=plan.pk)

    session = start_or_resume_session(request.user, plan)
    return redirect("workouts:active", pk=session.pk)


@login_required
def active_session(request, pk):
    """UC-18: log sets during an in-progress session."""
    session = get_object_or_404(WorkoutSession, pk=pk, user=request.user)

    if session.is_finished:
        return redirect("workouts:detail", pk=session.pk)

    entries = [
        {"entry": entry, "data": active_exercise(entry, session)}
        for entry in session.exercises.select_related("exercise").prefetch_related(
            "sets", "exercise__muscle_links__muscle_group", "exercise__equipment_links__equipment",
        )
    ]

    return render(
        request,
        "workouts/active_session.html",
        {
            "session": session,
            "entries": entries,
            "workout_data": [item["data"] for item in entries],
        },
    )


@login_required
@require_POST
def log_set(request, pk):
    """Log, edit or undo one set, without writing planned or draft values."""
    entry = get_object_or_404(
        SessionExercise.objects.select_related("session", "exercise"), pk=pk, session__user=request.user,
    )
    ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    def error(message, status=400):
        if ajax:
            return JsonResponse({"error": message}, status=status)
        messages.error(request, message)
        return redirect("workouts:active", pk=entry.session_id)

    operation = request.POST.get("operation", "log")
    if operation not in {"log", "edit", "undo"}:
        return error(_("Unknown set action."))
    with transaction.atomic():
        if not lock_active_session(entry.session_id, request.user):
            return error(_("This workout is already finished."), 409)
        logged = None
        if operation != "log":
            identifier = request.POST.get("logged_id", "")
            if not identifier.isascii() or not identifier.isdecimal() or len(identifier) > 19:
                return error(_("This set is no longer available."), 409)
            logged = entry.sets.filter(pk=int(identifier)).first()
            if logged is None:
                if operation == "undo" and ajax:
                    return JsonResponse({"set": None})
                return error(_("This set is no longer available."), 409)

        if operation == "undo":
            recalculate_personal_records(entry, removed=logged.pk)
            logged.delete()
            result = {"set": None}
        else:
            data = request.POST.copy()
            if logged:
                data["set_number"] = logged.set_number
                if "rpe" not in data:
                    data["rpe"] = logged.rpe or ""
            form = SessionSetForm(data, instance=logged)
            if not form.is_valid():
                return error(" ".join(str(item) for errors in form.errors.values() for item in errors))
            item = form.save(commit=False)
            item.session_exercise = entry
            if operation == "log":
                existing = entry.sets.filter(set_number=item.set_number).first()
                if existing:
                    if any(getattr(existing, field) != getattr(item, field) for field in form.fields):
                        return error(_("This set was already logged. Refresh to see the saved values."), 409)
                    return JsonResponse({"set": set_values(existing), "new_record": False}) if ajax else redirect(
                        "workouts:active", pk=entry.session_id,
                    )
            item.save()
            if operation == "log":
                new_record = bool(evaluate_personal_record(item))
            else:
                new_record = recalculate_personal_records(entry, edited=item)
            result = {"set": set_values(item), "new_record": new_record}
    if ajax:
        return JsonResponse(result)
    return redirect("workouts:active", pk=entry.session_id)


@login_required
@require_POST
def complete_session(request, pk):
    """UC-18: finish the session and store the summary."""
    session = get_object_or_404(WorkoutSession, pk=pk, user=request.user)

    ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    summary_url = reverse("workouts:detail", args=[session.pk])
    with transaction.atomic():
        session = lock_active_session(pk, request.user)
        if session:
            form = CompleteSessionForm(request.POST, instance=session)
            entries = session.exercises.prefetch_related("sets")
            incomplete = any(
                {target["set_number"] for target in (entry.targets or {}).get("sets", [])}
                - {item.set_number for item in entry.sets.all()}
                for entry in entries
            )
            error = None
            if incomplete and request.POST.get("allow_incomplete") != "yes":
                error = _("Some planned sets remain. Confirm to finish this workout.")
            elif not form.is_valid():
                error = _("Please correct the session details.")
            if error:
                if ajax:
                    return JsonResponse({"error": error, "incomplete": incomplete}, status=400)
                messages.error(request, error)
                return redirect("workouts:active", pk=pk)
            finish_session(form.save(commit=False))
    return JsonResponse({"url": summary_url}) if ajax else redirect(summary_url)


@login_required
def personal_records(request):
    """Keep saved links to the former records page working."""
    params = request.GET.copy()
    params["tab"] = "records"
    return redirect(f"{reverse('analytics:dashboard')}?{params.urlencode()}")
