"""Tests for analytics and improvement metrics (FREQ-9, FREQ-10, FREQ-12)."""
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from exercises.models import Exercise
from plans.models import PlanExercise, WorkoutPlan
from workouts.models import SessionExercise, SessionSet, WorkoutSession
from workouts.services import evaluate_personal_record

from .services import exercise_progress, summary, training_streak, weekly_volume


class AnalyticsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tracker", email="t@example.com", password="pw12345678")
        self.client.login(username="tracker", password="pw12345678")
        self.exercise = Exercise.objects.create(name="Squat", exercise_type="strength")
        self.plan = WorkoutPlan.objects.create(user=self.user, name="Leg Day")
        PlanExercise.objects.create(plan=self.plan, exercise=self.exercise, order=1)

    def add_session(self, days_ago, sets):
        session = WorkoutSession.objects.create(
            user=self.user, plan=self.plan, name="Session",
            started_at=timezone.now() - timedelta(days=days_ago),
            ended_at=timezone.now() - timedelta(days=days_ago),
            duration_minutes=60,
        )
        entry = SessionExercise.objects.create(session=session, exercise=self.exercise, order=1)
        for set_number, reps, weight in sets:
            set_obj = SessionSet.objects.create(
                session_exercise=entry, set_number=set_number, reps_completed=reps, weight_kg=weight
            )
            evaluate_personal_record(set_obj)
        return session

    def test_improvement_metrics(self):
        self.add_session(60, [(1, 10, 60)])
        self.add_session(5, [(1, 10, 80)])

        progress = exercise_progress(self.user)
        self.assertEqual(len(progress), 1)
        row = progress[0]
        self.assertEqual(row["first"], 60)
        self.assertEqual(row["current"], 80)
        self.assertEqual(row["change_pct"], 33.3)

    def test_weekly_volume_chart(self):
        self.add_session(20, [(1, 10, 50)])  # 500 kg
        self.add_session(3, [(1, 12, 50)])   # 600 kg
        chart = weekly_volume(self.user, weeks=12)
        self.assertEqual(len(chart["labels"]), 2)
        self.assertEqual(sum(chart["volume"]), 1100.0)
        self.assertEqual(sum(chart["sets"]), 2)

    def test_summary_and_streak(self):
        self.add_session(10, [(1, 10, 50)])
        self.add_session(2, [(1, 10, 50)])
        stats = summary(self.user)
        self.assertEqual(stats["total_sessions"], 2)
        self.assertEqual(stats["total_volume_kg"], 1000.0)
        self.assertGreaterEqual(stats["streak_weeks"], 1)
        self.assertEqual(training_streak(self.user), stats["streak_weeks"])

    def test_dashboard_page(self):
        self.add_session(4, [(1, 10, 50)])
        response = self.client.get(reverse("analytics:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Analytics dashboard")

    def test_progress_page(self):
        self.add_session(30, [(1, 10, 50)])
        response = self.client.get(reverse("analytics:progress"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Improvement metrics")
