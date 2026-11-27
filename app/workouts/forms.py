"""Forms for logging workout sessions (FREQ-8)."""
import math

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import SessionSet, WorkoutSession


class SessionSetForm(forms.ModelForm):
    """UC-18: record the actual performance of a completed set."""

    class Meta:
        model = SessionSet
        fields = ["set_number", "reps_completed", "weight_kg", "duration_seconds", "rpe"]

    def clean_set_number(self):
        value = self.cleaned_data["set_number"]
        if value < 1:
            raise forms.ValidationError(_("Set numbers start at 1."))
        return value

    def clean_weight_kg(self):
        value = self.cleaned_data["weight_kg"]
        if not math.isfinite(value) or value < 0 or value > 10000:
            raise forms.ValidationError(_("Enter a weight between 0 and 10,000 kg."))
        return value

    def clean_rpe(self):
        value = self.cleaned_data.get("rpe")
        if value is not None and not 1 <= value <= 10:
            raise forms.ValidationError(_("RPE must be between 1 and 10."))
        return value


class CompleteSessionForm(forms.ModelForm):
    class Meta:
        model = WorkoutSession
        fields = ["notes", "rating"]

    def clean_rating(self):
        value = self.cleaned_data.get("rating")
        if value is not None and not 1 <= value <= 5:
            raise forms.ValidationError(_("Rating must be between 1 and 5."))
        return value
