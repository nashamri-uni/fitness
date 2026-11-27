"""Tests for workout plans (FREQ-4 to FREQ-7)."""
import json

from django.test import Client, TestCase
from django.test import TransactionTestCase
from django.urls import reverse
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from accounts.models import User
from exercises.management.commands.seed_data import EXERCISE_IMAGES
from exercises.models import Equipment, Exercise, ExerciseEquipment, ExerciseMuscleGroup, MuscleGroup
from .forms import AddExerciseForm

from .models import PlanExercise, PlanSet, WorkoutPlan, WorkoutProgram
from .views import program_revision


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

    def save_builder(self, program, payload):
        revision = program_revision(WorkoutProgram.objects.get(pk=program.pk))
        return self.client.post(
            reverse("plans:save_program", args=[program.pk]),
            data=json.dumps({"revision": revision, **payload}),
            content_type="application/json",
        )

    def test_plan_list_search_matches_english_and_arabic_names_for_current_user(self):
        self.create_plan()
        arabic_plan = WorkoutPlan.objects.create(user=self.user, name="تمرين الصدر")
        WorkoutPlan.objects.create(user=self.other, name="Push Day")

        english_response = self.client.get(reverse("plans:list"), {"q": "pUsH"})
        self.assertEqual(
            list(english_response.context["plans"].values_list("name", flat=True)),
            ["Push Day"],
        )
        self.assertContains(english_response, "Push Day")
        self.assertNotContains(english_response, "تمرين الصدر")

        arabic_response = self.client.get(reverse("plans:list"), {"q": "تمرين"})
        self.assertEqual(
            list(arabic_response.context["plans"].values_list("pk", flat=True)),
            [arabic_plan.pk],
        )
        self.assertContains(arabic_response, "تمرين الصدر")
        self.assertNotContains(arabic_response, "Push Day")

    def test_plan_list_search_shows_empty_message_and_clear_search_action(self):
        self.create_plan()

        response = self.client.get(reverse("plans:list"), {"q": "Cardio"})

        self.assertEqual(response.context["plans"].count(), 0)
        self.assertContains(response, "No programs found")
        self.assertContains(response, 'href="%s"' % reverse("plans:list"))
        self.assertContains(response, "Clear search")
        self.assertNotContains(response, "You have no workout programs yet.")

    def test_plan_list_search_controls_are_translated_into_arabic(self):
        self.create_plan()
        self.client.post(reverse("set_language"), {"language": "ar", "next": "/"})

        response = self.client.get(reverse("plans:list"), {"q": "غير موجود"})

        self.assertContains(response, "ابحث في البرامج وأيام التدريب")
        self.assertContains(response, "مسح البحث")
        self.assertContains(response, "لم يتم العثور على برامج")

    def test_program_list_shows_program_stats_and_add_day_starts_a_new_draft(self):
        plan = self.create_plan()
        PlanExercise.objects.create(plan=plan, exercise=self.exercise)

        response = self.client.get(reverse("plans:list"))

        self.assertContains(response, "Edit program")
        self.assertContains(response, "Add workout day")
        self.assertContains(response, "?new_day=1")
        self.assertEqual(response.context["programs"][0]["day_count"], 1)
        self.assertEqual(response.context["programs"][0]["exercise_count"], 1)

    def test_program_list_shows_named_delete_confirmation_in_english_and_arabic(self):
        plan = self.create_plan()
        plan.name = 'Upper "A" & <B>'
        plan.save(update_fields=["name"])
        delete_url = reverse("plans:delete", args=[plan.pk]) + "?from=programs"

        english = self.client.get(reverse("plans:list"))
        self.assertContains(english, f'href="{delete_url}"')
        self.assertContains(english, 'data-confirm-delete="Delete “Upper &quot;A&quot; &amp; &lt;B&gt;”? Logged sessions are kept."')
        self.assertContains(english, 'id="program-day-delete-dialog"')

        self.client.post(reverse("set_language"), {"language": "ar", "next": "/"})
        arabic = self.client.get(reverse("plans:list"))
        self.assertContains(arabic, 'dir="rtl"')
        self.assertContains(arabic, 'حذف اليوم')
        self.assertContains(arabic, 'هل تريد حذف «Upper &quot;A&quot; &amp; &lt;B&gt;»؟')

    def test_delete_day_from_program_list_requires_ownership_and_csrf(self):
        plan = self.create_plan()
        other_day = WorkoutPlan.objects.create(user=self.user, program=plan.program, name="Pull Day")
        list_url = reverse("plans:list")
        delete_url = reverse("plans:delete", args=[plan.pk]) + "?from=programs"
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.other)
        client.get(list_url)
        token = client.cookies["csrftoken"].value
        self.assertEqual(client.post(delete_url, {"csrfmiddlewaretoken": token}).status_code, 404)

        client.force_login(self.user)
        confirmation = client.get(delete_url)
        self.assertContains(confirmation, plan.name)
        self.assertContains(confirmation, f'<a class="btn btn-secondary" href="{list_url}">Cancel</a>', html=True)
        self.assertEqual(client.post(delete_url).status_code, 403)
        self.assertTrue(WorkoutPlan.objects.filter(pk=plan.pk).exists())

        token = client.cookies["csrftoken"].value
        response = client.post(delete_url, {"csrfmiddlewaretoken": token})
        self.assertRedirects(response, list_url)
        self.assertFalse(WorkoutPlan.objects.filter(pk=plan.pk).exists())
        self.assertTrue(WorkoutPlan.objects.filter(pk=other_day.pk).exists())

    def test_delete_day_from_program_list_preserves_training_history_and_analytics(self):
        from analytics.services import exercise_progress, summary, weekly_volume
        from workouts.services import evaluate_personal_record, finish_session, start_session

        plan = self.create_plan()
        entry = PlanExercise.objects.create(plan=plan, exercise=self.exercise)
        planned_set = PlanSet.objects.create(plan_exercise=entry)
        session = start_session(self.user, plan)
        session_exercise = session.exercises.get()
        logged_set = session_exercise.sets.create(reps_completed=8, weight_kg=40)
        evaluate_personal_record(logged_set)
        finish_session(session, notes="Workout completed", rating=4)
        analytics_before = (summary(self.user), weekly_volume(self.user), exercise_progress(self.user))
        record_ids = list(logged_set.records.values_list("pk", flat=True))

        response = self.client.post(reverse("plans:delete", args=[plan.pk]) + "?from=programs")

        self.assertRedirects(response, reverse("plans:list"))
        self.assertFalse(WorkoutPlan.objects.filter(pk=plan.pk).exists())
        self.assertFalse(PlanSet.objects.filter(pk=planned_set.pk).exists())
        session.refresh_from_db()
        self.assertIsNone(session.plan_id)
        self.assertEqual(session.name, plan.name)
        self.assertEqual(session.notes, "Workout completed")
        self.assertTrue(session.is_finished)
        self.assertEqual(session.exercises.get().pk, session_exercise.pk)
        logged_set.refresh_from_db()
        self.assertTrue(logged_set.is_personal_record)
        self.assertCountEqual(logged_set.records.values_list("pk", flat=True), record_ids)
        stats_before, volume_before, progress_before = analytics_before
        stats_after = summary(self.user)
        self.assertEqual(stats_after.pop("workout_plans"), stats_before.pop("workout_plans") - 1)
        self.assertEqual(stats_after, stats_before)
        self.assertEqual(weekly_volume(self.user), volume_before)
        self.assertEqual(exercise_progress(self.user), progress_before)

    def test_program_list_uses_arabic_singular_counts(self):
        plan = self.create_plan()
        PlanExercise.objects.create(plan=plan, exercise=self.exercise)
        self.client.post(reverse("set_language"), {"language": "ar", "next": "/"})

        response = self.client.get(reverse("plans:list"))

        self.assertContains(response, "1 يوم تدريب")
        self.assertContains(response, "1 تمرين")

    def test_program_builder_renders_existing_day_or_new_draft_without_redirecting(self):
        plan = self.create_plan()
        builder_url = reverse("plans:program_builder", args=[plan.program_id])

        existing_response = self.client.get(builder_url)
        new_day_response = self.client.get(builder_url, {"new_day": "1"})

        self.assertEqual(existing_response.status_code, 200)
        self.assertEqual(existing_response.context["selected_plan_id"], plan.pk)
        self.assertFalse(existing_response.context["start_new_day"])
        self.assertEqual(new_day_response.status_code, 200)
        self.assertEqual(new_day_response.context["selected_plan_id"], "")
        self.assertTrue(new_day_response.context["start_new_day"])

    def test_builder_includes_lazy_local_animation_and_exercise_details(self):
        plan = self.create_plan()
        chest = MuscleGroup.objects.create(name="Chest", body_region=MuscleGroup.BodyRegion.UPPER)
        equipment = Equipment.objects.create(name="Bench")
        ExerciseMuscleGroup.objects.create(
            exercise=self.exercise,
            muscle_group=chest,
            role=ExerciseMuscleGroup.Role.PRIMARY,
        )
        ExerciseEquipment.objects.create(exercise=self.exercise, equipment=equipment)
        self.exercise.description = "A compound movement."
        self.exercise.instructions = "Lower the bar with control."
        self.exercise.save()

        response = self.client.get(reverse("plans:detail", args=[plan.pk]))
        library_item = next(
            item for item in response.context["builder_data"]["exercises"]
            if item["id"] == self.exercise.pk
        )

        self.assertTrue(library_item["animation"].endswith(".gif"))
        self.assertTrue(library_item["thumbnail"].endswith(".webp"))
        self.assertEqual(library_item["description"], "A compound movement.")
        self.assertEqual(library_item["instructions"], "Lower the bar with control.")
        self.assertEqual(library_item["muscles"], [{"name": "Chest", "role": "primary"}])
        self.assertEqual(library_item["equipment"], ["Bench"])

    def test_create_plan(self):
        response = self.client.post(
            reverse("plans:create"),
            {
                "program_name": "Push Program",
                "goal": "hypertrophy",
                "name": "Push Day",
                "description": "",
                "estimated_duration_minutes": 40,
            },
        )
        plan = WorkoutPlan.objects.get(name="Push Day")
        self.assertRedirects(response, reverse("plans:detail", args=[plan.pk]))
        self.assertEqual(plan.user, self.user)
        self.assertEqual(plan.program.name, "Push Program")
        self.assertEqual(plan.program_order, 1)
        self.assertEqual(plan.program.goal, "hypertrophy")
        self.assertEqual(plan.goal, "hypertrophy")

    def test_create_program_form_does_not_require_a_training_split(self):
        response = self.client.get(reverse("plans:create"))

        self.assertContains(response, 'name="program_name"')
        self.assertContains(response, 'name="name"')
        self.assertContains(response, 'name="goal"', count=6)
        self.assertNotContains(response, 'name="split"')

    def test_program_creation_requires_one_of_the_six_goals(self):
        common = {"program_name": "Goal", "name": "Day", "estimated_duration_minutes": 40}
        url = reverse("plans:create")
        self.assertEqual(self.client.post(url, common).status_code, 200)
        self.assertEqual(self.client.post(url, {**common, "goal": "other"}).status_code, 200)
        self.assertFalse(WorkoutProgram.objects.exists())
        for goal, _ in WorkoutPlan.Goal.choices:
            with self.subTest(goal=goal):
                response = self.client.post(url, {**common, "goal": goal})
                self.assertEqual(response.status_code, 302)
                program = WorkoutProgram.objects.get(goal=goal)
                self.assertEqual(program.days.get().goal, goal)
                day = WorkoutPlan.objects.create(user=self.user, program=program, name="Next")
                self.assertEqual(day.goal, goal)

    def test_cardio_draft_inheritance_and_forged_new_day_exercises(self):
        program = WorkoutProgram.objects.create(user=self.user, name="Cardio", goal="cardio")
        bench = Exercise.objects.create(name="Bench Press")
        url = reverse("plans:program_builder", args=[program.pk])
        initial = self.client.get(url, {"new_day": 1}).context["builder_data"]
        self.assertEqual(initial["program"]["goal"], "cardio")
        self.assertIn(self.exercise.pk, initial["cardio_ids"])
        self.assertNotIn(bench.pk, initial["cardio_ids"])
        entry = {"exercise_id": bench.pk, "rest_seconds": 0, "sets": [
            {"reps": 10, "weight_kg": 0, "duration_seconds": 0},
        ]}
        day = {"id": None, "client_key": "new", "name": "New day", "estimated_duration_minutes": 30,
               "goal": "strength", "exercises": [entry]}
        self.assertEqual(self.save_builder(program, {"name": "Cardio", "days": [day]}).status_code, 400)
        self.assertFalse(program.days.exists())
        entry["exercise_id"] = self.exercise.pk
        self.assertEqual(self.save_builder(program, {"name": "Cardio", "days": [day]}).status_code, 200)
        self.assertEqual(program.days.get().goal, "cardio")

    def test_switching_to_cardio_requires_explicit_conflict_resolution(self):
        program = WorkoutProgram.objects.create(user=self.user, name="Training", goal="strength")
        day = WorkoutPlan.objects.create(user=self.user, name="Lifting", program=program)
        bench = Exercise.objects.create(name="Bench Press")
        entry = PlanExercise.objects.create(plan=day, exercise=bench)
        planned = PlanSet.objects.create(plan_exercise=entry)
        saved = self.client.get(reverse("plans:detail", args=[day.pk])).context["builder_data"]["days"][0]
        saved["client_key"] = "saved"
        payload = {"name": program.name, "goal": "cardio", "days": [saved]}

        response = self.save_builder(program, payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Bench Press", response.json()["error"])
        program.refresh_from_db()
        self.assertEqual(program.goal, "strength")
        self.assertTrue(PlanSet.objects.filter(pk=planned.pk).exists())
        saved["exercises"] = []
        self.assertEqual(self.save_builder(program, payload).status_code, 200)
        day.refresh_from_db()
        self.assertEqual(day.goal, "cardio")

    def test_stale_builder_save_preserves_a_newer_day_and_normalized_names(self):
        plan = self.create_plan()
        stale_revision = program_revision(plan.program)
        initial_day = {"id": plan.pk, "client_key": "initial", "name": "  Renamed  ",
                       "description": "Notes", "estimated_duration_minutes": 35, "exercises": []}
        new_day = {**initial_day, "id": None, "client_key": "new", "name": "Extra day"}
        response = self.save_builder(plan.program, {"name": "  New title  ", "days": [initial_day, new_day]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["program_name"], "New title")
        self.assertEqual(response.json()["records"]["initial"]["name"], "Renamed")
        stale = {"revision": stale_revision, "name": "Old copy", "days": [initial_day]}
        self.assertEqual(self.save_builder(plan.program, stale).status_code, 409)
        self.assertEqual(plan.program.days.count(), 2)

    def test_builder_rejects_empty_new_exercise_set_list(self):
        plan = self.create_plan()
        exercise = {"exercise_id": self.exercise.pk, "rest_seconds": 0, "sets": []}
        days = [{"id": plan.pk, "client_key": "day", "name": plan.name,
                 "estimated_duration_minutes": 40, "exercises": [exercise]}]
        self.assertEqual(self.save_builder(plan.program, {"name": plan.program.name, "days": days}).status_code, 400)
        self.assertFalse(plan.exercises.exists())

    def test_legacy_route_cannot_remove_the_last_planned_set(self):
        plan = self.create_plan()
        entry = PlanExercise.objects.create(plan=plan, exercise=self.exercise)
        item = PlanSet.objects.create(plan_exercise=entry)
        self.assertRedirects(self.client.post(reverse("plans:delete_set", args=[item.pk])),
                             reverse("plans:detail", args=[plan.pk]))
        self.assertTrue(entry.sets.filter(pk=item.pk).exists())

    def test_builder_saves_multiple_days_exercises_custom_sets_and_zero_rest(self):
        plan = self.create_plan()
        resistance = Exercise.objects.create(name="Bench Press")
        payload = {
            "name": "Custom program",
            "days": [
                {
                    "id": plan.pk,
                    "client_key": f"day-{plan.pk}",
                    "name": "Upper body",
                    "description": "First saved day",
                    "estimated_duration_minutes": 55,
                    "exercises": [
                        {
                            "exercise_id": self.exercise.pk,
                            "rest_seconds": 0,
                            "notes": "Keep the reps controlled.",
                            "sets": [
                                {"id": None, "reps": 12, "duration_seconds": 0, "weight_kg": 0, "set_type": "normal"},
                                {"id": None, "reps": 10, "duration_seconds": 0, "weight_kg": 0, "set_type": "warmup"},
                                {"id": None, "reps": 8, "duration_seconds": 0, "weight_kg": 0, "set_type": "failure"},
                            ],
                        },
                        {
                            "exercise_id": resistance.pk,
                            "rest_seconds": 90,
                            "notes": "",
                            "sets": [
                                {"id": None, "reps": 8, "duration_seconds": 0, "weight_kg": 40, "set_type": "drop_set"},
                            ],
                        },
                    ],
                },
                {
                    "id": None,
                    "client_key": "new-day",
                    "name": "Cardio finish",
                    "description": "",
                    "estimated_duration_minutes": 25,
                    "exercises": [],
                },
            ],
        }

        response = self.save_builder(plan.program, payload)

        self.assertEqual(response.status_code, 200, response.content)
        plan.refresh_from_db()
        plan.program.refresh_from_db()
        self.assertEqual(plan.program.name, "Custom program")
        self.assertEqual(plan.name, "Upper body")
        self.assertEqual(plan.program_order, 1)
        self.assertEqual(plan.exercises.count(), 2)
        bodyweight_entry = plan.exercises.get(exercise=self.exercise)
        self.assertEqual(bodyweight_entry.rest_seconds, 0)
        self.assertEqual(bodyweight_entry.notes, "Keep the reps controlled.")
        self.assertEqual(
            list(bodyweight_entry.sets.values_list("set_number", "reps", "set_type")),
            [(1, 12, "normal"), (2, 10, "warmup"), (3, 8, "failure")],
        )
        resistance_entry = plan.exercises.get(exercise=resistance)
        self.assertEqual(resistance_entry.sets.get().weight_kg, 40)
        new_day = plan.program.days.get(program_order=2)
        self.assertEqual(new_day.name, "Cardio finish")
        self.assertEqual(response.json()["days"]["new-day"], new_day.pk)

    def test_builder_preserves_customized_existing_sets_when_saving(self):
        plan = self.create_plan()
        entry = PlanExercise.objects.create(plan=plan, exercise=self.exercise, order=1, rest_seconds=0)
        set_obj = PlanSet.objects.create(
            plan_exercise=entry,
            set_number=4,
            reps=7,
            duration_seconds=20,
            weight_kg=17.5,
            set_type=PlanSet.SetType.DROP_SET,
        )

        response = self.save_builder(
            plan.program,
            {
                "name": plan.program.name,
                "days": [
                    {
                        "id": plan.pk,
                        "client_key": f"day-{plan.pk}",
                        "name": plan.name,
                        "description": "",
                        "estimated_duration_minutes": plan.estimated_duration_minutes,
                        "exercises": [
                            {
                                "exercise_id": self.exercise.pk,
                                "rest_seconds": 0,
                                "notes": "",
                                "sets": [
                                    {
                                        "id": set_obj.pk,
                                        "reps": 7,
                                        "duration_seconds": 20,
                                        "weight_kg": 17.5,
                                        "set_type": "drop_set",
                                    }
                                ],
                            }
                        ],
                    }
                ],
            },
        )

        self.assertEqual(response.status_code, 200, response.content)
        set_obj.refresh_from_db()
        self.assertEqual(set_obj.pk, response.json()["records"][f"day-{plan.pk}"]["exercises"][str(self.exercise.pk)]["sets"][0])
        self.assertEqual((set_obj.set_number, set_obj.reps, set_obj.duration_seconds, set_obj.weight_kg, set_obj.set_type), (1, 7, 20, 17.5, "drop_set"))

    def test_invalid_builder_payload_rolls_back_all_program_changes(self):
        plan = self.create_plan()
        response = self.save_builder(
            plan.program,
            {
                "name": "Should not persist",
                "days": [
                    {
                        "id": plan.pk,
                        "client_key": f"day-{plan.pk}",
                        "name": "Changed day",
                        "description": "",
                        "estimated_duration_minutes": 45,
                        "exercises": [
                            {
                                "exercise_id": self.exercise.pk,
                                "rest_seconds": 90,
                                "notes": "",
                                "sets": [],
                            },
                            {
                                "exercise_id": self.exercise.pk,
                                "rest_seconds": 90,
                                "notes": "",
                                "sets": [],
                            },
                        ],
                    }
                ],
            },
        )

        self.assertEqual(response.status_code, 400)
        plan.refresh_from_db()
        plan.program.refresh_from_db()
        self.assertEqual(plan.name, "Push Day")
        self.assertEqual(plan.program.name, "My Program")

    def test_builder_rejects_programs_owned_by_another_user(self):
        plan = self.create_plan()
        self.client.login(username="other", password="pw12345678")

        response = self.save_builder(plan.program, {"name": "No access", "days": []})

        self.assertEqual(response.status_code, 404)

    def test_saved_builder_day_can_start_a_session(self):
        from workouts.models import SessionExercise, WorkoutSession

        plan = self.create_plan()
        response = self.save_builder(
            plan.program,
            {
                "name": plan.program.name,
                "days": [
                    {
                        "id": plan.pk,
                        "client_key": f"day-{plan.pk}",
                        "name": plan.name,
                        "description": "",
                        "estimated_duration_minutes": 45,
                        "exercises": [
                            {
                                "exercise_id": self.exercise.pk,
                                "rest_seconds": 90,
                                "notes": "",
                                "sets": [
                                    {"id": None, "reps": 10, "duration_seconds": 0, "weight_kg": 0, "set_type": "normal"},
                                ],
                            }
                        ],
                    }
                ],
            },
        )
        self.assertEqual(response.status_code, 200)

        start_response = self.client.post(reverse("workouts:start", args=[plan.pk]))
        session = WorkoutSession.objects.get(plan=plan)

        self.assertRedirects(start_response, reverse("workouts:active", args=[session.pk]))
        self.assertEqual(SessionExercise.objects.filter(session=session, exercise=self.exercise).count(), 1)

    def test_removing_a_saved_day_keeps_session_history(self):
        from workouts.models import SessionExercise, WorkoutSession

        plan = self.create_plan()
        PlanExercise.objects.create(plan=plan, exercise=self.exercise, order=1)
        self.client.post(reverse("workouts:start", args=[plan.pk]))
        session = WorkoutSession.objects.get(plan=plan)
        saved_session_exercise_id = session.exercises.get().pk

        response = self.save_builder(plan.program, {"name": plan.program.name, "days": []})

        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(WorkoutPlan.objects.filter(pk=plan.pk).exists())
        session.refresh_from_db()
        self.assertIsNone(session.plan_id)
        self.assertTrue(SessionExercise.objects.filter(pk=saved_session_exercise_id, session=session).exists())

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

    def test_cardio_plan_shows_cardio_machines_and_conditioning_only(self):
        plan = WorkoutPlan.objects.create(user=self.user, name="Cardio Day", goal=WorkoutPlan.Goal.CARDIO)
        cardio_names = (
            "Treadmill",
            "Elliptical Machine",
            "Stationary Bike",
            "Rowing Machine",
            "Burpee",
            "Jumping Jack",
            "Mountain Climber",
            "High Knees Lift Run",
        )
        for name in cardio_names:
            Exercise.objects.create(name=name, exercise_type=Exercise.ExerciseType.CARDIO)
        plank = Exercise.objects.create(name="Plank")
        resistance_exercises = [
            Exercise.objects.create(name=name)
            for name in ("Bench Press", "Biceps Curl", "Leg Press")
        ]

        response = self.client.get(reverse("plans:detail", args=[plan.pk]))
        categories = response.context["exercise_categories"]
        visible_names = {
            exercise.name
            for category in categories
            for exercise in category["exercises"]
        }
        visible_names.update(
            exercise.name
            for category in categories
            for group in category["groups"]
            for exercise in group["exercises"]
        )

        self.assertEqual(visible_names, {"Push-up", plank.name, *cardio_names})
        self.assertTrue(all(category["exercise_count"] > 0 for category in categories))
        cardio_category = next(category for category in categories if category["key"] == "cardio")
        self.assertEqual(
            {exercise.name for exercise in cardio_category["exercises"]},
            {"Treadmill", "Elliptical Machine", "Stationary Bike", "Rowing Machine"},
        )
        self.assertEqual(
            {exercise.name for exercise in cardio_category["groups"][0]["exercises"]},
            {"Push-up", "Plank", "Burpee", "Jumping Jack", "Mountain Climber", "High Knees Lift Run"},
        )
        self.assertEqual(plank.exercise_type, Exercise.ExerciseType.STRENGTH)
        self.assertEqual(
            set(AddExerciseForm(plan=plan).fields["exercise"].queryset.values_list("name", flat=True)),
            visible_names,
        )
        for exercise in resistance_exercises:
            self.assertNotContains(response, f'value="{exercise.pk}"')

    def test_cardio_plan_rejects_resistance_exercise_submission(self):
        plan = WorkoutPlan.objects.create(user=self.user, name="Cardio Day", goal=WorkoutPlan.Goal.CARDIO)
        bench_press = Exercise.objects.create(name="Bench Press")

        response = self.client.post(
            reverse("plans:detail", args=[plan.pk]),
            {"exercise": bench_press.pk, "order": 1, "rest_seconds": 90},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(PlanExercise.objects.filter(plan=plan, exercise=bench_press).exists())
        self.assertContains(response, "Select a valid choice")

    def test_non_cardio_goals_keep_all_active_exercises(self):
        Exercise.objects.create(name="Bench Press")
        Exercise.objects.create(name="Treadmill", exercise_type=Exercise.ExerciseType.CARDIO)
        expected = set(Exercise.objects.filter(is_active=True).values_list("name", flat=True))

        for goal, _label in WorkoutPlan.Goal.choices:
            if goal == WorkoutPlan.Goal.CARDIO:
                continue
            with self.subTest(goal=goal):
                plan = WorkoutPlan.objects.create(user=self.user, name=f"{goal} Plan", goal=goal)
                available = set(
                    AddExerciseForm(plan=plan).fields["exercise"].queryset.values_list("name", flat=True)
                )
                self.assertEqual(available, expected)

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
        builder_exercises = response.context["builder_data"]["exercises"]
        self.assertIn(core_primary.pk, {item["id"] for item in builder_exercises})
        self.assertIn(unlinked.pk, {item["id"] for item in builder_exercises})
        self.assertIn(self.exercise.local_thumbnail_url, response.content.decode())
        self.assertContains(response, 'class="builder-library-list"')

    def test_selected_plan_exercise_uses_a_static_thumbnail(self):
        plan = self.create_plan()
        PlanExercise.objects.create(plan=plan, exercise=self.exercise, order=1)

        response = self.client.get(reverse("plans:detail", args=[plan.pk]))

        exercise_data = response.context["builder_data"]["days"][0]["exercises"][0]
        self.assertEqual(exercise_data["thumbnail"], self.exercise.local_thumbnail_url)
        self.assertNotEqual(exercise_data["thumbnail"], self.exercise.local_image_url)

    def test_inactive_saved_exercise_remains_editable_outside_the_catalog(self):
        plan = self.create_plan()
        entry = PlanExercise.objects.create(plan=plan, exercise=self.exercise)
        saved_set = PlanSet.objects.create(plan_exercise=entry, reps=8)
        self.exercise.is_active = False
        self.exercise.save(update_fields=["is_active"])

        response = self.client.get(reverse("plans:detail", args=[plan.pk]))
        data = response.context["builder_data"]
        self.assertNotIn(self.exercise.pk, {item["id"] for item in data["exercises"]})
        self.assertEqual(data["retired_exercises"][0]["id"], self.exercise.pk)
        self.assertEqual(data["retired_exercises"][0]["animation"], self.exercise.local_image_url)
        day = data["days"][0]
        day["client_key"] = "saved-day"
        day["exercises"][0]["sets"][0]["reps"] = 12
        payload = {"name": plan.program.name, "days": [day]}

        response = self.save_builder(plan.program, payload)
        self.assertEqual(response.status_code, 200, response.content)
        saved_set.refresh_from_db()
        self.assertEqual(saved_set.reps, 12)

        day["exercises"][0]["removed_set_ids"] = [saved_set.pk]
        response = self.save_builder(plan.program, payload)
        self.assertEqual(response.status_code, 400, response.content)
        saved_set.refresh_from_db()
        self.assertEqual(saved_set.reps, 12)

    def test_already_added_exercise_is_not_offered_again(self):
        plan = self.create_plan()
        PlanExercise.objects.create(plan=plan, exercise=self.exercise, order=4, rest_seconds=45)

        response = self.client.get(reverse("plans:detail", args=[plan.pk]))

        self.assertContains(response, '"exercise_id": %s' % self.exercise.pk)
        self.assertContains(response, 'data-added="Added"')
        self.assertNotIn(
            self.exercise.pk,
            AddExerciseForm(plan=plan).fields["exercise"].queryset.values_list("pk", flat=True),
        )

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

        self.assertEqual(response.context["builder_data"]["exercises"][0]["category"], "الجزء العلوي")
        self.assertEqual(response.context["builder_data"]["exercises"][0]["group"], "الصدر")
        self.assertEqual(response.context["builder_data"]["exercises"][0]["name"], "تمرين الضغط")
        self.assertContains(response, "ابحث عن تمارين بالإنجليزية أو العربية")
        self.assertNotContains(response, 'name="order"')
        self.assertNotContains(response, 'name="set_number"')
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


class ProgramGoalMigrationTests(TransactionTestCase):
    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_consistent_goals_are_derived_and_mixed_goals_survive_reversal(self):
        old = [("plans", "0002_workoutprogram_and_day_order")]
        new = [("plans", "0003_workoutprogram_goal")]
        executor = MigrationExecutor(connection)
        executor.migrate(old)
        apps = executor.loader.project_state(old).apps
        user = apps.get_model("accounts", "User").objects.create(username="legacy-goals")
        Program = apps.get_model("plans", "WorkoutProgram")
        Day = apps.get_model("plans", "WorkoutPlan")
        consistent = Program.objects.create(user=user, name="Consistent")
        mixed = Program.objects.create(user=user, name="Mixed")
        empty = Program.objects.create(user=user, name="Empty")
        Day.objects.create(user=user, program=consistent, name="Run", goal="cardio")
        Day.objects.create(user=user, program=mixed, name="Lift", goal="strength")
        Day.objects.create(user=user, program=mixed, name="Condition", goal="cardio")
        before = list(Day.objects.order_by("pk").values_list("pk", "program_id", "goal"))

        executor = MigrationExecutor(connection)
        executor.migrate(new)
        migrated = executor.loader.project_state(new).apps
        Program = migrated.get_model("plans", "WorkoutProgram")
        self.assertEqual(Program.objects.get(pk=consistent.pk).goal, "cardio")
        self.assertIsNone(Program.objects.get(pk=mixed.pk).goal)
        self.assertIsNone(Program.objects.get(pk=empty.pk).goal)
        executor = MigrationExecutor(connection)
        executor.migrate(old)
        Day = executor.loader.project_state(old).apps.get_model("plans", "WorkoutPlan")
        self.assertEqual(list(Day.objects.order_by("pk").values_list("pk", "program_id", "goal")), before)


class WorkoutProgramMigrationTests(TransactionTestCase):
    migrate_from = [("plans", "0001_initial")]
    migrate_to = [("plans", "0002_workoutprogram_and_day_order")]

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_existing_plan_and_sets_are_preserved_and_grouped(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_from)
        old_apps = executor.loader.project_state(self.migrate_from).apps
        User = old_apps.get_model("accounts", "User")
        Exercise = old_apps.get_model("exercises", "Exercise")
        WorkoutPlan = old_apps.get_model("plans", "WorkoutPlan")
        PlanExercise = old_apps.get_model("plans", "PlanExercise")
        PlanSet = old_apps.get_model("plans", "PlanSet")

        user = User.objects.create(username="legacy-migration-user", password="not-used")
        exercise = Exercise.objects.create(name="Legacy Press")
        plan = WorkoutPlan.objects.create(user=user, name="Legacy Workout", goal="strength")
        plan_exercise = PlanExercise.objects.create(
            plan=plan,
            exercise=exercise,
            order=3,
            rest_seconds=0,
        )
        planned_set = PlanSet.objects.create(
            plan_exercise=plan_exercise,
            set_number=2,
            reps=8,
            weight_kg=25,
        )

        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_to)
        new_apps = executor.loader.project_state(self.migrate_to).apps
        NewWorkoutPlan = new_apps.get_model("plans", "WorkoutPlan")
        NewWorkoutProgram = new_apps.get_model("plans", "WorkoutProgram")
        NewPlanExercise = new_apps.get_model("plans", "PlanExercise")
        NewPlanSet = new_apps.get_model("plans", "PlanSet")
        saved_plan = NewWorkoutPlan.objects.get(pk=plan.pk)

        self.assertEqual(saved_plan.program.user_id, user.pk)
        self.assertEqual(saved_plan.program.name, "My Program")
        self.assertEqual(saved_plan.program_order, 1)
        self.assertEqual(saved_plan.name, "Legacy Workout")
        saved_entry = NewPlanExercise.objects.get(pk=plan_exercise.pk)
        self.assertEqual((saved_entry.exercise_id, saved_entry.rest_seconds), (exercise.pk, 0))
        saved_set = NewPlanSet.objects.get(pk=planned_set.pk)
        self.assertEqual((saved_set.set_number, saved_set.reps, saved_set.weight_kg), (2, 8, 25))
        self.assertEqual(NewWorkoutProgram.objects.count(), 1)
