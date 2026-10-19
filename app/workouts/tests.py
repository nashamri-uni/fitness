"""Tests for session logging and personal record detection (FREQ-8, FREQ-10, FREQ-11)."""
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from exercises.models import Exercise
from plans.models import PlanExercise, PlanSet, WorkoutPlan

from .models import PersonalRecord, SessionExercise, SessionSet, WorkoutSession
from .services import evaluate_personal_record, finish_session, start_session


class SessionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="lifter", email="l@example.com", password="pw12345678")
        self.client.login(username="lifter", password="pw12345678")
        self.exercise = Exercise.objects.create(name="Bench Press", exercise_type="strength")
        self.plan = WorkoutPlan.objects.create(user=self.user, name="Push Day")
        entry = PlanExercise.objects.create(plan=self.plan, exercise=self.exercise, order=1)
        PlanSet.objects.create(plan_exercise=entry, set_number=1, reps=8, weight_kg=80)

    def test_start_session_copies_plan_exercises(self):
        response = self.client.post(reverse("workouts:start", args=[self.plan.pk]))
        session = WorkoutSession.objects.get(user=self.user)
        self.assertRedirects(response, reverse("workouts:active", args=[session.pk]))
        self.assertEqual(SessionExercise.objects.filter(session=session).count(), 1)
        self.assertFalse(session.is_finished)

    def test_start_session_requires_exercises(self):
        empty_plan = WorkoutPlan.objects.create(user=self.user, name="Empty")
        self.client.post(reverse("workouts:start", args=[empty_plan.pk]))
        self.assertFalse(WorkoutSession.objects.exists())

    def test_logging_first_set_creates_personal_records(self):
        session = start_session(self.user, self.plan)
        entry = session.exercises.get()
        set_obj = SessionSet.objects.create(
            session_exercise=entry, set_number=1, reps_completed=8, weight_kg=80, duration_seconds=30
        )
        beaten = evaluate_personal_record(set_obj)

        self.assertTrue(beaten)
        self.assertTrue(set_obj.is_personal_record)
        self.assertEqual(PersonalRecord.objects.filter(user=self.user).count(), 4)
        record = PersonalRecord.objects.get(record_type=PersonalRecord.RecordType.MAX_WEIGHT)
        self.assertEqual(record.value, 80)
        self.assertEqual(record.session_set, set_obj)

    def test_beating_a_record_updates_it(self):
        session = start_session(self.user, self.plan)
        entry = session.exercises.get()
        first = SessionSet.objects.create(session_exercise=entry, set_number=1, reps_completed=8, weight_kg=80)
        evaluate_personal_record(first)

        better = SessionSet.objects.create(session_exercise=entry, set_number=2, reps_completed=10, weight_kg=90)
        beaten = evaluate_personal_record(better)

        record = PersonalRecord.objects.get(
            user=self.user,
            exercise=self.exercise,
            record_type=PersonalRecord.RecordType.MAX_WEIGHT,
        )
        self.assertEqual(record.value, 90)
        self.assertEqual(record.session_set, better)
        self.assertIn(PersonalRecord.RecordType.MAX_WEIGHT, beaten)
        self.assertTrue(better.is_personal_record)

    def test_non_improving_set_is_not_a_record(self):
        session = start_session(self.user, self.plan)
        entry = session.exercises.get()
        first = SessionSet.objects.create(session_exercise=entry, set_number=1, reps_completed=8, weight_kg=80)
        evaluate_personal_record(first)

        weaker = SessionSet.objects.create(session_exercise=entry, set_number=2, reps_completed=6, weight_kg=70)
        beaten = evaluate_personal_record(weaker)
        self.assertFalse(beaten)
        self.assertFalse(weaker.is_personal_record)

    def test_log_set_view_flags_record(self):
        session = start_session(self.user, self.plan)
        entry = session.exercises.get()
        response = self.client.post(
            reverse("workouts:log_set", args=[entry.pk]),
            {"set_number": 1, "reps_completed": 10, "weight_kg": 100, "duration_seconds": 0, "rpe": 9},
        )
        self.assertRedirects(response, reverse("workouts:active", args=[session.pk]))
        set_obj = SessionSet.objects.get(session_exercise=entry)
        self.assertTrue(set_obj.is_personal_record)

    def test_finish_session_calculates_duration(self):
        session = start_session(self.user, self.plan)
        session.started_at = timezone.now() - timedelta(minutes=45)
        session.save()
        finish_session(session, notes="Good session", rating=4)
        session.refresh_from_db()
        self.assertTrue(session.is_finished)
        self.assertEqual(session.duration_minutes, 45)
        self.assertEqual(session.rating, 4)

    def test_session_volume(self):
        session = start_session(self.user, self.plan)
        entry = session.exercises.get()
        SessionSet.objects.create(session_exercise=entry, set_number=1, reps_completed=10, weight_kg=60)
        self.assertEqual(session.total_volume(), 600)

    def test_history_and_detail_pages(self):
        session = start_session(self.user, self.plan)
        finish_session(session)
        self.assertEqual(self.client.get(reverse("workouts:sessions")).status_code, 200)
        self.assertEqual(self.client.get(reverse("workouts:detail", args=[session.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("workouts:records")).status_code, 200)
