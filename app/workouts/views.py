"""Workout session views (UC-18, UC-19, UC-20, UC-25)."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

from plans.models import WorkoutPlan

from .forms import CompleteSessionForm, SessionSetForm
from .models import PersonalRecord, SessionExercise, WorkoutSession
from .services import evaluate_personal_record, finish_session, start_session


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
    return render(request, "workouts/session_detail.html", {"session": session})


@login_required
def start_session_view(request, plan_pk):
    """UC-18: begin a tracked session from a saved plan (UC-15 reuse)."""
    if request.method != "POST":
        return redirect("plans:detail", pk=plan_pk)

    plan = get_object_or_404(WorkoutPlan, pk=plan_pk, user=request.user)
    if not plan.exercises.exists():
        messages.error(request, _("This plan has no exercises yet. Add exercises before starting a session."))
        return redirect("plans:detail", pk=plan.pk)

    session = start_session(request.user, plan)
    messages.success(request, _("Session '%(name)s' started. Good luck!") % {"name": session.name})
    return redirect("workouts:active", pk=session.pk)


@login_required
def active_session(request, pk):
    """UC-18: log sets during an in-progress session."""
    session = get_object_or_404(WorkoutSession, pk=pk, user=request.user)

    if session.is_finished:
        return redirect("workouts:detail", pk=session.pk)

    entries = []
    for entry in session.exercises.select_related("exercise"):
        planned = []
        if session.plan:
            plan_entry = session.plan.exercises.filter(exercise=entry.exercise).first()
            planned = list(plan_entry.sets.all()) if plan_entry else []
        entries.append(
            {
                "entry": entry,
                "planned_sets": planned,
                "logged_sets": list(entry.sets.all()),
                "form": SessionSetForm(initial={"set_number": entry.sets.count() + 1}),
            }
        )

    return render(
        request,
        "workouts/active_session.html",
        {
            "session": session,
            "entries": entries,
            "complete_form": CompleteSessionForm(),
            "elapsed_minutes": int((timezone.now() - session.started_at).total_seconds() // 60),
        },
    )


@login_required
def log_set(request, pk):
    """UC-18/UC-24: store one logged set and detect personal records."""
    entry = get_object_or_404(SessionExercise, pk=pk, session__user=request.user)

    if request.method == "POST":
        form = SessionSetForm(request.POST)
        if form.is_valid():
            set_obj = form.save(commit=False)
            set_obj.session_exercise = entry
            set_obj.save()

            beaten = evaluate_personal_record(set_obj)
            if beaten:
                labels = ", ".join(str(dict(PersonalRecord.RecordType.choices)[r]) for r in beaten)
                messages.success(request, _("New personal record for %(name)s: %(labels)s.") % {"name": entry.exercise.display_name(), "labels": labels})
            else:
                messages.success(request, _("Set logged for %(name)s.") % {"name": entry.exercise.display_name()})
        else:
            errors = "; ".join(
                str(error) for errors in form.errors.values() for error in errors
            )
            messages.error(request, _("Could not log the set: %(errors)s") % {"errors": errors})

    return redirect("workouts:active", pk=entry.session.pk)


@login_required
def complete_session(request, pk):
    """UC-18: finish the session and store the summary."""
    session = get_object_or_404(WorkoutSession, pk=pk, user=request.user)

    if request.method == "POST":
        form = CompleteSessionForm(request.POST, instance=session)
        if form.is_valid():
            form.save()
            # ended_at and duration_minutes are derived from the recorded timestamps.
            finish_session(session)
            messages.success(request, _("Session '%(name)s' completed.") % {"name": session.name})
            return redirect("workouts:detail", pk=session.pk)
        messages.error(request, _("Please correct the session details."))

    return redirect("workouts:active", pk=session.pk)


@login_required
def personal_records(request):
    """UC-25: view personal records."""
    records = PersonalRecord.objects.filter(user=request.user).select_related("exercise", "session_set")
    return render(request, "workouts/records.html", {"records": records})
