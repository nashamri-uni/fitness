"""Views for authentication and profile (UC-1, UC-2, UC-3, UC-28, UC-29)."""
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.debug import sensitive_post_parameters

from .emails import users_with_email
from .forms import EMAIL_IN_USE, GoogleProfileForm, ProfileForm, RegisterForm, UserForm
from .models import User, UserProfile, WeeklyWorkoutGoalHistory


@sensitive_post_parameters("password1", "password2")
def register(request):
    """UC-1: Register new account."""
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
            except IntegrityError:
                if users_with_email(form.cleaned_data["email"]).exists():
                    form.add_error("email", EMAIL_IN_USE)
                elif User.objects.filter(username=form.cleaned_data["username"]).exists():
                    form.add_error("username", _("This username is already in use."))
                else:
                    raise
            else:
                login(request, user, backend="django.contrib.auth.backends.ModelBackend")
                messages.success(request, _("Account created successfully. You are now logged in."))
                return redirect("analytics:dashboard")
    else:
        form = RegisterForm()
    return render(request, "accounts/register.html", {"form": form})


@login_required
def complete_google_profile(request):
    user = request.user
    if not user.requires_google_profile:
        return redirect("analytics:dashboard")
    form = GoogleProfileForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            updated = User.objects.filter(pk=user.pk, requires_google_profile=True).update(
                gender=form.cleaned_data["gender"], requires_google_profile=False,
            )
            if updated:
                profile = UserProfile.objects.get(user=user)
                profile.weekly_workout_goal = form.cleaned_data["weekly_workout_goal"]
                profile.save(update_fields=["weekly_workout_goal"])
                WeeklyWorkoutGoalHistory.objects.create(
                    user=user, goal_days=profile.weekly_workout_goal, effective_at=timezone.now(),
                )
        return redirect("analytics:dashboard")
    return render(request, "accounts/complete_google_profile.html", {"form": form})


@login_required
def profile(request):
    """UC-28/UC-29: Update profile information and fitness preferences."""
    profile = UserProfile.objects.get_or_create(user=request.user)[0]

    if request.method == "POST":
        user_form = UserForm(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, _("Profile updated."))
            return redirect("accounts:profile")
    else:
        user_form = UserForm(instance=request.user)
        profile_form = ProfileForm(instance=profile)

    return render(
        request,
        "accounts/profile.html",
        {"user_form": user_form, "profile_form": profile_form},
    )
