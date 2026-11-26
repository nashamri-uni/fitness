"""Workout plan views (UC-8 to UC-17)."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _, gettext_lazy as _lazy

from exercises.models import Exercise, ExerciseMuscleGroup

from .forms import AddExerciseForm, PlanExerciseForm, PlanSetForm, WorkoutPlanForm
from .models import PlanExercise, PlanSet, WorkoutPlan


def _build_exercise_categories(exercises):
    """Group available exercises once, preferring their primary muscle mapping."""
    category_definitions = (
        ("upper", _lazy("Upper body")),
        ("lower", _lazy("Lower body")),
        ("cardio", _lazy("Cardio")),
        ("other", _lazy("Free Exercises")),
    )
    categories = {
        key: {"key": key, "name": name, "groups": {}, "exercises": [], "exercise_count": 0}
        for key, name in category_definitions
    }

    for exercise in exercises:
        links = list(exercise.muscle_links.all())
        muscle_link = next(
            (link for link in links if link.role == ExerciseMuscleGroup.Role.PRIMARY),
            links[0] if links else None,
        )

        if exercise.exercise_type == Exercise.ExerciseType.CARDIO:
            category_key = "cardio"
        elif muscle_link and muscle_link.muscle_group.body_region in {"upper", "lower"}:
            category_key = muscle_link.muscle_group.body_region
        else:
            category_key = "other"

        category = categories[category_key]
        if category_key in {"upper", "lower"}:
            group = category["groups"].setdefault(
                muscle_link.muscle_group_id,
                {"name": muscle_link.muscle_group.display_name(), "exercises": []},
            )
            group["exercises"].append(exercise)
        else:
            category["exercises"].append(exercise)
        category["exercise_count"] += 1

    return [
        {
            "name": category["name"],
            "key": category["key"],
            "exercise_count": category["exercise_count"],
            "groups": list(category["groups"].values()),
            "exercises": category["exercises"],
        }
        for category in categories.values()
        if category["groups"] or category["exercises"]
    ]


@login_required
def plan_list(request):
    """UC-14: view saved workout plans."""
    plans = WorkoutPlan.objects.filter(user=request.user)
    search_query = request.GET.get("q", "").strip()
    if search_query:
        plans = plans.filter(name__icontains=search_query)
    return render(request, "plans/list.html", {"plans": plans, "search_query": search_query})


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

    exercises = list(
        form.fields["exercise"].queryset.prefetch_related(
            Prefetch(
                "muscle_links",
                queryset=ExerciseMuscleGroup.objects.select_related("muscle_group").order_by(
                    "role", "muscle_group__name"
                ),
            )
        )
    )
    selected_exercise = form["exercise"].value()

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
        {
            "plan": plan,
            "add_form": form,
            "entries": entries,
            "exercise_categories": _build_exercise_categories(exercises),
            "selected_exercise_id": "" if selected_exercise is None else str(selected_exercise),
        },
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
