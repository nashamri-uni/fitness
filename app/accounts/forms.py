"""Forms for registration and profile management (FREQ-1, FREQ-13)."""
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import User, UserProfile, WeeklyWorkoutGoalHistory, WEEKLY_WORKOUT_GOAL_CHOICES


class LoginForm(AuthenticationForm):
    """Keep Django's authentication behavior while adding browser-friendly field hints."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {
                "autocomplete": "username",
                "placeholder": _("Enter your username"),
                "aria-describedby": "login-username-errors",
            }
        )
        self.fields["password"].widget.attrs.update(
            {
                "autocomplete": "current-password",
                "placeholder": _("Enter your password"),
                "aria-describedby": "login-password-errors",
            }
        )


class RegisterForm(forms.ModelForm):
    """UC-1: Register a new account."""

    weekly_workout_goal = forms.TypedChoiceField(
        label=_("Weekly workout goal (days)"),
        choices=[("", _("No goal set")), *WEEKLY_WORKOUT_GOAL_CHOICES],
        coerce=int,
        empty_value=None,
        required=False,
    )
    password1 = forms.CharField(
        label=_("Password"),
        help_text=_("Letters, numbers, and symbols are welcome."),
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        strip=False,
    )
    password2 = forms.CharField(
        label=_("Confirm password"),
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        strip=False,
    )
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        autocomplete = {
            "first_name": "given-name",
            "last_name": "family-name",
            "username": "username",
            "email": "email",
        }
        placeholders = {
            "username": _("Choose a username"),
            "email": _("Enter your email address"),
            "password1": _("Choose a password"),
            "password2": _("Confirm your password"),
        }
        for field_name, field in self.fields.items():
            described_by = f"register-{field_name.replace('_', '-')}-errors"
            if field_name == "password1":
                described_by = (
                    f"{described_by} register-password1-help register-password-checks"
                )
            elif field_name == "password2":
                described_by = f"{described_by} register-password-match"
            field.widget.attrs["aria-describedby"] = described_by
            if field_name in autocomplete:
                field.widget.attrs["autocomplete"] = autocomplete[field_name]
            if field_name in placeholders:
                field.widget.attrs["placeholder"] = placeholders[field_name]

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password1")
        if password:
            candidate_user = self.instance
            for field_name in ("first_name", "last_name", "username", "email"):
                setattr(candidate_user, field_name, cleaned_data.get(field_name, ""))
            try:
                validate_password(password, user=candidate_user)
            except ValidationError as error:
                self.add_error("password1", error)
        return cleaned_data

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(_("The two password fields do not match."))
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
