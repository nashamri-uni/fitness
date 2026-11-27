"""Forms for building and editing workout plans (FREQ-4 to FREQ-7)."""
from django import forms
from django.db.models import Q
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.translation import gettext_lazy as _

from exercises.models import Exercise

from .models import PlanExercise, PlanSet, TrainingGoal, WorkoutPlan


GOAL_DETAILS = {
    TrainingGoal.HYPERTROPHY: ("↗", _("Build muscle with resistance training.")),
    TrainingGoal.STRENGTH: ("◇", _("Improve the load you can lift.")),
    TrainingGoal.WEIGHT_LOSS: ("◎", _("Combine strength work and conditioning.")),
    TrainingGoal.MAINTENANCE: ("=", _("Maintain your current fitness.")),
    TrainingGoal.CARDIO: ("∿", _("Improve cardiovascular fitness.")),
    TrainingGoal.ENDURANCE: ("∞", _("Sustain effort over longer workouts.")),
}


class CreateWorkoutProgramForm(forms.Form):
    goal = forms.ChoiceField(choices=TrainingGoal.choices, label=_("Training goal"), widget=forms.RadioSelect)
    program_name = forms.CharField(max_length=120, label=_("Program name"), initial=_("My program"))
    name = forms.CharField(max_length=120, label=_("First workout day"), initial=_("Day 1"))
    description = forms.CharField(
        required=False,
        max_length=4000,
        label=_("Description"),
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    estimated_duration_minutes = forms.IntegerField(
        min_value=1,
        max_value=2147483647,
        initial=45,
        label=_("Estimated duration (minutes)"),
        widget=forms.TextInput(attrs={"inputmode": "numeric"}),
    )


CARDIO_CONDITIONING_EXERCISES = (
    "Push-up",
    "Plank",
    "Burpee",
    "Jumping Jack",
    "Mountain Climber",
    "High Knees Lift Run",
)


def available_exercises_for_goal(goal):
    exercises = Exercise.objects.filter(is_active=True)
    if goal == TrainingGoal.CARDIO:
        exercises = exercises.filter(
            Q(exercise_type=Exercise.ExerciseType.CARDIO)
            | Q(name__in=CARDIO_CONDITIONING_EXERCISES)
        )
    return exercises


def available_exercises_for_plan(plan):
    if plan is None:
        return available_exercises_for_goal(None)
    program_goal = plan.program.goal if plan.program_id else None
    return available_exercises_for_goal(program_goal or plan.goal)


class WorkoutPlanForm(forms.ModelForm):
    estimated_duration_minutes = forms.IntegerField(
        min_value=1, max_value=2147483647, label=_("Estimated duration (minutes)"),
    )
    description = forms.CharField(required=False, max_length=4000, widget=forms.Textarea,
                                  label=_("Description"))
    class Meta:
        model = WorkoutPlan
        fields = ["name", "description", "estimated_duration_minutes"]


class AddExerciseForm(forms.Form):
    """UC-9: select an exercise from the library to add to the routine."""

    exercise = forms.ModelChoiceField(
        queryset=Exercise.objects.filter(is_active=True),
        label=_("Exercise"),
    )
    order = forms.IntegerField(required=False, min_value=1, label=_("Order"))
    rest_seconds = forms.IntegerField(
        required=False,
        min_value=0,
        initial=90,
        label=_("Rest seconds"),
    )

    def __init__(self, *args, plan=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.plan = plan
        exercises = available_exercises_for_plan(plan)
        if plan is not None:
            existing = [entry.exercise_id for entry in plan.exercises.all()]
            exercises = exercises.exclude(pk__in=existing)
        self.fields["exercise"].queryset = exercises


class PlanExerciseForm(forms.ModelForm):
    """UC-10: organise exercises inside a routine (order, notes, rest)."""

    class Meta:
        model = PlanExercise
        fields = ["order", "notes", "rest_seconds"]


class PlanSetForm(forms.ModelForm):
    """UC-11: define sets, repetitions, duration and target weight."""

    class Meta:
        model = PlanSet
        fields = ["set_number", "reps", "duration_seconds", "weight_kg", "set_type"]

    def clean_weight_kg(self):
        value = self.cleaned_data["weight_kg"]
        MinValueValidator(0)(value)
        MaxValueValidator(10000)(value)
        return value
