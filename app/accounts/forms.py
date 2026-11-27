"""Forms for registration and profile management (FREQ-1, FREQ-13)."""
from django import forms
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import User, UserProfile, WeeklyWorkoutGoalHistory, WEEKLY_WORKOUT_GOAL_CHOICES


class RegisterForm(forms.ModelForm):
    """UC-1: Register a new account."""

    weekly_workout_goal = forms.TypedChoiceField(
        label=_("Weekly workout goal (days)"),
        choices=[("", _("No goal set")), *WEEKLY_WORKOUT_GOAL_CHOICES],
        coerce=int,
        empty_value=None,
        required=False,
    )
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)
    field_order = [
        "first_name",
        "last_name",
        "username",
        "email",
        "gender",
        "weekly_workout_goal",
        "password1",
        "password2",
    ]

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email", "gender"]

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("The two password fields do not match.")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            with transaction.atomic():
                user.save()
                profile = UserProfile.objects.create(
                    user=user,
                    weekly_workout_goal=self.cleaned_data["weekly_workout_goal"],
                )
                WeeklyWorkoutGoalHistory.objects.create(
                    user=user,
                    goal_days=profile.weekly_workout_goal,
                    effective_at=timezone.now(),
                )
        return user


class ProfileForm(forms.ModelForm):
    """UC-28/UC-29: Update profile information and fitness preferences."""

    class Meta:
        model = UserProfile
        fields = ["date_of_birth", "height_cm", "weight_kg", "fitness_goal", "weekly_workout_goal"]
        widgets = {"date_of_birth": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._previous_weekly_workout_goal = self.instance.weekly_workout_goal

    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            with transaction.atomic():
                profile.save()
                if self._previous_weekly_workout_goal != profile.weekly_workout_goal:
                    WeeklyWorkoutGoalHistory.objects.create(
                        user=profile.user,
                        goal_days=profile.weekly_workout_goal,
                        effective_at=timezone.now(),
                    )
                self.save_m2m()
        return profile


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "gender"]
