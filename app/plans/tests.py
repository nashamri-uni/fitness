"""Tests for workout plans (FREQ-4 to FREQ-7)."""
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from exercises.models import Exercise

from .models import PlanExercise, PlanSet, WorkoutPlan


class PlanTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="planowner", email="p@example.com", password="pw12345678")
        self.other = User.objects.create_user(username="other", email="o@example.com", password="pw12345678")
        self.client.login(username="planowner", password="pw12345678")
        self.exercise = Exercise.objects.create(name="Push-up", exercise_type="strength", difficulty="beginner")

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
            {"exercise": self.exercise.pk, "order": 1, "rest_seconds": 120},
        )
        self.assertRedirects(response, reverse("plans:detail", args=[plan.pk]))
        entry = PlanExercise.objects.get(plan=plan)
        self.assertEqual(entry.exercise, self.exercise)
        self.assertEqual(entry.rest_seconds, 120)

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
