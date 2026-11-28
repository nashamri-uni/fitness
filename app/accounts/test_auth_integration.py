"""Password and Google authorization through FitPlanner's public endpoints."""
import time
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import jwt
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount, SocialToken
from allauth.socialaccount.providers.oauth2.client import OAuth2Error
from cryptography.hazmat.primitives.asymmetric import rsa
from django.contrib.auth import SESSION_KEY
from django.core import mail
from django.core.cache import cache
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.urls import reverse

from plans.models import WorkoutPlan

from .models import User, UserProfile

PASSWORD = "Distinctive!Strong-Routine-938"
SECOND_PASSWORD = "An-even!better-routine-257"
PROVIDER = {
    "google": {
        "APPS": [{"client_id": "unit-test-client", "secret": "unit-test-secret"}],
        "SCOPE": ["openid", "email", "profile"],
        "OAUTH_PKCE_ENABLED": True,
    },
}


class EmailAuthenticationTests(TestCase):
    def setUp(self):
        cache.clear()

    def register(self, **overrides):
        return self.client.post(reverse("accounts:register"), {
            "username": "new-lifter", "email": "New@Example.com", "gender": "female",
            "password1": PASSWORD, "password2": PASSWORD, **overrides,
        })

    def test_registration_normalizes_email_and_keeps_django_password(self):
        response = self.register()
        self.assertRedirects(response, reverse("analytics:dashboard"))
        user = User.objects.get(username="new-lifter")
        self.assertEqual(user.email, "new@example.com")
        self.assertTrue(user.check_password(PASSWORD))

    def test_registration_rejects_missing_invalid_and_duplicate_email(self):
        User.objects.create_user("existing", "taken@example.com")
        for email in ("", "not-an-address", "taken@example.com", "TAKEN@EXAMPLE.COM"):
            with self.subTest(email=email):
                response = self.register(email=email)
                self.assertIn("email", response.context["form"].errors)
        self.assertFalse(User.objects.filter(username="new-lifter").exists())

    def test_registration_validates_international_domains_consistently(self):
        self.assertRedirects(self.register(email="Lifter@bücher.example"), reverse("analytics:dashboard"))
        self.assertEqual(User.objects.get(username="new-lifter").email, "lifter@xn--bcher-kva.example")

    def test_email_uniqueness_is_enforced_by_the_database(self):
        user = User.objects.create_user("existing", "taken@example.com")
        with self.assertRaisesRegex(IntegrityError, "accounts_email_conflict"), transaction.atomic():
            User.objects.create_user("duplicate", "TAKEN@EXAMPLE.COM")
        other = User.objects.create_user("other", "free@example.com")
        with self.assertRaisesRegex(IntegrityError, "accounts_email_conflict"), transaction.atomic():
            User.objects.filter(pk=other.pk).update(email=user.email.upper())

    def test_username_and_case_insensitive_email_login(self):
        user = User.objects.create_user("existing", "lifter@example.com", PASSWORD)
        for identifier in (user.username, "lifter@example.com", "LIFTER@EXAMPLE.COM"):
            with self.subTest(identifier=identifier):
                client = Client()
                response = client.post(reverse("accounts:login"), {"username": identifier, "password": PASSWORD})
                self.assertRedirects(response, reverse("analytics:dashboard"))
                self.assertEqual(client.session[SESSION_KEY], str(user.pk))

    def test_inactive_unknown_bad_password_and_collision_get_same_error(self):
        User.objects.create_user("known", "known@example.com", PASSWORD)
        User.objects.create_user("inactive", "inactive@example.com", PASSWORD, is_active=False)
        User.objects.create_user("known@example.com", "other@example.com", PASSWORD)
        errors = []
        for identifier, password in (
            ("known", "wrong"), ("inactive", PASSWORD), ("missing", PASSWORD), ("known@example.com", PASSWORD),
        ):
            response = self.client.post(reverse("accounts:login"), {"username": identifier, "password": password})
            errors.append(response.context["form"].non_field_errors()[0])
            self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertEqual(len(set(errors)), 1)

    def test_blank_email_and_admin_username_remain_usable(self):
        old_user = User.objects.create_user("old-username", password=PASSWORD)
        staff = User.objects.create_superuser("staff", "staff@example.com", PASSWORD)
        self.assertRedirects(self.client.post(reverse("accounts:login"), {
            "username": old_user.username, "password": PASSWORD,
        }), reverse("analytics:dashboard"))
        admin_client = Client()
        response = admin_client.post(reverse("admin:login"), {"username": staff.username, "password": PASSWORD})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(admin_client.session[SESSION_KEY], str(staff.pk))

    @override_settings(ACCOUNT_RATE_LIMITS={"fitplanner_login": "2/m/key"})
    def test_login_rate_limits_repeated_attempts(self):
        User.objects.create_user("limited", "limited@example.com", PASSWORD)
        url = reverse("accounts:login")
        for _ in range(2):
            self.client.post(url, {"username": "limited@example.com", "password": "wrong"})
        response = self.client.post(url, {"username": "LIMITED@EXAMPLE.COM", "password": PASSWORD})
        self.assertEqual(response.context["form"].errors.as_data()["__all__"][0].code, "rate_limited")
        self.assertNotIn(SESSION_KEY, self.client.session)

    @override_settings(EMAIL_CHANGE_ENABLED=True, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_email_change_requires_proof_password_and_signed_confirmation(self):
        user = User.objects.create_user("lifter", "lifter@example.com", PASSWORD)
        other = User.objects.create_user("other", "other@example.com", PASSWORD)
        self.client.force_login(user)
        self.client.post(reverse("accounts:profile"), {"email": "bypass@example.com", "gender": "male"})
        self.client.post(reverse("accounts:change_email"), {"email": "new@example.com", "current_password": "wrong"})
        self.assertFalse(mail.outbox)
        self.client.post(reverse("accounts:change_email"), {"email": "New@example.com", "current_password": PASSWORD})
        self.assertEqual(mail.outbox[0].to, ["new@example.com"])
        confirmation = urlsplit(mail.outbox[0].body.split()[-1]).path
        self.assertEqual(self.client.get(confirmation).status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.email, "lifter@example.com")
        stranger = Client()
        stranger.force_login(other)
        self.assertRedirects(stranger.post(confirmation), reverse("accounts:security"))
        self.assertRedirects(self.client.post(confirmation), reverse("accounts:security"))
        user.refresh_from_db()
        self.assertEqual(user.email, "new@example.com")
        self.assertTrue(EmailAddress.objects.get(user=user, email=user.email).verified)


@override_settings(GOOGLE_AUTH_ENABLED=True, SOCIALACCOUNT_PROVIDERS=PROVIDER)
class GoogleAuthorizationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def setUp(self):
        cache.clear()

    def begin(self, path="google_login", **data):
        response = self.client.post(reverse(path), data)
        parsed = urlsplit(response.url)
        self.assertEqual(parsed.netloc, "accounts.google.com")
        query = parse_qs(parsed.query)
        self.assertEqual(query["redirect_uri"], ["http://testserver/accounts/google/login/callback/"])
        self.assertEqual(set(query["scope"][0].split()), {"openid", "email", "profile"})
        self.assertEqual(query["code_challenge_method"], ["S256"])
        return query["state"][0]

    def callback(self, state, **overrides):
        claims = {
            "iss": "https://accounts.google.com", "aud": "unit-test-client",
            "sub": "google-provider-subject", "email": "GOOGLE@example.com", "email_verified": True,
            "given_name": "Sam", "family_name": "Lifter", "exp": int(time.time()) + 300, **overrides,
        }
        signed = jwt.encode(claims, self.key, algorithm="RS256", headers={"kid": "test-key"})
        with (
            patch("allauth.socialaccount.providers.oauth2.client.OAuth2Client.get_access_token",
                  return_value={"access_token": "mock-token", "id_token": signed}),
            patch("allauth.socialaccount.internal.jwtkit.fetch_key",
                  return_value=("RS256", self.key.public_key())),
        ):
            return self.client.get(reverse("google_callback"), {"code": "mock-code", "state": state})

    def test_google_creates_profile_and_logs_in_by_stable_subject(self):
        response = self.callback(self.begin(next="https://external.invalid/"))
        self.assertRedirects(response, reverse("analytics:dashboard"), fetch_redirect_response=False)
        user = User.objects.get(email="google@example.com")
        self.assertTrue(user.username)
        self.assertEqual((user.first_name, user.last_name, user.gender), ("Sam", "Lifter", ""))
        self.assertFalse(user.has_usable_password())
        self.assertTrue(UserProfile.objects.filter(user=user).exists())
        self.assertTrue(EmailAddress.objects.get(user=user, email=user.email).verified)
        self.assertFalse(SocialToken.objects.exists())
        self.assertRedirects(self.client.get(reverse("analytics:dashboard")), reverse("accounts:complete_google_profile"))
        self.assertRedirects(self.client.post(reverse("accounts:complete_google_profile"), {
            "gender": "female", "weekly_workout_goal": "5",
        }), reverse("analytics:dashboard"))
        self.assertEqual(UserProfile.objects.get(user=user).weekly_workout_goal, 5)
        self.client.logout()
        self.assertEqual(self.callback(self.begin(), email="changed-at-google@example.com").status_code, 302)
        self.assertEqual(self.client.session[SESSION_KEY], str(user.pk))
        self.assertEqual(User.objects.count(), 1)

    def test_provider_email_and_audience_must_be_valid(self):
        for claims in ({"email_verified": False}, {"email": None}, {"aud": "wrong"}, {"exp": 1}, {"sub": ""}):
            with self.subTest(claims=claims):
                self.assertRedirects(self.callback(self.begin(), **claims), reverse("accounts:login"))
        self.assertFalse(User.objects.exists())

    def test_verified_email_never_links_an_existing_local_account_automatically(self):
        user = User.objects.create_user("existing", "google@example.com", PASSWORD)
        plan = WorkoutPlan.objects.create(user=user, name="Original workout")
        self.assertRedirects(self.callback(self.begin()), reverse("accounts:login"))
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertFalse(SocialAccount.objects.exists())
        self.assertEqual(WorkoutPlan.objects.get(pk=plan.pk).user_id, user.pk)

        self.client.force_login(user)
        security = reverse("accounts:security")
        self.assertEqual(self.client.post(security, {"action": "connect", "current_password": "wrong"}).status_code, 200)
        self.assertRedirects(self.callback(self.begin("accounts:security", action="connect", current_password=PASSWORD)),
                             security)
        self.assertEqual(SocialAccount.objects.get().user_id, user.pk)
        self.assertEqual(WorkoutPlan.objects.get(pk=plan.pk).user_id, user.pk)
        self.assertEqual(User.objects.count(), 1)

    def test_google_identity_cannot_be_connected_to_another_user(self):
        original = User.objects.create_user("original", "original@example.com", PASSWORD)
        other = User.objects.create_user("other", "other@example.com", PASSWORD)
        SocialAccount.objects.create(user=original, provider="google", uid="google-provider-subject")
        self.client.force_login(other)
        state = self.begin("accounts:security", action="connect", current_password=PASSWORD)
        self.assertRedirects(self.callback(state), reverse("accounts:security"))
        self.assertEqual(SocialAccount.objects.get().user_id, original.pk)
        self.assertEqual(self.client.session[SESSION_KEY], str(other.pk))

    def test_google_only_user_must_set_a_password_before_disconnect(self):
        self.callback(self.begin())
        self.client.post(reverse("accounts:complete_google_profile"), {"gender": "male"})
        security = reverse("accounts:security")
        self.client.post(security, {"action": "disconnect"})
        self.assertTrue(SocialAccount.objects.exists())
        self.assertRedirects(self.client.post(reverse("accounts:password"), {
            "new_password1": SECOND_PASSWORD, "new_password2": SECOND_PASSWORD,
        }), security)
        self.assertRedirects(self.client.post(security, {"action": "disconnect", "current_password": SECOND_PASSWORD}),
                             security)
        self.assertFalse(SocialAccount.objects.exists())
        self.assertTrue(User.objects.get().check_password(SECOND_PASSWORD))

    def test_unrelated_session_and_cancelled_oauth_cannot_authenticate(self):
        state = self.begin()
        other_client = Client()
        self.assertRedirects(
            other_client.get(reverse("google_callback"), {"code": "mock-code", "state": state}),
            reverse("accounts:login"),
        )
        result = self.client.get(reverse("google_callback"), {"error": "access_denied", "state": state})
        self.assertRedirects(result, reverse("accounts:login"))
        self.assertRedirects(self.callback(state), reverse("accounts:login"))
        self.assertFalse(User.objects.exists())

    def test_expired_state_and_provider_exchange_failure_are_safe(self):
        state = self.begin()
        session = self.client.session
        stored = session["socialaccount_states"]
        value, _, provider = stored[state]
        stored[state] = (value, time.time() - 601, provider)
        session["socialaccount_states"] = stored
        session.save()
        self.assertRedirects(self.callback(state), reverse("accounts:login"))

        state = self.begin()
        with patch("allauth.socialaccount.providers.oauth2.client.OAuth2Client.get_access_token",
                   side_effect=OAuth2Error("provider unavailable")):
            response = self.client.get(reverse("google_callback"), {"state": state, "code": "mock-code"})
        self.assertRedirects(response, reverse("accounts:login"))
        self.assertFalse(User.objects.exists())

    def test_oauth_start_is_post_only_and_csrf_protected(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.get(reverse("google_login")).status_code, 405)
        self.assertEqual(client.post(reverse("google_login")).status_code, 403)

    @override_settings(GOOGLE_AUTH_ENABLED=False)
    def test_unconfigured_google_keeps_password_login_available(self):
        self.assertNotContains(self.client.get(reverse("accounts:login")), 'class="auth-google-button"')
        self.assertRedirects(self.client.post(reverse("google_login")), reverse("accounts:login"))
        user = User.objects.create_user("local", "local@example.com", PASSWORD)
        self.assertRedirects(self.client.post(reverse("accounts:login"), {
            "username": user.email, "password": PASSWORD,
        }), reverse("analytics:dashboard"))


class LegacyEmailMigrationTests(TransactionTestCase):
    def test_migration_preserves_duplicate_email_users_and_reserves_the_address(self):
        executor = MigrationExecutor(connection)
        before = [("accounts", "0002_weeklyworkoutgoalhistory_and_more")]
        after = [("accounts", "0003_authentication_identity")]
        executor.migrate(before)
        try:
            old_user = executor.loader.project_state(before).apps.get_model("accounts", "User")
            legacy = [
                old_user.objects.create(username="legacy-one", email="legacy@example.com"),
                old_user.objects.create(username="legacy-two", email="LEGACY@example.com"),
            ]
        finally:
            MigrationExecutor(connection).migrate(after)

        self.assertEqual([User.objects.get(pk=user.pk).email for user in legacy], [user.email for user in legacy])
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user("new-duplicate", "Legacy@example.com")
        for user in legacy:
            current = User.objects.get(pk=user.pk)
            current.set_password(PASSWORD)
            current.save(update_fields=["password"])
            self.assertEqual(self.client.post(reverse("accounts:login"), {
                "username": user.username, "password": PASSWORD,
            }).status_code, 302)
            self.client.logout()
        response = self.client.post(reverse("accounts:login"), {"username": "legacy@example.com", "password": PASSWORD})
        self.assertEqual(response.context["form"].errors.as_data()["__all__"][0].code, "invalid_login")
