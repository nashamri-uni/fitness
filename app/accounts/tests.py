"""Tests for registration, login and profile (FREQ-1, FREQ-2, FREQ-13)."""
from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from .forms import ProfileForm
from .models import User, UserProfile, WeeklyWorkoutGoalHistory


class RegisterTests(TestCase):
    def test_register_creates_user_and_profile(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "first_name": "Test",
                "last_name": "User",
                "username": "testuser",
                "email": "test@example.com",
                "gender": "male",
                "weekly_workout_goal": "4",
                "password1": "s3cure-password",
                "password2": "s3cure-password",
            },
        )
        self.assertRedirects(response, reverse("analytics:dashboard"))

        user = User.objects.get(username="testuser")
        self.assertTrue(user.has_usable_password())
        self.assertNotEqual(user.password, "s3cure-password")  # stored hashed
        self.assertEqual(user.role, User.Role.USER)
        profile = UserProfile.objects.get(user=user)
        self.assertEqual(profile.weekly_workout_goal, 4)
        self.assertEqual(
            WeeklyWorkoutGoalHistory.objects.get(user=user).goal_days,
            4,
        )

    def test_registration_rejects_password_shorter_than_eight_characters(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "first_name": "Short",
                "last_name": "Password",
                "username": "shortpass",
                "email": "shortpass@example.com",
                "gender": "male",
                "password1": "Abc!234",
                "password2": "Abc!234",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("password1", response.context["form"].errors)
        self.assertFalse(User.objects.filter(username="shortpass").exists())

    def test_registration_rejects_numeric_password_that_is_eight_characters(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "first_name": "Numeric",
                "last_name": "Password",
                "username": "numericpass",
                "email": "numericpass@example.com",
                "gender": "male",
                "password1": "12345678",
                "password2": "12345678",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("password1", response.context["form"].errors)
        self.assertFalse(User.objects.filter(username="numericpass").exists())

    def test_registration_accepts_a_long_password(self):
        password = "Violet!930-LongSecurePassphrase"
        response = self.client.post(
            reverse("accounts:register"),
            {
                "first_name": "Long",
                "last_name": "Password",
                "username": "longpass",
                "email": "longpass@example.com",
                "gender": "female",
                "password1": password,
                "password2": password,
            },
        )

        self.assertRedirects(response, reverse("analytics:dashboard"))
        user = User.objects.get(username="longpass")
        self.assertTrue(user.check_password(password))

    def test_registration_rejects_goals_outside_one_to_seven_days(self):
        for goal in ("0", "8"):
            with self.subTest(goal=goal):
                response = self.client.post(
                    reverse("accounts:register"),
                    {
                        "first_name": "Test",
                        "last_name": "User",
                        "username": f"testuser{goal}",
                        "email": f"test{goal}@example.com",
                        "gender": "male",
                        "weekly_workout_goal": goal,
                        "password1": "s3cure-password",
                        "password2": "s3cure-password",
                    },
                )
                self.assertEqual(response.status_code, 200)
                self.assertFalse(User.objects.filter(username=f"testuser{goal}").exists())

    def test_mismatched_passwords_are_rejected(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "first_name": "Test",
                "last_name": "User",
                "username": "testuser",
                "email": "test@example.com",
                "gender": "male",
                "password1": "password-one",
                "password2": "password-two",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("password2", response.context["form"].errors)
        self.assertFalse(User.objects.exists())

    def test_duplicate_usernames_are_rejected(self):
        User.objects.create_user(username="existing", password="previous-password")
        response = self.client.post(
            reverse("accounts:register"),
            {
                "first_name": "New",
                "last_name": "User",
                "username": "existing",
                "email": "new@example.com",
                "gender": "male",
                "password1": "Strong!984-Workout",
                "password2": "Strong!984-Workout",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("username", response.context["form"].errors)
        self.assertEqual(User.objects.filter(username="existing").count(), 1)

    def test_login_and_logout(self):
        user = User.objects.create_user(username="bob", email="bob@example.com", password="pw12345678")
        self.assertTrue(self.client.login(username="bob", password="pw12345678"))

        response = self.client.get(reverse("analytics:dashboard"))
        self.assertEqual(response.status_code, 200)

        self.client.post(reverse("accounts:logout"))
        response = self.client.get(reverse("analytics:dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse("exercises:library"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_profile_update(self):
        user = User.objects.create_user(username="carol", email="carol@example.com", password="pw12345678")
        UserProfile.objects.create(user=user)
        self.client.login(username="carol", password="pw12345678")

        response = self.client.post(
            reverse("accounts:profile"),
            {
                "first_name": "Carol",
                "last_name": "B",
                "email": "carol@example.com",
                "gender": "female",
                "date_of_birth": "1998-04-12",
                "height_cm": "170",
                "weight_kg": "65",
                "fitness_goal": "strength",
                "weekly_workout_goal": "5",
            },
        )
        self.assertRedirects(response, reverse("accounts:profile"))
        profile = UserProfile.objects.get(user=user)
        self.assertEqual(profile.fitness_goal, "strength")
        self.assertEqual(profile.weight_kg, 65.0)
        self.assertEqual(profile.weekly_workout_goal, 5)
        self.assertEqual(
            WeeklyWorkoutGoalHistory.objects.get(user=user).goal_days,
            5,
        )

    def test_profile_form_rejects_goals_outside_one_to_seven_days(self):
        user = User.objects.create_user(username="dana", password="pw12345678")
        form = ProfileForm(
            data={"weekly_workout_goal": "8"},
            instance=UserProfile(user=user),
        )

        self.assertFalse(form.is_valid())


class LanguageTests(TestCase):
    """Language switching (English / Arabic) and RTL rendering."""

    def test_default_language_is_english(self):
        user = User.objects.create_user(username="dave", email="dave@example.com", password="pw12345678")
        self.client.login(username="dave", password="pw12345678")

        html = self.client.get(reverse("accounts:profile")).content.decode()
        self.assertIn('lang="en"', html)
        self.assertIn('dir="ltr"', html)

    def test_switching_to_arabic_renders_an_rtl_page(self):
        user = User.objects.create_user(username="salma", email="salma@example.com", password="pw12345678")
        self.client.login(username="salma", password="pw12345678")

        response = self.client.post(reverse("set_language"), {"language": "ar", "next": reverse("accounts:profile")})
        self.assertEqual(response.status_code, 302)

        html = self.client.get(reverse("accounts:profile")).content.decode()
        self.assertIn('lang="ar"', html)
        self.assertIn('dir="rtl"', html)
        self.assertIn("الملف الشخصي", html)
        self.assertIn("css/rtl.css", html)
        self.assertIn("الهدف الأسبوعي للتمرين (أيام)", html)
        self.assertIn('data-label-light="التبديل إلى الوضع الداكن"', html)
        self.assertIn('data-label-dark="التبديل إلى الوضع الفاتح"', html)
        register_response = self.client.get(reverse("accounts:register"))
        self.assertContains(register_response, "لم يتم تحديد هدف")

    def test_language_menu_uses_the_django_language_switch_form(self):
        """The globe menu submits the Django language-switch form."""
        user = User.objects.create_user(username="amina", email="amina@example.com", password="pw12345678")
        self.client.login(username="amina", password="pw12345678")

        html = self.client.get(reverse("accounts:profile")).content.decode()
        self.assertIn('class="inline-form language-switcher" data-auto-submit', html)
        self.assertIn('method="post" action="/i18n/setlang/"', html)
        self.assertIn('class="language-trigger"', html)
        self.assertIn('aria-haspopup="menu"', html)
        self.assertIn('class="language-menu" id="language-dropdown-menu" role="menu" hidden', html)
        self.assertIn('data-language="en"', html)
        self.assertIn('data-language="ar"', html)
        self.assertIn('role="menuitemradio"', html)
        self.assertIn('aria-checked="true"', html)
        self.assertIn('data-language-value disabled', html)
        self.assertIn('name="csrfmiddlewaretoken"', html)
        self.assertIn('name="language"', html)
        self.assertIn('value="en" selected', html)
        self.assertIn('value="ar"', html)

        app_js = (settings.BASE_DIR / "static" / "js" / "app.js").read_text(encoding="utf-8")
        self.assertIn("setupLanguageSwitcher", app_js)

    def test_switching_keeps_the_user_on_the_current_page(self):
        user = User.objects.create_user(username="reem", email="reem@example.com", password="pw12345678")
        self.client.login(username="reem", password="pw12345678")
        current_page = reverse("exercises:library")

        response = self.client.post(reverse("set_language"), {"language": "ar", "next": current_page})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], current_page)


class AuthPageTests(TestCase):
    def test_login_page_uses_django_post_authentication_and_return_target(self):
        user = User.objects.create_user(
            username="login-user",
            email="login@example.com",
            password="Secure!Passphrase2030",
        )
        response = self.client.get(reverse("accounts:login"))
        html = response.content.decode()
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertIn('name="next"', html)
        self.assertIn('name="username"', html)
        self.assertIn('name="password"', html)
        self.assertIn('data-password-toggle="id_password"', html)
        self.assertNotIn('class="nav"', html)
        self.assertIn('class="auth-page"', html)
        self.assertIn('id="theme-toggle"', html)
        self.assertIn('data-language-trigger', html)
        header = html.split("</header>", 1)[0]
        self.assertNotIn('href="{}"'.format(reverse("accounts:login")), header)
        self.assertNotIn('href="{}"'.format(reverse("accounts:register")), header)
        self.assertIn('href="{}"'.format(reverse("accounts:register")), html)

        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": user.username,
                "password": "Secure!Passphrase2030",
                "next": reverse("accounts:profile"),
            },
        )
        self.assertRedirects(response, reverse("accounts:profile"))

    def test_login_failure_does_not_disclose_whether_username_exists(self):
        User.objects.create_user(username="known-user", password="Secure!Passphrase2030")
        errors = []
        for username in ("known-user", "unknown-user"):
            response = self.client.post(
                reverse("accounts:login"),
                {"username": username, "password": "wrong-password"},
            )
            self.assertEqual(response.status_code, 200)
            errors.append(list(response.context["form"].non_field_errors()))

        self.assertEqual(errors[0], errors[1])

    def test_registration_page_renders_every_existing_field(self):
        response = self.client.get(reverse("accounts:register"))
        html = response.content.decode()
        for field_name in (
            "first_name",
            "last_name",
            "username",
            "email",
            "gender",
            "weekly_workout_goal",
            "password1",
            "password2",
        ):
            with self.subTest(field=field_name):
                self.assertIn(f'name="{field_name}"', html)
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertIn('data-password-toggle="id_password1"', html)
        self.assertIn('data-password-toggle="id_password2"', html)
        self.assertIn('data-password-rule="minimum-length"', html)
        self.assertIn('id="register-password-match"', html)
        self.assertIn("Create Account", html)
        header = html.split("</header>", 1)[0]
        self.assertNotIn('href="{}"'.format(reverse("accounts:login")), header)
        self.assertNotIn('href="{}"'.format(reverse("accounts:register")), header)
        self.assertIn('href="{}"'.format(reverse("accounts:login")), html)
