"""Tests for workout plans (FREQ-4 to FREQ-7)."""
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from exercises.models import Exercise, ExerciseMuscleGroup, MuscleGroup
from exercises.management.commands.seed_data import EXERCISE_IMAGES

from .models import PlanExercise, PlanSet, WorkoutPlan


class PlanTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="planowner", email="p@example.com", password="pw12345678")
        self.other = User.objects.create_user(username="other", email="o@example.com", password="pw12345678")
        self.client.login(username="planowner", password="pw12345678")
        self.exercise = Exercise.objects.create(
            name="Push-up",
            exercise_type="strength",
            difficulty="beginner",
            image=EXERCISE_IMAGES["Push-up"],
        )

    def create_plan(self):
        return WorkoutPlan.objects.create(user=self.user, name="Push Day", goal="hypertrophy")

    def test_create_plan(self):
        response = self.client.post(
            reverse("plans:create"),
            {"name": "Push Day", "description": "", "goal": "hypertrophy", "estimated_duration_minutes": 40},
        )
        plan = WorkoutPlan.objects.get(name="Push Day")
        self.assertRedirects(response, reverse("plans:detail", args=[plan.pk]))
        self.assertEqual(plan.user, self.user)

    def test_add_exercise_to_plan(self):
        plan = self.create_plan()
        response = self.client.post(
            reverse("plans:detail", args=[plan.pk]),
            {"exercise": self.exercise.pk, "order": 3, "rest_seconds": 120},
        )
        self.assertRedirects(response, reverse("plans:detail", args=[plan.pk]))
        entry = PlanExercise.objects.get(plan=plan)
        self.assertEqual(entry.exercise, self.exercise)
        self.assertEqual(entry.order, 3)
        self.assertEqual(entry.rest_seconds, 120)

    def test_exercise_browser_groups_by_primary_muscle_and_cardio_type(self):
        plan = self.create_plan()
        chest = MuscleGroup.objects.create(name="Chest", body_region="upper")
        core = MuscleGroup.objects.create(name="Core", body_region="core")
        legs = MuscleGroup.objects.create(name="Quadriceps", body_region="lower")
        ExerciseMuscleGroup.objects.create(exercise=self.exercise, muscle_group=chest, role="primary")
        ExerciseMuscleGroup.objects.create(exercise=self.exercise, muscle_group=core, role="secondary")

        cardio = Exercise.objects.create(name="Treadmill", exercise_type="cardio")
        ExerciseMuscleGroup.objects.create(exercise=cardio, muscle_group=legs, role="primary")
        lower_exercise = Exercise.objects.create(name="Squat")
        ExerciseMuscleGroup.objects.create(exercise=lower_exercise, muscle_group=legs, role="primary")
        core_primary = Exercise.objects.create(name="Plank")
        ExerciseMuscleGroup.objects.create(exercise=core_primary, muscle_group=core, role="primary")
        unlinked = Exercise.objects.create(name="Unmapped Exercise")

        response = self.client.get(reverse("plans:detail", args=[plan.pk]))
        categories = {
            str(category["name"]): category
            for category in response.context["exercise_categories"]
        }

        self.assertEqual(
            [exercise.name for exercise in categories["Upper body"]["groups"][0]["exercises"]],
            ["Push-up"],
        )
        self.assertEqual(categories["Upper body"]["groups"][0]["name"], "Chest")
        self.assertNotIn("Core", categories)
        self.assertEqual(
            [exercise.name for exercise in categories["Lower body"]["groups"][0]["exercises"]],
            ["Squat"],
        )
        self.assertEqual([exercise.name for exercise in categories["Cardio"]["exercises"]], ["Treadmill"])
        self.assertEqual(categories["Cardio"]["groups"], [])
        other = categories["Free Exercises"]
        self.assertEqual(
            [exercise.name for exercise in other["exercises"]],
            ["Plank", "Unmapped Exercise"],
        )
        self.assertEqual(other["groups"], [])
        self.assertContains(response, 'id="id_exercise_%s"' % core_primary.pk)
        self.assertContains(response, 'id="id_exercise_%s"' % unlinked.pk)
        self.assertContains(response, f'src="{self.exercise.local_thumbnail_url}"')
        self.assertContains(response, 'class="exercise-thumbnail exercise-thumbnail--picker"')

    def test_selected_plan_exercise_uses_a_static_thumbnail(self):
        plan = self.create_plan()
        PlanExercise.objects.create(plan=plan, exercise=self.exercise, order=1)

        response = self.client.get(reverse("plans:detail", args=[plan.pk]))

        self.assertContains(response, f'src="{self.exercise.local_thumbnail_url}"')
        self.assertContains(response, 'class="exercise-thumbnail exercise-thumbnail--selected"')
        self.assertNotContains(response, f'src="{self.exercise.local_image_url}"')

    def test_already_added_exercise_is_not_offered_again(self):
        plan = self.create_plan()
        PlanExercise.objects.create(plan=plan, exercise=self.exercise, order=4, rest_seconds=45)

        response = self.client.get(reverse("plans:detail", args=[plan.pk]))

        self.assertNotContains(response, 'id="id_exercise_%s"' % self.exercise.pk)
        self.assertContains(response, "No exercises are available to add.")
        self.assertContains(response, "name=\"order\"")
        self.assertContains(response, "name=\"rest_seconds\"")
        self.assertContains(response, "disabled")

    def test_invalid_duplicate_submission_keeps_form_validation(self):
        plan = self.create_plan()
        PlanExercise.objects.create(plan=plan, exercise=self.exercise)

        response = self.client.post(
            reverse("plans:detail", args=[plan.pk]),
            {"exercise": self.exercise.pk, "order": 2, "rest_seconds": 30},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(PlanExercise.objects.filter(plan=plan).count(), 1)
        self.assertContains(response, "Select a valid choice")

    def test_exercise_browser_renders_arabic_category_and_muscle_names(self):
        plan = self.create_plan()
        chest = MuscleGroup.objects.create(name="Chest", name_ar="الصدر", body_region="upper")
        self.exercise.name_ar = "تمرين الضغط"
        self.exercise.save()
        ExerciseMuscleGroup.objects.create(exercise=self.exercise, muscle_group=chest, role="primary")

        self.client.post(reverse("set_language"), {"language": "ar", "next": "/"})
        response = self.client.get(reverse("plans:detail", args=[plan.pk]))

        self.assertContains(response, "الجزء العلوي")
        self.assertContains(response, "الصدر")
        self.assertContains(response, "تمرين الضغط")
        self.assertContains(response, "<legend id=\"exercise-field-label\">التمرين</legend>")
        self.assertContains(response, '<label for="id_order">الترتيب</label>')
        self.assertContains(response, '<label for="id_rest_seconds">ثوانٍ الراحة</label>')
        self.assertContains(response, 'dir="rtl"')

    def test_add_set_to_plan_exercise(self):
        plan = self.create_plan()
        entry = PlanExercise.objects.create(plan=plan, exercise=self.exercise, order=1)
        self.client.post(
            reverse("plans:add_set", args=[entry.pk]),
            {"set_number": 1, "reps": 12, "duration_seconds": 0, "weight_kg": 20, "set_type": "normal"},
        )
        set_obj = PlanSet.objects.get(plan_exercise=entry)
        self.assertEqual(set_obj.reps, 12)
        self.assertEqual(set_obj.volume, 20 * 12)

    def test_invalid_set_values_are_rejected(self):
        plan = self.create_plan()
        entry = PlanExercise.objects.create(plan=plan, exercise=self.exercise)
        self.client.post(
            reverse("plans:add_set", args=[entry.pk]),
            {"set_number": 1, "reps": -3, "duration_seconds": 0, "weight_kg": 20, "set_type": "normal"},
        )
        self.assertFalse(PlanSet.objects.exists())

    def test_edit_and_delete_plan(self):
        plan = self.create_plan()
        self.client.post(
            reverse("plans:edit", args=[plan.pk]),
            {"name": "Renamed", "description": "", "goal": "strength", "estimated_duration_minutes": 30},
        )
        plan.refresh_from_db()
        self.assertEqual(plan.name, "Renamed")

        self.client.post(reverse("plans:delete", args=[plan.pk]))
        self.assertFalse(WorkoutPlan.objects.filter(pk=plan.pk).exists())

    def test_other_users_cannot_access_a_plan(self):
        plan = self.create_plan()
        self.client.login(username="other", password="pw12345678")
        response = self.client.get(reverse("plans:detail", args=[plan.pk]))
        self.assertEqual(response.status_code, 404)
