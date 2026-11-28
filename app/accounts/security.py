"""Authenticated account recovery, email verification and Google connections."""
from smtplib import SMTPException

from allauth.account.models import EmailAddress
from allauth.core import ratelimit
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.crypto import constant_time_compare, salted_hmac
from django.utils.translation import gettext as _
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods, require_POST

from .forms import EmailChangeForm, PasswordConfirmationForm, available_email
from .google import google_accounts, start_google, was_recently_authenticated_by_google
from .models import User

EMAIL_CHANGE_SALT = "accounts.verified_email_change"
EMAIL_CHANGE_MAX_AGE = 900


@login_required
@require_http_methods(["GET", "POST"])
@sensitive_post_parameters("current_password")
def security(request):
    connected = google_accounts(request.user).exists()
    can_change_email = settings.EMAIL_CHANGE_ENABLED and request.user.has_usable_password()
    can_connect = settings.GOOGLE_AUTH_ENABLED and not connected and request.user.has_usable_password()
    form = PasswordConfirmationForm(request, request.POST if request.method == "POST" else None)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "connect" and can_connect and form.is_valid():
            return start_google(request, purpose="connect", next_url=reverse("accounts:security"))
        if action == "disconnect" and connected:
            if not request.user.has_usable_password():
                messages.error(request, _("Set a password before disconnecting Google."))
                return redirect("accounts:security")
            if form.is_valid():
                google_accounts(request.user).delete()
                messages.success(request, _("Google account disconnected."))
                return redirect("accounts:security")
    return render(request, "accounts/security.html", {
        "connected": connected, "can_connect": can_connect, "form": form,
        "can_change_email": can_change_email, "email_change_enabled": settings.EMAIL_CHANGE_ENABLED,
    })


@login_required
@require_POST
def reauthenticate_google(request):
    if not google_accounts(request.user).exists():
        return redirect("accounts:security")
    return start_google(request, purpose="reauthenticate", next_url=reverse("accounts:password"))


@login_required
@require_http_methods(["GET", "POST"])
@sensitive_post_parameters("old_password", "new_password1", "new_password2")
def change_password(request):
    user = request.user
    already_has_password = user.has_usable_password()
    if not already_has_password and not was_recently_authenticated_by_google(request):
        return render(request, "accounts/security_form.html", {"needs_google_reauthentication": True})
    form_class = PasswordChangeForm if already_has_password else SetPasswordForm
    form = form_class(user, request.POST if request.method == "POST" else None)
    if request.method == "POST":
        if not ratelimit.consume(request, action="fitplanner_reauthenticate", key=str(user.pk)):
            messages.error(request, _("Too many attempts. Try again later."))
            return redirect("accounts:security")
        if form.is_valid():
            previous_password = user.password
            form.save(commit=False)
            if User.objects.filter(pk=user.pk, password=previous_password).update(password=user.password):
                update_session_auth_hash(request, user)
                messages.success(request, _("Password saved."))
            return redirect("accounts:security")
    return render(request, "accounts/security_form.html", {"form": form, "heading": _("Set or change password")})


def email_change_binding(user):
    return salted_hmac(EMAIL_CHANGE_SALT, f"{user.pk}:{user.email}:{user.password}").hexdigest()


@login_required
@require_http_methods(["GET", "POST"])
@sensitive_post_parameters("current_password")
def change_email(request):
    if not settings.EMAIL_CHANGE_ENABLED or not request.user.has_usable_password():
        return redirect("accounts:security")
    form = EmailChangeForm(request, request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        user = request.user
        if not ratelimit.consume(request, action="fitplanner_email_change", key=str(user.pk)):
            messages.error(request, _("Too many attempts. Try again later."))
            return redirect("accounts:security")
        email = form.cleaned_data["email"]
        token = signing.dumps({"user": user.pk, "email": email, "binding": email_change_binding(user)},
                              salt=EMAIL_CHANGE_SALT)
        url = request.build_absolute_uri(reverse("accounts:confirm_email", args=[token]))
        try:
            send_mail(
                _("Confirm your FitPlanner email change"),
                _("Open this link within 15 minutes to confirm your email change: %(url)s") % {"url": url},
                None, [email],
            )
        except (OSError, SMTPException):
            messages.error(request, _("The confirmation email could not be sent. Try again later."))
        else:
            messages.success(request, _("Check your new email address for a confirmation link."))
        return redirect("accounts:security")
    return render(request, "accounts/security_form.html", {"form": form, "heading": _("Change email address")})


@login_required
@require_http_methods(["GET", "POST"])
def confirm_email(request, token):
    user = request.user
    try:
        change = signing.loads(token, salt=EMAIL_CHANGE_SALT, max_age=EMAIL_CHANGE_MAX_AGE)
        if change["user"] != user.pk or not constant_time_compare(change["binding"], email_change_binding(user)):
            raise signing.BadSignature()
    except signing.BadSignature:
        messages.error(request, _("This email confirmation link is invalid or has expired."))
        return redirect("accounts:security")
    if request.method == "POST":
        try:
            with transaction.atomic():
                email = available_email(change["email"], user)
                updated = User.objects.filter(pk=user.pk, email=user.email, password=user.password).update(email=email)
                if updated:
                    EmailAddress.objects.filter(user=user).delete()
                    EmailAddress.objects.create(user=user, email=email, verified=True, primary=True)
        except (ValidationError, IntegrityError):
            messages.error(request, _("This email address is already in use."))
        else:
            if updated:
                messages.success(request, _("Your email address has been verified and updated."))
        return redirect("accounts:security")
    response = render(request, "accounts/security_form.html", {
        "confirm_address": change["email"], "heading": _("Confirm email change"),
    })
    response["Referrer-Policy"] = "no-referrer"
    response["Cache-Control"] = "no-store"
    return response
