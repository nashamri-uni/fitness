"""Forms for logging workout sessions (FREQ-8)."""
from django import forms

from .models import SessionSet, WorkoutSession


class SessionSetForm(forms.ModelForm):
    """UC-18: record the actual performance of a completed set."""

    class Meta:
        model = SessionSet
        fields = ["set_number", "reps_completed", "weight_kg", "duration_seconds", "rpe"]

    def clean_reps_completed(self):
        value = self.cleaned_data.get("reps_completed")
        if value is not None and value < 0:
            raise forms.ValidationError("Repetitions cannot be negative.")
        return value

    def clean_rpe(self):
        value = self.cleaned_data.get("rpe")
        if value is not None and not 1 <= value <= 10:
            raise forms.ValidationError("RPE must be between 1 and 10.")
        return value


class CompleteSessionForm(forms.ModelForm):
    class Meta:
        model = WorkoutSession
        fields = ["notes", "rating"]

    def clean_rating(self):
        value = self.cleaned_data.get("rating")
        if value is not None and not 1 <= value <= 5:
            raise forms.ValidationError("Rating must be between 1 and 5.")
        return value
