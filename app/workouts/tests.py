"""Tests for session logging and personal record detection (FREQ-8, FREQ-10, FREQ-11)."""
from datetime import timedelta

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from exercises.models import Equipment, Exercise, ExerciseEquipment
from exercises.management.commands.seed_data import EXERCISE_IMAGES
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

    def test_active_session_uses_clickable_static_thumbnail(self):
        self.exercise.image = EXERCISE_IMAGES["Incline Dumbbell Press"]
        self.exercise.save(update_fields=["image"])
        session = start_session(self.user, self.plan)

        response = self.client.get(reverse("workouts:active", args=[session.pk]))

        self.assertContains(response, f'src="{self.exercise.local_thumbnail_url}"')
        self.assertContains(response, f'href="{reverse("exercises:detail", args=[self.exercise.pk])}"')
        self.assertNotContains(response, f'src="{self.exercise.local_image_url}"')
        self.assertEqual(self.client.get(reverse("workouts:records")).status_code, 200)

    def log_json(self, entry, **changes):
        data = {"set_number": 1, "reps_completed": 8, "weight_kg": 80, "duration_seconds": 0}
        return self.client.post(
            reverse("workouts:log_set", args=[entry.pk]),
            {**data, **changes},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )

    def test_active_targets_are_frozen_and_previous_performance_is_scoped(self):
        past = start_session(self.user, self.plan)
        past.exercises.get().sets.create(reps_completed=7, weight_kg=72.5)
        finish_session(past)

        unfinished = start_session(self.user, self.plan)
        unfinished.exercises.get().sets.create(reps_completed=99, weight_kg=100)
        session = start_session(self.user, self.plan)
        other = User.objects.create_user(username="other")
        private = start_session(other, self.plan)
        private.exercises.get().sets.create(reps_completed=10, weight_kg=120)
        finish_session(private)
        self.plan.exercises.update(rest_seconds=15)
        self.plan.exercises.get().sets.update(reps=12, weight_kg=100)
        self.plan.delete()

        result = self.client.get(reverse("workouts:active", args=[session.pk])).context["workout_data"][0]
        self.assertEqual(result["rest"], 90)
        self.assertEqual(result["rows"][0]["target"]["weight_kg"], 80)
        self.assertEqual(result["rows"][0]["target"]["reps_completed"], 8)
        self.assertEqual(result["previous"][1]["weight_kg"], 72.5)
        self.assertIsNone(result["rows"][0]["logged"])

    def test_shared_classification_exposes_resistance_bodyweight_timed_and_cardio(self):
        barbell = Equipment.objects.create(name="Barbell")
        ExerciseEquipment.objects.create(exercise=self.exercise, equipment=barbell)
        for name, exercise_type in [
            ("Push-up", "strength"), ("Plank", "strength"), ("Treadmill", "strength"),
        ]:
            PlanExercise.objects.create(
                plan=self.plan, exercise=Exercise.objects.create(name=name, exercise_type=exercise_type),
            )
        session = start_session(self.user, self.plan)
        result = self.client.get(reverse("workouts:active", args=[session.pk])).context["workout_data"]
        self.assertEqual([item["kind"] for item in result], ["resistance", "bodyweight", "timed", "cardio"])

    def test_duplicate_requests_and_validation_do_not_create_extra_sets(self):
        entry = start_session(self.user, self.plan).exercises.get()
        invalid = self.log_json(entry, weight_kg="inf")
        self.assertEqual(invalid.status_code, 400)
        self.assertFalse(entry.sets.exists())
        first = self.log_json(entry)
        retry = self.log_json(entry)
        self.assertTrue(first.json()["new_record"])
        self.assertEqual(retry.json()["set"]["id"], first.json()["set"]["id"])
        self.assertFalse(retry.json()["new_record"])
        self.assertEqual(self.log_json(entry, weight_kg="81").status_code, 409)
        extra = self.log_json(entry, set_number=2)
        self.assertEqual(extra.status_code, 200)
        self.assertEqual(list(entry.sets.values_list("set_number", flat=True)), [1, 2])

    def test_edit_and_undo_recalculate_records_and_preserve_earlier_rpe(self):
        past = start_session(self.user, self.plan)
        past_set = past.exercises.get().sets.create(reps_completed=6, weight_kg=70, rpe=8)
        evaluate_personal_record(past_set)
        finish_session(past)
        entry = start_session(self.user, self.plan).exercises.get()
        logged = self.log_json(entry, weight_kg=95, rpe=9).json()["set"]
        record = PersonalRecord.objects.get(record_type=PersonalRecord.RecordType.MAX_WEIGHT)
        self.assertEqual(record.value, 95)
        edited = self.log_json(entry, operation="edit", logged_id=logged["id"], weight_kg=65)
        self.assertEqual(edited.status_code, 200)
        self.assertEqual(edited.json()["set"]["rpe"], 9)
        record.refresh_from_db()
        self.assertEqual(record.session_set, past_set)
        improved = self.log_json(entry, operation="edit", logged_id=logged["id"], weight_kg=85, rpe=9)
        self.assertTrue(improved.json()["new_record"])
        undone = self.log_json(entry, operation="undo", logged_id=logged["id"])
        self.assertIsNone(undone.json()["set"])
        self.assertFalse(entry.sets.exists())
        record.refresh_from_db()
        self.assertEqual(record.session_set, past_set)
        past_set.refresh_from_db()
        self.assertEqual(past_set.rpe, 8)
        self.assertTrue(past_set.is_personal_record)

    def test_finish_incomplete_is_explicit_and_finish_is_idempotent(self):
        session = start_session(self.user, self.plan)
        entry = session.exercises.get()
        url = reverse("workouts:complete", args=[session.pk])
        headers = {"X-Requested-With": "XMLHttpRequest"}
        response = self.client.post(url, headers=headers)
        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.json()["incomplete"])
        response = self.client.post(url, {"allow_incomplete": "yes", "notes": "Later", "rating": 4}, headers=headers)
        self.assertEqual(response.json()["url"], reverse("workouts:detail", args=[session.pk]))
        session.refresh_from_db()
        finished = session.ended_at
        self.client.post(url, {"allow_incomplete": "yes", "notes": "Second attempt", "rating": 2}, headers=headers)
        session.refresh_from_db()
        self.assertEqual((session.ended_at, session.notes, session.rating), (finished, "Later", 4))
        self.assertEqual(self.log_json(entry).status_code, 409)
        self.assertFalse(entry.sets.exists())

    def test_workout_mutations_require_owner_post_and_csrf(self):
        session = start_session(self.user, self.plan)
        entry = session.exercises.get()
        log_url = reverse("workouts:log_set", args=[entry.pk])
        finish_url = reverse("workouts:complete", args=[session.pk])
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        client.get(reverse("workouts:active", args=[session.pk]))
        token = client.cookies["csrftoken"].value
        for url in [log_url, finish_url]:
            self.assertEqual(client.get(url).status_code, 405)
            self.assertEqual(client.post(url).status_code, 403)
        client.force_login(User.objects.create_user(username="outsider"))
        client.get(reverse("workouts:sessions"))
        token = client.cookies["csrftoken"].value
        for url in [log_url, finish_url]:
            self.assertEqual(client.post(url, {"csrfmiddlewaretoken": token}).status_code, 404)

    def test_active_and_summary_use_arabic_labels_and_rtl(self):
        session = start_session(self.user, self.plan)
        self.client.post(reverse("set_language"), {"language": "ar", "next": "/"})
        response = self.client.get(reverse("workouts:active", args=[session.pk]))
        self.assertContains(response, 'dir="rtl"')
        self.assertContains(response, "إنهاء التمرين")
        self.assertNotContains(response, 'id="workout-rest"')
        self.assertNotContains(response, 'data-action="rpe"')
        finish_session(session)
        self.assertContains(self.client.get(reverse("workouts:detail", args=[session.pk])), "اكتمل التمرين")
