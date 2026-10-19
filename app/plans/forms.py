"""Forms for building and editing workout plans (FREQ-4 to FREQ-7)."""
from django import forms

from exercises.models import Exercise

from .models import PlanExercise, PlanSet, WorkoutPlan


class WorkoutPlanForm(forms.ModelForm):
    class Meta:
        model = WorkoutPlan
        fields = ["name", "description", "goal", "estimated_duration_minutes"]


class AddExerciseForm(forms.Form):
    """UC-9: select an exercise from the library to add to the routine."""

    exercise = forms.ModelChoiceField(queryset=Exercise.objects.filter(is_active=True))
    order = forms.IntegerField(required=False, min_value=1)
    rest_seconds = forms.IntegerField(required=False, min_value=0, initial=90)

    def __init__(self, *args, plan=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.plan = plan
        if plan is not None:
            existing = [entry.exercise_id for entry in plan.exercises.all()]
            self.fields["exercise"].queryset = Exercise.objects.filter(is_active=True).exclude(
                pk__in=existing
            )


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
