"""Workout plan views (UC-8 to UC-17)."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from .forms import AddExerciseForm, PlanExerciseForm, PlanSetForm, WorkoutPlanForm
from .models import PlanExercise, PlanSet, WorkoutPlan


@login_required
def plan_list(request):
    """UC-14: view saved workout plans."""
    plans = WorkoutPlan.objects.filter(user=request.user)
    return render(request, "plans/list.html", {"plans": plans})


@login_required
def plan_detail(request, pk):
    """UC-13/UC-15: view a saved plan and reuse it."""
    plan = get_object_or_404(WorkoutPlan, pk=pk, user=request.user)

    if request.method == "POST":
        form = AddExerciseForm(request.POST, plan=plan)
        if form.is_valid():
            entry = PlanExercise.objects.create(
                plan=plan,
                exercise=form.cleaned_data["exercise"],
                order=form.cleaned_data.get("order") or plan.exercises.count() + 1,
                rest_seconds=form.cleaned_data.get("rest_seconds") or 90,
            )
            messages.success(request, _("Added %(name)s to the plan.") % {"name": entry.exercise.display_name()})
            return redirect("plans:detail", pk=plan.pk)
    else:
        form = AddExerciseForm(plan=plan)

    entries = [
        {
            "entry": entry,
            "set_form": PlanSetForm(initial={"set_number": entry.sets.count() + 1}),
            "exercise_form": PlanExerciseForm(instance=entry),
        }
        for entry in plan.exercises.all()
    ]

    return render(
        request,
        "plans/detail.html",
        {"plan": plan, "add_form": form, "entries": entries},
    )


@login_required
def create_plan(request):
    """UC-8: create a personalized workout routine."""
    if request.method == "POST":
        form = WorkoutPlanForm(request.POST)
        if form.is_valid():
            plan = form.save(commit=False)
            plan.user = request.user
            plan.save()
            messages.success(request, _("Plan '%(name)s' created. Add exercises to it.") % {"name": plan.name})
            return redirect("plans:detail", pk=plan.pk)
    else:
        form = WorkoutPlanForm()
    return render(request, "plans/form.html", {"form": form, "action": _("Create plan")})


@login_required
def edit_plan(request, pk):
    """UC-16: edit a workout plan."""
    plan = get_object_or_404(WorkoutPlan, pk=pk, user=request.user)
    if request.method == "POST":
        form = WorkoutPlanForm(request.POST, instance=plan)
        if form.is_valid():
            form.save()
            messages.success(request, _("Plan updated."))
            return redirect("plans:detail", pk=plan.pk)
    else:
        form = WorkoutPlanForm(instance=plan)
    return render(request, "plans/form.html", {"form": form, "action": _("Edit plan"), "plan": plan})


@login_required
def delete_plan(request, pk):
    """UC-17: delete a workout plan."""
    plan = get_object_or_404(WorkoutPlan, pk=pk, user=request.user)
    if request.method == "POST":
        plan.delete()
        messages.success(request, _("Plan deleted."))
        return redirect("plans:list")
    return render(request, "plans/confirm_delete.html", {"plan": plan})


@login_required
def edit_plan_exercise(request, pk):
    """UC-10: reorder or annotate an exercise inside a plan."""
    entry = get_object_or_404(PlanExercise, pk=pk, plan__user=request.user)
    if request.method == "POST":
        form = PlanExerciseForm(request.POST, instance=entry)
        if form.is_valid():
            form.save()
            messages.success(request, _("Exercise settings saved."))
            return redirect("plans:detail", pk=entry.plan.pk)
    return redirect("plans:detail", pk=entry.plan.pk)


@login_required
def remove_plan_exercise(request, pk):
    entry = get_object_or_404(PlanExercise, pk=pk, plan__user=request.user)
    if request.method == "POST":
        plan_pk = entry.plan.pk
        entry.delete()
        messages.success(request, _("Exercise removed from the plan."))
        return redirect("plans:detail", pk=plan_pk)
    return redirect("plans:detail", pk=entry.plan.pk)


@login_required
def add_set(request, pk):
    """UC-11: add a set to a planned exercise."""
    entry = get_object_or_404(PlanExercise, pk=pk, plan__user=request.user)
    if request.method == "POST":
        form = PlanSetForm(request.POST)
        if form.is_valid():
            set_obj = form.save(commit=False)
            set_obj.plan_exercise = entry
            set_obj.save()
            messages.success(request, _("Set %(number)s saved for %(name)s.") % {"number": set_obj.set_number, "name": entry.exercise.display_name()})
        else:
            messages.error(request, _("Invalid set values. Please correct them and try again."))
    return redirect("plans:detail", pk=entry.plan.pk)


@login_required
def delete_set(request, pk):
    set_obj = get_object_or_404(PlanSet, pk=pk, plan_exercise__plan__user=request.user)
    if request.method == "POST":
        plan_pk = set_obj.plan_exercise.plan.pk
        set_obj.delete()
        messages.success(request, _("Set removed."))
        return redirect("plans:detail", pk=plan_pk)
    return redirect("plans:detail", pk=set_obj.plan_exercise.plan.pk)
