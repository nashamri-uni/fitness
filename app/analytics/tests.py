"""Tests for analytics and improvement metrics (FREQ-9, FREQ-10, FREQ-12)."""
from datetime import UTC, datetime, time, timedelta
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User, UserProfile, WeeklyWorkoutGoalHistory
from exercises.models import Equipment, Exercise, ExerciseEquipment, ExerciseMuscleGroup, MuscleGroup
from plans.models import PlanExercise, WorkoutPlan
from workouts.models import PersonalRecord, SessionExercise, SessionSet, WorkoutSession
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
        self.assertContains(response, "Dashboard sections")
        self.assertContains(response, 'data-account-dropdown')
        self.assertContains(response, 'aria-controls="account-dropdown-menu"')
        self.assertContains(response, reverse("accounts:profile"))
        self.assertContains(response, "Log out")
        self.assertContains(response, 'method="post" action="/accounts/logout/"')
        self.assertContains(response, 'class="theme-toggle-moon"')
        self.assertContains(response, 'class="theme-toggle-sun"')
        self.assertEqual(response.content.decode().count('aria-current="page"'), 2)
        self.assertNotContains(response, "Workout and Fitness Planner — Django project")
        self.assertContains(response, "data-activity-chart")
        self.assertContains(response, "?tab=progress")
        self.assertContains(response, "?tab=records")
        self.assertNotContains(response, reverse("workouts:records"))
        self.assertNotContains(response, "Weekly training volume")
        self.assertNotContains(response, "Average RPE")
        self.assertNotContains(response, "Average session")
        self.assertNotContains(response, "Total volume (kg)")
        self.assertEqual(response.content.decode().count('class="analytics-stat"'), 3)
        self.assertContains(response, 'analytics-stat--gold')

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
            goal = response.context["goal"]
            recent = response.context["recent"]

        self.assertEqual(goal["sessions"], 1)
        self.assertEqual(recent, completed)
        self.assertEqual((recent.exercise_count, recent.set_count), (0, 0))
        self.assertEqual(response.context["active_session"].user_id, self.user.pk)
        self.assertNotContains(response, other_plan.name)

    def test_dashboard_in_arabic_renders_translated_activity_controls(self):
        with self.settings(LANGUAGE_CODE="ar"):
            response = self.client.get(reverse("analytics:dashboard"), HTTP_ACCEPT_LANGUAGE="ar")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "أسبوعي")
        self.assertContains(response, "يومي")
        self.assertContains(response, "هدف التدريب الأسبوعي")
        self.assertContains(response, "التقدم الرياضي")
        self.assertContains(response, "الأرقام القياسية")
        self.assertContains(response, 'dir="rtl"')

    def test_dashboard_shows_empty_activity_message_without_completed_workouts(self):
        response = self.client.get(reverse("analytics:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your latest workout will appear here after you finish a session.")
        self.assertEqual([row["sessions"] for row in response.context["activity_rows"]], [0] * 7)

    def test_progress_page(self):
        self.add_session(30, [(1, 10, 50)])
        url = reverse("analytics:dashboard")
        self.assertRedirects(
            self.client.get(reverse("analytics:progress"), {"range": "all", "tab": "records"}),
            f"{url}?range=all&tab=progress",
        )
        self.assertRedirects(
            self.client.get(reverse("workouts:records"), {"type": "max_weight"}),
            f"{url}?type=max_weight&tab=records",
        )
        response = self.client.get(url, {"tab": "progress", "range": "all", "metric": "weight"})
        self.assertContains(response, "Exercise performance")
        self.assertContains(response, "Log another comparable workout to see a change.")
        self.assertEqual(response.context["performance"]["latest"], 50)

    def test_activity_periods_and_weekly_goal(self):
        now = datetime(2026, 11, 26, 15, tzinfo=UTC)
        with patch("django.utils.timezone.now", return_value=now):
            today = timezone.localdate()
            self.add_session_on(self.user, today)
            self.add_session_on(self.user, today)
            self.add_session_on(self.user, today - timedelta(weeks=1))
            self.add_session_on(self.user, today, completed=False)
            UserProfile.objects.update_or_create(user=self.user, defaults={"weekly_workout_goal": 3})
            url = reverse("analytics:dashboard")
            response = self.client.get(url)
            self.assertEqual(response.context["weekly_deltas"], {"count": 1, "minutes": 60})
            self.assertEqual([row["sessions"] for row in response.context["activity_rows"]], [0, 0, 0, 2, 0, 0, 0])
            goal = response.context["goal"]
            self.assertEqual((goal["sessions"], goal["days"], goal["remaining"], goal["percentage"]), (2, 1, 2, 33))
            weeks = self.client.get(url, {"activity": "weekly"}).context["activity_rows"]
            self.assertEqual(len(weeks), 8)
            self.assertEqual([(row["sessions"], row["days"]) for row in weeks[-3:]], [(0, 0), (1, 1), (2, 1)])
            prior_monday = today - timedelta(days=today.weekday(), weeks=1)
            prior = self.client.get(url, {"week": prior_monday.isoformat()}).context["activity_rows"]
            self.assertEqual(prior[0]["date"], prior_monday)
            self.assertEqual(sum(row["sessions"] for row in prior), 1)

    def test_performance_uses_chronology_ranges_and_zero_baselines(self):
        older = self.add_session(50, [(1, 4, 0)])
        peak = self.add_session(10, [(1, 5, 100), (2, 10, 95)])
        latest = self.add_session(2, [(1, 6, 75)])
        unfinished = self.add_session_on(self.user, timezone.localdate(), completed=False)
        entry = SessionExercise.objects.create(session=unfinished, exercise=self.exercise)
        SessionSet.objects.create(session_exercise=entry, reps_completed=20, weight_kg=900)
        url = reverse("analytics:dashboard")
        params = {"tab": "progress", "metric": "weight", "range": "all"}
        response = self.client.get(url, params)
        self.assertEqual([row["session"] for row in response.context["points"]], [older.pk, peak.pk, latest.pk])
        self.assertEqual([row["value"] for row in response.context["points"]], [0, 100, 75])
        facts = response.context["performance"]
        self.assertEqual(facts["delta"], {"value": 75, "percent": None})
        self.assertEqual(facts["previous"], {"value": -25, "percent": -25})
        self.assertEqual(facts["best"], 100)
        params["range"] = "1m"
        filtered = self.client.get(url, params)
        self.assertEqual(filtered.context["performance"]["first"], 100)
        self.assertContains(filtered, "analytics-negative")

    def test_cardio_duration_and_missing_metrics(self):
        bike = Exercise.objects.create(name="Spin bike", name_ar="دراجة", exercise_type="cardio")
        session = self.add_session_on(self.user, timezone.localdate() - timedelta(days=2))
        entry = SessionExercise.objects.create(session=session, exercise=bike)
        SessionSet.objects.bulk_create([
            SessionSet(session_exercise=entry, duration_seconds=40, reps_completed=2),
            SessionSet(session_exercise=entry, duration_seconds=20, reps_completed=4),
        ])
        second = self.add_session_on(self.user, timezone.localdate() - timedelta(days=1))
        missing = SessionExercise.objects.create(session=second, exercise=bike)
        SessionSet.objects.create(session_exercise=missing)
        url = reverse("analytics:dashboard")
        response = self.client.get(url, {"tab": "progress", "exercise": bike.pk, "metric": "weight"})
        self.assertEqual([metric[0] for metric in response.context["metrics"]], ["duration"])
        self.assertEqual([point["value"] for point in response.context["points"]], [60, None])
        self.assertEqual(response.context["performance"]["latest"], 60)
        self.assertIsNone(response.context["performance"]["delta"])

    def test_epley_limits_and_exercise_picker_exclude_private_and_unlogged_exercises(self):
        barbell = Equipment.objects.create(name="Barbell")
        ExerciseEquipment.objects.create(exercise=self.exercise, equipment=barbell)
        self.add_session(8, [(1, 5, 90), (2, 15, 210)])
        private = Exercise.objects.create(name="Private exercise", exercise_type="strength")
        other = User.objects.create_user(username="private")
        entry = SessionExercise.objects.create(
            session=self.add_session_on(other, timezone.localdate()), exercise=private,
        )
        SessionSet.objects.create(session_exercise=entry, reps_completed=5, weight_kg=300)
        Exercise.objects.create(name="Unlogged exercise", exercise_type="strength")
        response = self.client.get(reverse("analytics:dashboard"), {"tab": "progress", "exercise": private.pk, "metric": "e1rm"})
        self.assertEqual(response.context["exercises"], [self.exercise])
        self.assertEqual(response.context["observations"][0]["value"], 105)
        self.assertNotContains(response, private.name)

    def test_distribution_splits_primary_groups_and_never_counts_secondary_groups(self):
        groups = [MuscleGroup.objects.create(name=name, body_region="lower") for name in ("Glutes", "Quads", "Calves")]
        for group, role in zip(groups, ("primary", "primary", "secondary")):
            ExerciseMuscleGroup.objects.create(exercise=self.exercise, muscle_group=group, role=role)
        self.add_session(56, [(1, 6, 40)])
        recent = self.add_session(1, [(1, 6, 70)])
        unclassified = Exercise.objects.create(name="Unclassified movement", exercise_type="strength")
        entry = SessionExercise.objects.create(session=recent, exercise=unclassified)
        SessionSet.objects.create(session_exercise=entry, reps_completed=3)
        response = self.client.get(reverse("analytics:dashboard"), {"tab": "progress", "muscle_range": "1m"})
        self.assertEqual(response.context["distribution_total"], 2)
        self.assertEqual({row["name"]: row["sets"] for row in response.context["distribution"]}, {
            "Glutes": .5, "Quads": .5, "Unclassified": 1,
        })

    def test_record_filter_search_group_type_and_ownership(self):
        self.exercise.name_ar = "قرفصاء"
        self.exercise.save(update_fields=["name_ar"])
        group = MuscleGroup.objects.create(name="Quads", body_region="lower")
        ExerciseMuscleGroup.objects.create(exercise=self.exercise, muscle_group=group)
        finished = self.add_session(1, [(1, 5, 100)])
        other = User.objects.create_user(username="private")
        PersonalRecord.objects.create(
            user=other, exercise=self.exercise, record_type="max_weight", value=999, achieved_at=timezone.now(),
        )
        url = reverse("analytics:dashboard")
        response = self.client.get(url, {"tab": "records", "muscle": group.pk, "type": "max_weight", "q": "قرفصاء"})
        self.assertEqual(response.context["bests"], {"count": 3, "exercises": 1})
        exercise, records = response.context["record_groups"][0]
        self.assertEqual(exercise, self.exercise)
        self.assertEqual([record.value for record in records], [100])
        self.assertContains(response, reverse("workouts:detail", args=[finished.pk]))
        unmatched = self.client.get(url, {"tab": "records", "q": "missing"})
        self.assertContains(unmatched, "No personal bests match these filters.")

    def test_overview_start_resumes_one_active_workout_and_checks_plan_owner(self):
        url = reverse("analytics:dashboard")
        start = reverse("workouts:start", args=[self.plan.pk])
        self.assertContains(self.client.get(url), start)
        created = self.client.post(start)
        another = WorkoutPlan.objects.create(user=self.user, name="Another day")
        PlanExercise.objects.create(plan=another, exercise=self.exercise)
        repeated = self.client.post(reverse("workouts:start", args=[another.pk]))
        self.assertEqual(repeated.url, created.url)
        self.assertEqual(self.user.sessions.filter(ended_at__isnull=True).count(), 1)
        response = self.client.get(url)
        self.assertContains(response, "Continue Workout")
        self.assertNotContains(response, "Start Workout")
        private = WorkoutPlan.objects.create(user=User.objects.create_user(username="other"), name="Private")
        self.assertEqual(self.client.post(reverse("workouts:start", args=[private.pk])).status_code, 404)

    def test_empty_progress_and_records(self):
        url = reverse("analytics:dashboard")
        progress = self.client.get(url, {"tab": "progress"})
        self.assertContains(progress, "Finish a workout with logged sets")
        self.assertNotContains(progress, "data-performance-chart")
        self.assertContains(self.client.get(url, {"tab": "records"}), "Your personal bests will appear here")
