"""Tests for analytics and improvement metrics (FREQ-9, FREQ-10, FREQ-12)."""
from datetime import datetime, time, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from exercises.models import Exercise
from plans.models import PlanExercise, WorkoutPlan
from workouts.models import SessionExercise, SessionSet, WorkoutSession
from workouts.services import evaluate_personal_record

from .services import exercise_progress, summary, training_streak, weekly_volume, workout_activity


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

    def add_session_on(self, user, day, completed=True):
        started_at = timezone.make_aware(
            datetime.combine(day, time(10)),
            timezone.get_current_timezone(),
        )
        return WorkoutSession.objects.create(
            user=user,
            plan=self.plan if user == self.user else None,
            name="Activity session",
            started_at=started_at,
            ended_at=started_at if completed else None,
            duration_minutes=60,
        )

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

    def test_workout_activity_counts_unique_completed_local_days(self):
        today = timezone.localdate()
        current_monday = today - timedelta(days=today.weekday())
        active_day = current_monday + timedelta(days=1)
        self.add_session_on(self.user, active_day)
        self.add_session_on(self.user, active_day)
        self.add_session_on(self.user, current_monday + timedelta(days=3))
        self.add_session_on(self.user, current_monday + timedelta(days=4), completed=False)
        self.add_session_on(self.user, current_monday - timedelta(days=1))

        other_user = User.objects.create_user(username="other", password="pw12345678")
        self.add_session_on(other_user, active_day)

        activity = workout_activity(self.user)
        this_week = next(week for week in activity["weeks"] if week["start"] == current_monday.isoformat())
        self.assertEqual(this_week["count"], 2)
        self.assertEqual(this_week["daily"], [0, 2, 0, 1, 0, 0, 0])
        previous_week = next(
            week for week in activity["weeks"]
            if week["start"] == (current_monday - timedelta(weeks=1)).isoformat()
        )
        self.assertEqual(previous_week["count"], 1)
        self.assertEqual(previous_week["daily"], [0, 0, 0, 0, 0, 0, 1])
        self.assertTrue(activity["has_activity"])

    def test_workout_activity_includes_zero_weeks_and_seven_daily_values(self):
        activity = workout_activity(self.user)

        self.assertEqual(len(activity["weeks"]), 12)
        self.assertTrue(all(week["count"] == 0 for week in activity["weeks"]))
        self.assertTrue(all(len(week["daily"]) == 7 for week in activity["weeks"]))
        self.assertFalse(activity["has_activity"])

    def test_workout_activity_groups_by_local_calendar_date(self):
        with timezone.override("America/Los_Angeles"):
            local_today = timezone.localdate()
            local_monday = local_today - timedelta(days=local_today.weekday())
            late_local_day = local_monday + timedelta(days=1)
            self.add_session_on(self.user, late_local_day)
            activity = workout_activity(self.user)

        local_week = next(week for week in activity["weeks"] if week["start"] == local_monday.isoformat())
        self.assertEqual(local_week["daily"][1], 1)

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
        self.assertContains(response, "activity-chart")
        self.assertNotContains(response, "Weekly training volume")

    def test_dashboard_in_arabic_renders_translated_activity_controls(self):
        with self.settings(LANGUAGE_CODE="ar"):
            response = self.client.get(reverse("analytics:dashboard"), HTTP_ACCEPT_LANGUAGE="ar")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "أسبوعي")
        self.assertContains(response, "يومي")

    def test_dashboard_shows_empty_activity_message_without_completed_workouts(self):
        response = self.client.get(reverse("analytics:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No completed workouts in this week.")

    def test_progress_page(self):
        self.add_session(30, [(1, 10, 50)])
        response = self.client.get(reverse("analytics:progress"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Improvement metrics")
