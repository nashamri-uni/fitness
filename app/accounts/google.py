"""Google OpenID Connect through django-allauth."""
from datetime import timedelta
import time

from allauth.account.authentication import get_authentication_records
from allauth.core import ratelimit
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter, get_adapter
from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.providers.base import AuthError, AuthProcess
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter, _verify_and_decode
from allauth.socialaccount.providers.oauth2.client import OAuth2Error
from allauth.socialaccount.providers.oauth2.views import OAuth2CallbackView
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_POST

from .emails import normalize_email
from .forms import available_email
from .models import User, UserProfile

GOOGLE_PROVIDER = "google"
REAUTHENTICATION_AGE = timedelta(minutes=5).total_seconds()


def google_accounts(user):
    return SocialAccount.objects.filter(provider=GOOGLE_PROVIDER, user=user)


def was_recently_authenticated_by_google(request):
    now = time.time()
    identities = set(google_accounts(request.user).values_list("uid", flat=True))
    return any(
        record.get("method") == "socialaccount" and record.get("provider") == GOOGLE_PROVIDER
        and record.get("uid") in identities and 0 <= now - record["at"] <= REAUTHENTICATION_AGE
        for record in get_authentication_records(request, request.user)
    )


def return_to_account(request, message):
    messages.error(request, message)
    return redirect("accounts:security" if request.user.is_authenticated else "accounts:login")


def start_google(request, *, purpose="login", next_url=None):
    if not settings.GOOGLE_AUTH_ENABLED:
        return return_to_account(request, _("Google sign-in is not configured."))
    if not ratelimit.consume(request, action="fitplanner_google"):
        return return_to_account(request, _("Too many attempts. Try again later."))
    provider = get_adapter(request).get_provider(request, GOOGLE_PROVIDER)
    return provider.redirect(
        request,
        AuthProcess.CONNECT if purpose == "connect" else AuthProcess.LOGIN,
        next_url=next_url,
        data={"purpose": purpose, "user_id": request.user.pk},
        auth_params={"access_type": "online", "prompt": "select_account"} if purpose == "reauthenticate" else None,
    )


@require_POST
def google_login(request):
    if request.user.is_authenticated:
        return redirect("accounts:security")
    next_url = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(next_url, {request.get_host()}, require_https=request.is_secure()):
        next_url = reverse(settings.LOGIN_REDIRECT_URL)
    return start_google(request, next_url=next_url)


class VerifiedGoogleOAuth2Adapter(GoogleOAuth2Adapter):
    def parse_token(self, data):
        if not data.get("id_token"):
            raise OAuth2Error("Missing Google identity token")
        try:
            return super().parse_token(data)
        except (KeyError, ValueError, TypeError) as error:
            raise OAuth2Error("Invalid Google token response") from error

    def _decode_id_token(self, app, id_token):
        try:
            claims = _verify_and_decode(app, id_token, verify_signature=True)
        except (KeyError, TypeError, ValueError) as error:
            raise OAuth2Error("Invalid Google identity token") from error
        if (
            not isinstance(claims.get("sub"), str) or not claims["sub"].strip()
            or not isinstance(claims.get("exp"), (int, float))
        ):
            raise OAuth2Error("Incomplete Google identity token")
        return claims

    def complete_login(self, request, app, token, **kwargs):
        sociallogin = super().complete_login(request, app, token, **kwargs)
        if request.user.is_authenticated and SocialAccount.objects.filter(
            provider=GOOGLE_PROVIDER, uid=sociallogin.account.uid,
        ).exclude(user=request.user).exists():
            raise OAuth2Error("Google identity belongs to a different local account")
        sociallogin.account.extra_data = {"email": sociallogin.user.email}
        return sociallogin


_google_callback = OAuth2CallbackView.adapter_view(VerifiedGoogleOAuth2Adapter)


@require_GET
def google_callback(request):
    if not settings.GOOGLE_AUTH_ENABLED:
        return return_to_account(request, _("Google sign-in is not configured."))
    try:
        return _google_callback(request)
    except IntegrityError:
        return return_to_account(request, _("That Google account could not be linked or registered. Try again."))


class GoogleAccountAdapter(DefaultSocialAccountAdapter):
    def authenticate_by_email(self, sociallogin):
        # Provider email is useful for signup validation, never local authentication.
        return None

    def on_authentication_error(self, request, provider, error=None, exception=None, extra_context=None):
        message = (
            _("Google sign-in was cancelled.") if error == AuthError.CANCELLED
            else _("Google sign-in could not be completed. Start again and try another sign-in method if needed.")
        )
        raise ImmediateHttpResponse(return_to_account(request, message))

    def pre_social_login(self, request, sociallogin):
        data = sociallogin.state.get("data") or {}
        purpose = data.get("purpose")
        user = request.user
        known = sociallogin.is_existing
        if request.user.pk != data.get("user_id") or purpose not in {"login", "connect", "reauthenticate"}:
            self.reject(request, _("Your Google sign-in session has expired. Start again."))
        if known and not sociallogin.user.is_active:
            self.reject(request, _("Google sign-in could not be completed. Start again and try another sign-in method if needed."))
        if purpose == "reauthenticate" and (not known or sociallogin.user.pk != user.pk):
            self.reject(request, _("Choose the Google account connected to this FitPlanner account."))
        try:
            email_record = next(record for record in sociallogin.email_addresses if record.verified)
            email = normalize_email(email_record.email)
        except (StopIteration, ValidationError):
            self.reject(request, _("Google must provide a verified email address to continue."))
        if purpose == "connect":
            self.connect_account(request, sociallogin, email)
            raise ImmediateHttpResponse(redirect("accounts:security"))
        if not known:
            try:
                available_email(email)
            except ValidationError:
                self.reject(request, _("Sign in to your existing FitPlanner account, then connect Google in account security."))
            email_record.email = email
            sociallogin.email_addresses = [email_record]
            sociallogin.user.email = email
            sociallogin.account.extra_data = {"email": email}

    @transaction.atomic
    def connect_account(self, request, sociallogin, email):
        user_id = request.user.pk
        # Serialize concurrent requests before checking connections on SQLite.
        locked = User.objects.filter(pk=user_id, is_active=True, password=request.user.password)
        if not locked.update(last_login=F("last_login")):
            self.reject(request, _("Your Google sign-in session has expired. Start again."))
        user = locked.get()
        account = SocialAccount.objects.filter(provider=GOOGLE_PROVIDER, uid=sociallogin.account.uid).first()
        if (account and account.user_id != user.pk
                or google_accounts(user).exclude(uid=sociallogin.account.uid).exists()):
            self.reject(request, _("That Google account cannot be connected to this FitPlanner account."))
        if account is None:
            try:
                available_email(email, user)
            except ValidationError:
                self.reject(request, _("That Google account cannot be connected to this FitPlanner account."))
            sociallogin.connect(request, user)
        messages.success(request, _("Google account connected."))

    @transaction.atomic
    def save_user(self, request, sociallogin, form=None):
        sociallogin.user.gender = ""
        sociallogin.user.requires_google_profile = True
        user = super().save_user(request, sociallogin, form=form)
        UserProfile.objects.create(user=user)
        return user

    @staticmethod
    def reject(request, message):
        raise ImmediateHttpResponse(return_to_account(request, message))
