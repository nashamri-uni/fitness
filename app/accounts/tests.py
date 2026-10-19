"""Tests for registration, login and profile (FREQ-1, FREQ-2, FREQ-13)."""
from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from .models import User, UserProfile


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
                "password1": "s3cure-password",
                "password2": "s3cure-password",
            },
        )
        self.assertRedirects(response, reverse("analytics:dashboard"))

        user = User.objects.get(username="testuser")
        self.assertTrue(user.has_usable_password())
        self.assertNotEqual(user.password, "s3cure-password")  # stored hashed
        self.assertEqual(user.role, User.Role.USER)
        self.assertTrue(UserProfile.objects.filter(user=user).exists())

    def test_mismatched_passwords_are_rejected(self):
        self.client.post(
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
        self.assertFalse(User.objects.exists())

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
            },
        )
        self.assertRedirects(response, reverse("accounts:profile"))
        profile = UserProfile.objects.get(user=user)
        self.assertEqual(profile.fitness_goal, "strength")
        self.assertEqual(profile.weight_kg, 65.0)


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

    def test_language_dropdown_is_an_auto_submit_form(self):
        """Issue #1: the dropdown applies the language itself, no Switch click."""
        user = User.objects.create_user(username="amina", email="amina@example.com", password="pw12345678")
        self.client.login(username="amina", password="pw12345678")

        html = self.client.get(reverse("accounts:profile")).content.decode()
        self.assertIn('class="inline-form language-switcher" data-auto-submit', html)
        self.assertIn('name="language"', html)

        app_js = (settings.BASE_DIR / "static" / "js" / "app.js").read_text(encoding="utf-8")
        self.assertIn("setupLanguageSwitcher", app_js)

    def test_switching_keeps_the_user_on_the_current_page(self):
        user = User.objects.create_user(username="reem", email="reem@example.com", password="pw12345678")
        self.client.login(username="reem", password="pw12345678")
        current_page = reverse("exercises:library")

        response = self.client.post(reverse("set_language"), {"language": "ar", "next": current_page})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], current_page)
