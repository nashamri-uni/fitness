"""Views for authentication and profile (UC-1, UC-2, UC-3, UC-28, UC-29)."""
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _

from .forms import ProfileForm, RegisterForm, UserForm
from .models import UserProfile


def register(request):
    """UC-1: Register new account."""
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, _("Account created successfully. You are now logged in."))
            return redirect("analytics:dashboard")
    else:
        form = RegisterForm()
    return render(request, "accounts/register.html", {"form": form})


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
