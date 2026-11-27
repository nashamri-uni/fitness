"""Workout plan views (UC-8 to UC-17)."""
import json
import math

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Prefetch, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils.translation import gettext as _, gettext_lazy as _lazy

from exercises.models import Exercise, ExerciseMuscleGroup

from .forms import (
    AddExerciseForm,
    CreateWorkoutProgramForm,
    PlanExerciseForm,
    PlanSetForm,
    WorkoutPlanForm,
    available_exercises_for_plan,
)
from .models import PlanExercise, PlanSet, WorkoutPlan, WorkoutProgram


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


def _builder_exercise_kind(exercise):
    """Infer the builder inputs from movement names and equipment as well as type."""
    name = f"{exercise.name} {exercise.name_ar}".casefold()
    equipment = " ".join(
        link.equipment.name.casefold() for link in exercise.equipment_links.all()
    )
    timed_terms = ("plank", "wall sit", "hollow hold", "static hold", "dead hang")
    cardio_terms = ("treadmill", "elliptical", "stationary bike", "rowing machine", "stepper")
    if any(term in name for term in timed_terms):
        return "timed"
    if (
        exercise.exercise_type == Exercise.ExerciseType.CARDIO
        or any(term in name or term in equipment for term in cardio_terms)
    ):
        return "cardio"
    if not equipment or equipment == "bodyweight":
        return "bodyweight"
    return "resistance"


def _program_builder_data(program):
    """Serialize a user's program and exercise library for the interactive builder."""
    exercise_relations = (
        Prefetch(
            "muscle_links",
            queryset=ExerciseMuscleGroup.objects.select_related("muscle_group").order_by(
                "role", "muscle_group__name"
            ),
        ),
        "equipment_links__equipment",
    )
    library_query = Exercise.objects.filter(is_active=True).prefetch_related(*exercise_relations)
    categorized = _build_exercise_categories(list(library_query))

    def exercise_details(exercise):
        return {
            "id": exercise.pk,
            "name": exercise.display_name(),
            "english_name": exercise.name,
            "arabic_name": exercise.name_ar,
            "thumbnail": exercise.local_thumbnail_url,
            "animation": exercise.local_image_url,
            "kind": _builder_exercise_kind(exercise),
            "description": exercise.description,
            "instructions": exercise.instructions,
            "muscles": [
                {"name": link.muscle_group.display_name(), "role": link.role}
                for link in exercise.muscle_links.all()
            ],
            "equipment": [link.equipment.display_name() for link in exercise.equipment_links.all()],
        }

    library = []
    for category in categorized:
        category_data = {"category": str(category["name"]), "category_key": category["key"]}
        for exercise in category["exercises"]:
            library.append({**exercise_details(exercise), **category_data, "group": ""})
        for group in category["groups"]:
            for exercise in group["exercises"]:
                library.append({**exercise_details(exercise), **category_data, "group": str(group["name"])})

    plans = list(
        program.days.filter(user_id=program.user_id).order_by("program_order", "id")
        .prefetch_related("exercises__exercise", "exercises__sets")
    )
    catalog_ids = {exercise["id"] for exercise in library}
    retired_ids = {
        entry.exercise_id for plan in plans for entry in plan.exercises.all()
        if entry.exercise_id not in catalog_ids
    }
    retired = [
        exercise_details(exercise)
        for exercise in Exercise.objects.filter(pk__in=retired_ids).prefetch_related(*exercise_relations)
    ]
    days = []
    for plan in plans:
        entries = []
        for entry in plan.exercises.all():
            entries.append(
                {
                    "exercise_id": entry.exercise_id,
                    "thumbnail": entry.exercise.local_thumbnail_url,
                    "rest_seconds": entry.rest_seconds,
                    "notes": entry.notes,
                    "sets": [
                        {
                            "id": item.pk,
                            "reps": item.reps,
                            "duration_seconds": item.duration_seconds,
                            "weight_kg": item.weight_kg,
                            "set_type": item.set_type,
                        }
                        for item in entry.sets.all()
                    ],
                }
            )
        days.append(
            {
                "id": plan.pk,
                "name": plan.name,
                "description": plan.description,
                "estimated_duration_minutes": plan.estimated_duration_minutes,
                "goal": plan.goal,
                "allowed_exercise_ids": list(
                    available_exercises_for_plan(plan).values_list("pk", flat=True)
                ),
                "exercises": entries,
            }
        )

    return {
        "program": {"id": program.pk, "name": program.name},
        "days": days,
        "exercises": library,
        "retired_exercises": retired,
    }


@login_required
def plan_list(request):
    """UC-14: view saved workout plans."""
    plans = WorkoutPlan.objects.filter(user=request.user).select_related("program")
    search_query = request.GET.get("q", "").strip()
    if search_query:
        plans = plans.filter(name__icontains=search_query) | plans.filter(program__name__icontains=search_query)
    programs = WorkoutProgram.objects.filter(user=request.user).prefetch_related(
        Prefetch(
            "days",
            queryset=WorkoutPlan.objects.filter(user=request.user)
            .order_by("program_order", "id").prefetch_related("exercises"),
        )
    )
    if search_query:
        programs = programs.filter(
            Q(name__icontains=search_query) | Q(days__name__icontains=search_query)
        ).distinct()
    program_rows = []
    for program in programs:
        days = list(program.days.all())
        for day in days:
            day.exercise_count = len(day.exercises.all())
        if search_query and search_query.casefold() not in program.name.casefold():
            days = [day for day in days if search_query.casefold() in day.name.casefold()]
        program_rows.append(
            {
                "program": program,
                "days": days,
                "day_count": len(days),
                "exercise_count": sum(day.exercise_count for day in days),
                "estimated_minutes": sum(day.estimated_duration_minutes for day in days),
            }
        )
    return render(
        request,
        "plans/list.html",
        {"plans": plans, "programs": program_rows, "search_query": search_query},
    )


@login_required
def plan_detail(request, pk):
    """UC-13/UC-15: view a saved plan and reuse it."""
    plan = get_object_or_404(WorkoutPlan, pk=pk, user=request.user, program__user=request.user)

    if request.method == "POST":
        form = AddExerciseForm(request.POST, plan=plan)
        if form.is_valid():
            order = form.cleaned_data.get("order")
            rest_seconds = form.cleaned_data.get("rest_seconds")
            entry = PlanExercise.objects.create(
                plan=plan,
                exercise=form.cleaned_data["exercise"],
                order=order if order is not None else plan.exercises.count() + 1,
                rest_seconds=rest_seconds if rest_seconds is not None else 90,
            )
            for number in range(1, 4):
                PlanSet.objects.create(plan_exercise=entry, set_number=number)
            messages.success(request, _("Added %(name)s to the plan.") % {"name": entry.exercise.display_name()})
            return redirect("plans:detail", pk=plan.pk)
    else:
        form = AddExerciseForm(plan=plan)

    exercises = list(
        available_exercises_for_plan(plan).prefetch_related(
            Prefetch(
                "muscle_links",
                queryset=ExerciseMuscleGroup.objects.select_related("muscle_group").order_by(
                    "role", "muscle_group__name"
                ),
            ),
            "equipment_links__equipment",
        )
    )
    builder_data = _program_builder_data(plan.program)

    return render(
        request,
        "plans/builder.html",
        {
            "plan": plan,
            "program": plan.program,
            "exercise_categories": _build_exercise_categories(exercises),
            "builder_data": builder_data,
            "selected_plan_id": plan.pk,
            "add_form": form,
        },
    )


@login_required
def program_builder(request, pk):
    program = get_object_or_404(WorkoutProgram, pk=pk, user=request.user)
    first_day = program.days.filter(user=request.user).order_by("program_order", "id").first()
    start_new_day = request.GET.get("new_day") == "1" or first_day is None
    return render(
        request,
        "plans/builder.html",
        {
            "program": program,
            "plan": None,
            "builder_data": _program_builder_data(program),
            "selected_plan_id": "" if start_new_day else first_day.pk,
            "start_new_day": start_new_day,
        },
    )


@login_required
def create_plan(request):
    """Create a custom program with its first workout day."""
    if request.method == "POST":
        form = CreateWorkoutProgramForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                program = WorkoutProgram.objects.create(
                    user=request.user,
                    name=form.cleaned_data["program_name"],
                )
                plan = WorkoutPlan.objects.create(
                    user=request.user,
                    program=program,
                    program_order=1,
                    name=form.cleaned_data["name"],
                    description=form.cleaned_data["description"],
                    estimated_duration_minutes=form.cleaned_data["estimated_duration_minutes"],
                )
            messages.success(request, _("Program '%(name)s' created. Add exercises to your first day.") % {"name": program.name})
            return redirect("plans:detail", pk=plan.pk)
    else:
        form = CreateWorkoutProgramForm()
    return render(request, "plans/form.html", {"form": form, "action": _("Create workout program")})


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


def _validated_integer(value, field, minimum=0):
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or value > 2147483647
    ):
        raise ValueError(
            _("%(field)s must be a whole number of at least %(minimum)s.")
            % {"field": field, "minimum": minimum}
        )
    return value


@login_required
@require_POST
def save_program_builder(request, pk):
    """Validate and atomically save every day and set in a program draft."""
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": _("Invalid save data.")}, status=400)
    if not isinstance(payload, dict) or not isinstance(payload.get("days"), list):
        return JsonResponse({"error": _("Invalid save data.")}, status=400)
    get_object_or_404(WorkoutProgram, pk=pk, user=request.user)

    try:
        program_name = payload.get("name")
        if not isinstance(program_name, str) or not program_name.strip() or len(program_name.strip()) > 120:
            raise ValueError(_("Enter a program name of 120 characters or fewer."))
        if len(payload["days"]) > 50:
            raise ValueError(_("A program can contain up to 50 workout days."))

        with transaction.atomic():
            program = get_object_or_404(
                WorkoutProgram.objects.select_for_update(),
                pk=pk,
                user=request.user,
            )
            existing_days = {
                day.pk: day
                for day in WorkoutPlan.objects.filter(program=program, user=request.user)
            }
            seen_day_ids = set()
            saved_day_ids = set()
            client_keys = {}
            saved_records = {}
            seen_client_keys = set()
            program.name = program_name.strip()
            program.save(update_fields=["name", "updated_at"])

            for day_order, day_data in enumerate(payload["days"], start=1):
                if not isinstance(day_data, dict):
                    raise ValueError(_("Invalid workout day data."))
                client_key = day_data.get("client_key")
                if not isinstance(client_key, str) or not client_key or client_key in seen_client_keys:
                    raise ValueError(_("Invalid workout day data."))
                seen_client_keys.add(client_key)
                day_id = day_data.get("id")
                if day_id is not None:
                    day_id = _validated_integer(day_id, _("Workout day ID"), 1)
                    if day_id not in existing_days or day_id in seen_day_ids:
                        raise ValueError(_("A workout day could not be found in this program."))
                    plan = existing_days[day_id]
                    seen_day_ids.add(day_id)
                else:
                    plan = WorkoutPlan(user=request.user, program=program)

                name = day_data.get("name")
                if not isinstance(name, str) or not name.strip() or len(name.strip()) > 120:
                    raise ValueError(_("Each workout day needs a name of 120 characters or fewer."))
                duration = _validated_integer(
                    day_data.get("estimated_duration_minutes"),
                    _("Estimated duration"),
                    1,
                )
                description = day_data.get("description", "")
                exercise_data_list = day_data.get("exercises")
                if not isinstance(description, str) or len(description) > 4000:
                    raise ValueError(_("Workout day descriptions must be 4,000 characters or fewer."))
                if not isinstance(exercise_data_list, list) or len(exercise_data_list) > 100:
                    raise ValueError(_("Invalid exercise list."))

                plan.name = name.strip()
                plan.description = description
                plan.estimated_duration_minutes = duration
                plan.program_order = day_order
                plan.save()
                saved_day_ids.add(plan.pk)

                seen_exercise_ids = set()
                saved_exercises = {}
                for exercise_order, exercise_data in enumerate(exercise_data_list, start=1):
                    if not isinstance(exercise_data, dict):
                        raise ValueError(_("Invalid exercise data."))
                    exercise_id = _validated_integer(
                        exercise_data.get("exercise_id"),
                        _("Exercise ID"),
                        1,
                    )
                    if exercise_id in seen_exercise_ids:
                        raise ValueError(_("An exercise can only appear once in a workout day."))
                    seen_exercise_ids.add(exercise_id)

                    entry = PlanExercise.objects.filter(plan=plan, exercise_id=exercise_id).first()
                    if entry is None:
                        exercise = available_exercises_for_plan(plan).filter(pk=exercise_id).first()
                        if exercise is None:
                            raise ValueError(_("Select an available exercise."))
                        entry = PlanExercise(plan=plan, exercise=exercise)
                    rest_seconds = _validated_integer(
                        exercise_data.get("rest_seconds"),
                        _("Rest time"),
                        0,
                    )
                    notes = exercise_data.get("notes", "")
                    set_data_list = exercise_data.get("sets")
                    if not isinstance(notes, str) or len(notes) > 255:
                        raise ValueError(_("Exercise notes must be 255 characters or fewer."))
                    if not isinstance(set_data_list, list) or len(set_data_list) > 50:
                        raise ValueError(_("Invalid set list."))

                    entry.order = exercise_order
                    entry.rest_seconds = rest_seconds
                    entry.notes = notes
                    entry.save()

                    existing_sets = {item.pk: item for item in entry.sets.all()}
                    removed_set_ids_data = exercise_data.get("removed_set_ids", [])
                    if not isinstance(removed_set_ids_data, list):
                        raise ValueError(_("Invalid set list."))
                    removed_set_ids = {
                        _validated_integer(set_id, _("Set ID"), 1)
                        for set_id in removed_set_ids_data
                    }
                    if len(removed_set_ids) != len(removed_set_ids_data) or not removed_set_ids.issubset(existing_sets):
                        raise ValueError(_("A set could not be found for this exercise."))
                    kept_set_ids = set()
                    submitted_existing_ids = set()
                    saved_set_ids = []
                    for set_number, set_data in enumerate(set_data_list, start=1):
                        if not isinstance(set_data, dict):
                            raise ValueError(_("Invalid set data."))
                        set_id = set_data.get("id")
                        if set_id is not None:
                            set_id = _validated_integer(set_id, _("Set ID"), 1)
                            if set_id not in existing_sets or set_id in kept_set_ids or set_id in removed_set_ids:
                                raise ValueError(_("A set could not be found for this exercise."))
                            set_obj = existing_sets[set_id]
                            kept_set_ids.add(set_id)
                            submitted_existing_ids.add(set_id)
                        else:
                            set_obj = PlanSet(plan_exercise=entry)

                        reps = _validated_integer(set_data.get("reps"), _("Repetitions"), 0)
                        duration_seconds = _validated_integer(
                            set_data.get("duration_seconds"),
                            _("Duration"),
                            0,
                        )
                        weight = set_data.get("weight_kg")
                        try:
                            valid_weight = (
                                not isinstance(weight, bool)
                                and isinstance(weight, (float, int))
                                and math.isfinite(float(weight))
                                and 0 <= weight <= 10000
                            )
                        except OverflowError:
                            valid_weight = False
                        if not valid_weight:
                            raise ValueError(_("Weight must be a non-negative number."))
                        set_type = set_data.get("set_type", PlanSet.SetType.NORMAL)
                        if set_type not in PlanSet.SetType.values:
                            raise ValueError(_("Select a valid set type."))
                        set_obj.set_number = set_number
                        set_obj.reps = reps
                        set_obj.duration_seconds = duration_seconds
                        set_obj.weight_kg = weight
                        set_obj.set_type = set_type
                        set_obj.save()
                        kept_set_ids.add(set_obj.pk)
                        saved_set_ids.append(set_obj.pk)

                    if existing_sets.keys() - submitted_existing_ids - removed_set_ids:
                        raise ValueError(_("Existing sets must be kept or explicitly removed."))
                    entry.sets.filter(pk__in=removed_set_ids).delete()
                    saved_exercises[str(exercise_id)] = {
                        "id": entry.pk,
                        "sets": saved_set_ids,
                    }

                plan.exercises.exclude(exercise_id__in=seen_exercise_ids).delete()
                client_keys[client_key] = plan.pk
                saved_records[client_key] = {
                    "id": plan.pk,
                    "exercises": saved_exercises,
                }

            program.days.filter(user=request.user).exclude(pk__in=saved_day_ids).delete()
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    except Http404:
        return JsonResponse({"error": _("A workout day or exercise could not be found.")}, status=400)

    return JsonResponse({
        "ok": True,
        "program_name": program.name,
        "days": client_keys,
        "records": saved_records,
    })
