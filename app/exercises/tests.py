"""Tests for the exercise library (FREQ-3, FREQ-14, FREQ-15)."""
from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .models import Equipment, Exercise, ExerciseEquipment, ExerciseMuscleGroup, MuscleGroup


class LibraryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="user1", email="u1@example.com", password="pw12345678")
        self.client.login(username="user1", password="pw12345678")

        self.chest = MuscleGroup.objects.create(name="Chest", body_region="upper")
        self.back = MuscleGroup.objects.create(name="Back", body_region="upper")
        self.barbell = Equipment.objects.create(name="Barbell")
        self.bench = Equipment.objects.create(name="Bench")

        self.bench_press = Exercise.objects.create(
            name="Barbell Bench Press", exercise_type="strength", difficulty="intermediate",
            created_by=self.user,
        )
        ExerciseMuscleGroup.objects.create(exercise=self.bench_press, muscle_group=self.chest, role="primary")
        ExerciseEquipment.objects.create(exercise=self.bench_press, equipment=self.barbell)

        self.pull_up = Exercise.objects.create(name="Pull-up", exercise_type="strength", difficulty="intermediate")
        ExerciseMuscleGroup.objects.create(exercise=self.pull_up, muscle_group=self.back, role="primary")

        self.inactive = Exercise.objects.create(name="Old Exercise", is_active=False)

    def test_library_lists_active_exercises(self):
        response = self.client.get(reverse("exercises:library"))
        names = [exercise.name for exercise in response.context["page_obj"]]
        self.assertIn("Barbell Bench Press", names)
        self.assertIn("Pull-up", names)
        self.assertNotIn("Old Exercise", names)

    def test_filter_by_muscle_group(self):
        response = self.client.get(reverse("exercises:library"), {"muscle_group": self.chest.pk})
        names = [exercise.name for exercise in response.context["page_obj"]]
        self.assertEqual(names, ["Barbell Bench Press"])

    def test_filter_by_equipment(self):
        response = self.client.get(reverse("exercises:library"), {"equipment": self.bench.pk})
        self.assertEqual(len(response.context["page_obj"]), 0)

    def test_search(self):
        response = self.client.get(reverse("exercises:library"), {"q": "pull"})
        names = [exercise.name for exercise in response.context["page_obj"]]
        self.assertEqual(names, ["Pull-up"])

    def test_exercise_detail(self):
        response = self.client.get(reverse("exercises:detail", args=[self.bench_press.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Barbell Bench Press")

    def test_admin_only_management(self):
        response = self.client.get(reverse("exercises:manage"))
        self.assertEqual(response.status_code, 302)

        admin = User.objects.create_user(username="admin1", email="a@example.com", password="pw12345678", role="admin")
        self.client.login(username="admin1", password="pw12345678")
        response = self.client.get(reverse("exercises:manage"))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_create_exercise_with_links(self):
        admin = User.objects.create_user(username="admin2", email="a2@example.com", password="pw12345678", role="admin")
        self.client.login(username="admin2", password="pw12345678")

        response = self.client.post(
            reverse("exercises:create"),
            {
                "name": "New Exercise",
                "description": "Test",
                "instructions": "Do it.",
                "difficulty": "beginner",
                "exercise_type": "strength",
                "image": "",
                "video_url": "",
                "is_active": "on",
                "muscle_groups": [self.chest.pk],
                "equipment": [self.barbell.pk],
            },
        )
        self.assertRedirects(response, reverse("exercises:manage"))
        exercise = Exercise.objects.get(name="New Exercise")
        self.assertEqual(exercise.created_by, admin)
        self.assertEqual(exercise.muscle_links.count(), 1)
        self.assertEqual(exercise.equipment_links.count(), 1)

    def test_editing_an_exercise_removes_unselected_links(self):
        admin = User.objects.create_user(username="admin3", email="a3@example.com", password="pw12345678", role="admin")
        self.client.login(username="admin3", password="pw12345678")

        # bench_press starts out linked to chest + barbell (see setUp).
        response = self.client.post(
            reverse("exercises:edit", args=[self.bench_press.pk]),
            {
                "name": "Barbell Bench Press",
                "description": "",
                "instructions": "",
                "difficulty": "intermediate",
                "exercise_type": "strength",
                "image": "",
                "video_url": "",
                "is_active": "on",
                "muscle_groups": [self.back.pk],
                "equipment": [],
            },
        )
        self.assertRedirects(response, reverse("exercises:manage"))
        self.bench_press.refresh_from_db()
        self.assertEqual(
            list(self.bench_press.muscle_links.values_list("muscle_group_id", flat=True)),
            [self.back.pk],
        )
        self.assertEqual(self.bench_press.equipment_links.count(), 0)

    def test_arabic_names_are_used_when_arabic_is_active(self):
        self.chest.name_ar = "الصدر"
        self.barbell.name_ar = "البار"
        self.bench_press.name_ar = "ضغط البار على المقعد"
        self.chest.save()
        self.barbell.save()
        self.bench_press.save()

        self.client.post(reverse("set_language"), {"language": "ar", "next": "/"})
        response = self.client.get(reverse("exercises:library"))
        self.assertContains(response, "ضغط البار على المقعد")
        self.assertContains(response, "الصدر")
        self.assertContains(response, "البار")

        self.client.post(reverse("set_language"), {"language": "en", "next": "/"})
        response = self.client.get(reverse("exercises:library"))
        self.assertContains(response, "Barbell Bench Press")
        self.assertContains(response, "Chest")
