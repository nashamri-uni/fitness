"""Tests for analytics and improvement metrics (FREQ-9, FREQ-10, FREQ-12)."""
from datetime import datetime, time, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User, UserProfile, WeeklyWorkoutGoalHistory
from exercises.models import Exercise
from plans.models import PlanExercise, WorkoutPlan
from workouts.models import SessionExercise, SessionSet, WorkoutSession
from workouts.services import evaluate_personal_record

from .services import (
    exercise_progress,
    summary,
    training_streak,
    weekly_goal_progress,
    weekly_volume,
    workout_activity,
)


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

    def test_weekly_goal_counts_completed_sessions_and_unique_local_days(self):
        UserProfile.objects.create(user=self.user, weekly_workout_goal=3)
        today = timezone.localdate()
        monday = today - timedelta(days=today.weekday())
        self.add_session_on(self.user, monday + timedelta(days=1))
        self.add_session_on(self.user, monday + timedelta(days=1))
        self.add_session_on(self.user, monday + timedelta(days=3))
        self.add_session_on(self.user, monday + timedelta(days=5), completed=False)

        other_user = User.objects.create_user(username="other", password="pw12345678")
        self.add_session_on(other_user, monday + timedelta(days=1))

        progress = weekly_goal_progress(self.user)
        self.assertEqual(progress["sessions"], 3)
        self.assertEqual(progress["days"], 2)
        self.assertEqual(progress["goal"], 3)
        self.assertEqual(progress["percentage"], 67)

    def test_weekly_goal_history_preserves_prior_week_targets(self):
        today = timezone.localdate()
        current_monday = today - timedelta(days=today.weekday())
        previous_week = current_monday - timedelta(weeks=2)
        next_week = previous_week + timedelta(weeks=1)
        current_timezone = timezone.get_current_timezone()
        WeeklyWorkoutGoalHistory.objects.create(
            user=self.user,
            goal_days=3,
            effective_at=timezone.make_aware(
                datetime.combine(previous_week - timedelta(days=1), time(12)),
                current_timezone,
            ),
        )
        WeeklyWorkoutGoalHistory.objects.create(
            user=self.user,
            goal_days=5,
            effective_at=timezone.make_aware(
                datetime.combine(previous_week + timedelta(days=6), time(12)),
                current_timezone,
            ),
        )

        previous_progress = weekly_goal_progress(self.user, previous_week)
        next_progress = weekly_goal_progress(self.user, next_week)
        self.assertEqual(previous_progress["goal"], 3)
        self.assertEqual(next_progress["goal"], 5)
        self.assertEqual(previous_progress["percentage"], 0)

    def test_weekly_goal_uses_local_calendar_dates(self):
        with timezone.override("America/Los_Angeles"):
            today = timezone.localdate()
            monday = today - timedelta(days=today.weekday())
            session_day = monday + timedelta(days=1)
            started_at = timezone.make_aware(
                datetime.combine(session_day, time(23, 30)),
                timezone.get_current_timezone(),
            )
            UserProfile.objects.create(user=self.user, weekly_workout_goal=1)
            WorkoutSession.objects.create(
                user=self.user,
                plan=self.plan,
                name="Late local session",
                started_at=started_at,
                ended_at=started_at,
                duration_minutes=30,
            )

            progress = weekly_goal_progress(self.user)

        self.assertEqual(progress["days"], 1)
        self.assertEqual(progress["percentage"], 100)

    def test_summary_and_streak(self):
        self.add_session(10, [(1, 10, 50)])
        self.add_session(2, [(1, 10, 50)])
        stats = summary(self.user)
        self.assertEqual(stats["total_sessions"], 2)
        self.assertEqual(stats["total_volume_kg"], 1000.0)
        self.assertGreaterEqual(stats["streak_weeks"], 1)
        self.assertEqual(training_streak(self.user), stats["streak_weeks"])

    def test_training_streak_is_not_limited_to_twelve_weeks(self):
        today = timezone.localdate()
        monday = today - timedelta(days=today.weekday())
        for weeks_ago in range(14):
            self.add_session_on(self.user, monday - timedelta(weeks=weeks_ago))

        self.assertEqual(training_streak(self.user), 14)
        self.assertEqual(training_streak(self.user, weeks=12), 12)

    def test_summary_provides_real_values_for_dashboard_cards(self):
        UserProfile.objects.create(user=self.user, weekly_workout_goal=2)
        self.add_session(1, [(1, 10, 50)])
        self.add_session(1, [(1, 10, 50)])
        other_user = User.objects.create_user(username="other", password="pw12345678")
        WorkoutPlan.objects.create(user=other_user, name="Other plan")
        self.add_session_on(other_user, timezone.localdate())

        stats = summary(self.user)
        self.assertEqual(stats["total_sessions"], 2)
        self.assertEqual(stats["sessions_this_week"], 2)
        self.assertEqual(stats["workout_plans"], 1)
        self.assertEqual(stats["weekly_goal_days"], 2)
        self.assertEqual(stats["weekly_goal_completed_days"], 1)
        self.assertEqual(stats["weekly_goal_percent"], 50)
        self.assertEqual(
            stats["personal_records"],
            self.user.personal_records.count(),
        )
        self.assertGreaterEqual(stats["streak_weeks"], 1)

    def test_dashboard_page(self):
        self.add_session(4, [(1, 10, 50)])
        response = self.client.get(reverse("analytics:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Analytics dashboard")
        self.assertContains(response, 'data-account-dropdown')
        self.assertContains(response, 'aria-controls="account-dropdown-menu"')
        self.assertContains(response, reverse("accounts:profile"))
        self.assertContains(response, "Log out")
        self.assertContains(response, 'method="post" action="/accounts/logout/"')
        self.assertContains(response, 'class="theme-toggle-moon"')
        self.assertContains(response, 'class="theme-toggle-sun"')
        self.assertEqual(response.content.decode().count('aria-current="page"'), 1)
        self.assertNotContains(response, "Workout and Fitness Planner — Django project")
        self.assertContains(response, "activity-chart")
        self.assertContains(response, 'id="dashboard-details-dialog"')
        for detail in ("sessions", "week", "plans", "goal", "records", "streak"):
            self.assertContains(response, f'data-dashboard-detail="{detail}"')
            self.assertContains(response, f'data-dashboard-detail-template="{detail}"')
        self.assertNotContains(response, "Weekly training volume")
        self.assertNotContains(response, "Average RPE")
        self.assertNotContains(response, "Average session")
        self.assertNotContains(response, "Total volume (kg)")
        self.assertEqual(response.content.decode().count('class="dashboard-stat-card'), 6)

    def test_dashboard_detail_queries_are_local_and_user_scoped(self):
        other_user = User.objects.create_user(username="other", password="pw12345678")
        other_plan = WorkoutPlan.objects.create(user=other_user, name="Other user's plan")

        with timezone.override("America/Los_Angeles"):
            today = timezone.localdate()
            monday = today - timedelta(days=today.weekday())
            completed = self.add_session_on(self.user, monday + timedelta(days=1))
            completed.name = "My completed session"
            completed.save(update_fields=["name"])
            self.add_session_on(self.user, monday + timedelta(days=2), completed=False)
            self.add_session_on(other_user, monday + timedelta(days=1))

            response = self.client.get(reverse("analytics:dashboard"))
            weekly_sessions = list(response.context["sessions_this_week"])
            plans = list(response.context["plans"])
            recent_sessions = list(response.context["recent_sessions"])

        self.assertEqual(weekly_sessions, [completed])
        self.assertEqual(plans, [self.plan])
        self.assertTrue(all(session.user_id == self.user.pk for session in recent_sessions))
        self.assertNotContains(response, other_plan.name)

    def test_dashboard_in_arabic_renders_translated_activity_controls(self):
        with self.settings(LANGUAGE_CODE="ar"):
            response = self.client.get(reverse("analytics:dashboard"), HTTP_ACCEPT_LANGUAGE="ar")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "أسبوعي")
        self.assertContains(response, "يومي")
        self.assertContains(response, "التقدم نحو الهدف الأسبوعي")
        self.assertContains(response, 'dir="rtl"')

    def test_dashboard_shows_empty_activity_message_without_completed_workouts(self):
        response = self.client.get(reverse("analytics:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No completed workouts in this week.")

    def test_progress_page(self):
        self.add_session(30, [(1, 10, 50)])
        response = self.client.get(reverse("analytics:progress"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Improvement metrics")
