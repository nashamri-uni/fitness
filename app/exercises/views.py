"""Exercise library views (UC-4 to UC-7, UC-30, UC-31, UC-32)."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from django.utils.translation import gettext as _

from .forms import ExerciseForm
from .models import Equipment, Exercise, MuscleGroup


@login_required
def library(request):
    """UC-4/UC-5/UC-6/UC-30/UC-31: browse, search and filter the exercise library."""
    exercises = Exercise.objects.filter(is_active=True).select_related("created_by")

    muscle_group = request.GET.get("muscle_group", "")
    equipment = request.GET.get("equipment", "")
    difficulty = request.GET.get("difficulty", "")
    exercise_type = request.GET.get("type", "")
    query = request.GET.get("q", "")

    if muscle_group:
        exercises = exercises.filter(muscle_links__muscle_group_id=muscle_group)
    if equipment:
        exercises = exercises.filter(equipment_links__equipment_id=equipment)
    if difficulty:
        exercises = exercises.filter(difficulty=difficulty)
    if exercise_type:
        exercises = exercises.filter(exercise_type=exercise_type)
    if query:
        exercises = exercises.filter(Q(name__icontains=query) | Q(description__icontains=query))

    exercises = exercises.distinct()

    paginator = Paginator(exercises, 12)
    page = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "exercises/library.html",
        {
            "page_obj": page,
            "paginator": paginator,
            "muscle_groups": MuscleGroup.objects.all(),
            "equipment": Equipment.objects.all(),
            "selected": {
                "muscle_group": muscle_group,
                "equipment": equipment,
                "difficulty": difficulty,
                "type": exercise_type,
                "q": query,
            },
            "DIFFICULTY_CHOICES": Exercise.Difficulty.choices,
            "TYPE_CHOICES": Exercise.ExerciseType.choices,
        },
    )


@login_required
def exercise_detail(request, pk):
    """UC-7: view exercise details."""
    exercise = get_object_or_404(Exercise, pk=pk)
    return render(request, "exercises/detail.html", {"exercise": exercise})


def admin_required(view_func):
    """Restrict a view to project administrators (FREQ-15)."""
    from functools import wraps

    from django.contrib.auth.decorators import login_required as lr

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not (request.user.is_project_admin or request.user.is_staff):
            messages.error(request, _("Only administrators can manage the exercise library."))
            return redirect("exercises:library")
        return view_func(request, *args, **kwargs)

    return lr(wrapper)


@admin_required
def manage_exercises(request):
    """UC-32: administrator exercise library management."""
    exercises = Exercise.objects.select_related("created_by").order_by("name")
    return render(request, "exercises/manage.html", {"exercises": exercises})


@admin_required
def create_exercise(request):
    if request.method == "POST":
        form = ExerciseForm(request.POST)
        if form.is_valid():
            form.instance.created_by = request.user
            exercise = form.save()
            messages.success(request, _("Exercise '%(name)s' added.") % {"name": exercise.name})
            return redirect("exercises:manage")
    else:
        form = ExerciseForm()
    return render(request, "exercises/form.html", {"form": form, "action": _("Add exercise")})


@admin_required
def edit_exercise(request, pk):
    exercise = get_object_or_404(Exercise, pk=pk)
    if request.method == "POST":
        form = ExerciseForm(request.POST, instance=exercise)
        if form.is_valid():
            form.save()
            messages.success(request, _("Exercise '%(name)s' updated.") % {"name": exercise.name})
            return redirect("exercises:manage")
    else:
        form = ExerciseForm(instance=exercise)
    return render(request, "exercises/form.html", {"form": form, "action": _("Edit exercise"), "exercise": exercise})


@admin_required
def delete_exercise(request, pk):
    exercise = get_object_or_404(Exercise, pk=pk)
    if request.method == "POST":
        exercise.delete()
        messages.success(request, _("Exercise '%(name)s' deleted.") % {"name": exercise.name})
        return redirect("exercises:manage")
    return render(request, "exercises/confirm_delete.html", {"exercise": exercise})


