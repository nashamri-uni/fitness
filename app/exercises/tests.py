"""Tests for the exercise library (FREQ-3, FREQ-14, FREQ-15)."""
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from django.urls import reverse

from accounts.models import User
from plans.models import PlanExercise, WorkoutPlan
from workouts.models import SessionExercise, WorkoutSession

from .management.commands.seed_data import (
    EQUIPMENT,
    EXERCISES,
    EXERCISE_IMAGES,
    MUSCLE_GROUPS,
    RETIRED_EXERCISES,
)
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

    def test_library_and_detail_render_only_existing_local_images(self):
        image_path = EXERCISE_IMAGES["Incline Dumbbell Press"]
        exercise = Exercise.objects.create(
            name="Incline Dumbbell Press",
            image=image_path,
        )

        self.assertTrue(exercise.local_image_url)
        self.assertTrue(exercise.local_image_url.startswith("/"))
        self.assertTrue(exercise.local_image_url.endswith(".gif"))
        self.assertTrue(exercise.local_thumbnail_url.endswith(".webp"))
        detail_response = self.client.get(reverse("exercises:detail", args=[exercise.pk]))
        library_response = self.client.get(reverse("exercises:library"), {"q": exercise.name})
        self.assertContains(detail_response, f'src="{exercise.local_image_url}"')
        self.assertContains(library_response, f'src="{exercise.local_thumbnail_url}"')
        self.assertNotContains(library_response, f'src="{exercise.local_image_url}"')

        exercise.image = "https://example.invalid/exercise.gif"
        exercise.save(update_fields=["image"])
        self.assertEqual(exercise.local_image_url, "")
        self.assertEqual(exercise.local_thumbnail_url, "")
        external_response = self.client.get(reverse("exercises:detail", args=[exercise.pk]))
        self.assertNotContains(external_response, "https://example.invalid")
        self.assertNotContains(external_response, "<img")

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


class SeedDataTests(TestCase):
    def run_seed(self):
        call_command("seed_data", stdout=StringIO())

    def test_seed_catalogue_is_complete_idempotent_and_correctly_linked(self):
        self.run_seed()

        self.assertEqual(len(EXERCISES), 128)
        self.assertEqual(Exercise.objects.count(), 128)
        self.assertEqual(Exercise.objects.values("name").distinct().count(), 128)
        self.assertEqual(Exercise.objects.filter(is_active=True).count(), 111)
        self.assertEqual(
            set(Exercise.objects.filter(is_active=False).values_list("name", flat=True)),
            RETIRED_EXERCISES,
        )
        self.assertEqual(
            dict(Exercise.objects.filter(name__in=EXERCISE_IMAGES).values_list("name", "image")),
            EXERCISE_IMAGES,
        )
        self.assertTrue(
            all(
                Exercise.objects.get(name=name).local_image_url
                and Exercise.objects.get(name=name).local_thumbnail_url
                for name in EXERCISE_IMAGES
            )
        )
        self.assertFalse(
            [
                exercise.name
                for exercise in Exercise.objects.filter(is_active=True)
                if not exercise.local_image_url or not exercise.local_thumbnail_url
            ]
        )
        self.assertIn("Dead Bug", EXERCISE_IMAGES)
        self.assertEqual(
            dict(Exercise.objects.values_list("name", "name_ar")),
            {name: name_ar for name, name_ar, *_ in EXERCISES},
        )
        self.assertEqual(
            dict(MuscleGroup.objects.values_list("name", "name_ar")),
            {name: name_ar for name, _, name_ar in MUSCLE_GROUPS},
        )
        self.assertEqual(
            dict(Equipment.objects.values_list("name", "name_ar")),
            {name: name_ar for name, name_ar in EQUIPMENT},
        )
        self.assertEqual(
            Exercise.objects.get(name="Flat Dumbbell Bench Press").name_ar,
            "بنش مستوٍ بالدمبل",
        )
        self.assertEqual(
            list(
                Exercise.objects.get(name="Flat Dumbbell Bench Press")
                .muscle_links.filter(role=ExerciseMuscleGroup.Role.PRIMARY)
                .values_list("muscle_group__name", flat=True)
            ),
            ["Chest"],
        )
        self.assertEqual(
            list(
                Exercise.objects.get(name="Treadmill Run")
                .equipment_links.values_list("equipment__name", flat=True)
            ),
            ["Treadmill"],
        )
        self.assertEqual(
            list(
                Exercise.objects.get(name="Hip Adduction Machine")
                .muscle_links.filter(role=ExerciseMuscleGroup.Role.PRIMARY)
                .values_list("muscle_group__name", flat=True)
            ),
            ["Adductors"],
        )
        self.assertEqual(
            Exercise.objects.get(name="Battle Rope").exercise_type,
            Exercise.ExerciseType.CARDIO,
        )
        self.assertEqual(
            Exercise.objects.get(name="Jumping Jack").exercise_type,
            Exercise.ExerciseType.CARDIO,
        )
        self.assertEqual(
            Exercise.objects.get(name="High Knees Lift Run").exercise_type,
            Exercise.ExerciseType.CARDIO,
        )
        self.assertEqual(
            Exercise.objects.get(name="Incline Treadmill Run").exercise_type,
            Exercise.ExerciseType.CARDIO,
        )
        self.assertEqual(
            Exercise.objects.get(name="Bicycle Crunch").exercise_type,
            Exercise.ExerciseType.STRENGTH,
        )
        self.assertEqual(
            {
                exercise_type: Exercise.objects.filter(
                    is_active=True,
                    exercise_type=exercise_type,
                ).count()
                for exercise_type in Exercise.ExerciseType.values
            },
            {"strength": 96, "cardio": 14, "flexibility": 1, "balance": 0},
        )
        self.assertEqual(
            {
                group.name: ExerciseMuscleGroup.objects.filter(
                    exercise__is_active=True,
                    muscle_group=group,
                    role=ExerciseMuscleGroup.Role.PRIMARY,
                ).count()
                for group in MuscleGroup.objects.all()
            },
            {
                "Adductors": 1,
                "Back": 15,
                "Biceps": 9,
                "Calves": 5,
                "Chest": 11,
                "Core": 14,
                "Forearms": 1,
                "Glutes": 7,
                "Hamstrings": 7,
                "Quadriceps": 21,
                "Shoulders": 13,
                "Triceps": 7,
            },
        )
        self.assertEqual(MuscleGroup.objects.get(name="Shoulders").name_ar, "الأكتاف")

        exercise_id = Exercise.objects.get(name="Flat Dumbbell Bench Press").pk
        muscle_link_count = ExerciseMuscleGroup.objects.count()
        equipment_link_count = ExerciseEquipment.objects.count()
        self.run_seed()

        self.assertEqual(Exercise.objects.count(), 128)
        self.assertEqual(Exercise.objects.filter(is_active=True).count(), 111)
        self.assertEqual(Exercise.objects.get(name="Flat Dumbbell Bench Press").pk, exercise_id)
        self.assertEqual(ExerciseMuscleGroup.objects.count(), muscle_link_count)
        self.assertEqual(ExerciseEquipment.objects.count(), equipment_link_count)

    def test_seed_soft_retires_niche_exercises_without_deleting_history(self):
        self.run_seed()
        exercise = Exercise.objects.get(name="Turkish Get-Up")
        exercise_id = exercise.pk
        owner = User.objects.create_user(username="retiredowner", password="pw12345678")
        plan = WorkoutPlan.objects.create(user=owner, name="Historic plan")
        plan_entry = PlanExercise.objects.create(plan=plan, exercise=exercise, order=1)
        session = WorkoutSession.objects.create(
            user=owner,
            plan=plan,
            name="Historic session",
            started_at=timezone.now(),
        )
        session_entry = SessionExercise.objects.create(session=session, exercise=exercise, order=1)

        self.run_seed()

        exercise.refresh_from_db()
        self.assertEqual(exercise.pk, exercise_id)
        self.assertFalse(exercise.is_active)
        self.assertEqual(plan_entry.exercise_id, exercise_id)
        self.assertEqual(session_entry.exercise_id, exercise_id)

    def test_seed_updates_known_seed_rows_without_breaking_plan_or_session_history(self):
        owner = User.objects.create_user(username="seedowner", password="pw12345678")
        chest = MuscleGroup.objects.create(name="Chest", body_region="upper", name_ar="الصدر")
        back = MuscleGroup.objects.create(name="Back", body_region="upper", name_ar="الظهر")
        shoulders = MuscleGroup.objects.create(name="Shoulders", body_region="upper", name_ar="الكتف")
        exercise = Exercise.objects.create(
            name="Barbell Bench Press",
            name_ar="ضغط البار على المقعد",
            description="Barbell Bench Press (strength, intermediate).",
            instructions="Old seed instructions.",
            exercise_type="strength",
            difficulty="intermediate",
        )
        ExerciseMuscleGroup.objects.create(
            exercise=exercise, muscle_group=back, role=ExerciseMuscleGroup.Role.PRIMARY
        )
        plan = WorkoutPlan.objects.create(user=owner, name="Historic plan")
        plan_entry = PlanExercise.objects.create(plan=plan, exercise=exercise, order=1)
        session = WorkoutSession.objects.create(
            user=owner,
            plan=plan,
            name="Historic session",
            started_at=timezone.now(),
        )
        session_entry = SessionExercise.objects.create(session=session, exercise=exercise, order=1)
        exercise_id = exercise.pk
        shoulders_id = shoulders.pk

        self.run_seed()

        exercise.refresh_from_db()
        self.assertEqual(exercise.pk, exercise_id)
        self.assertEqual(exercise.name_ar, "بنش برس بالبار")
        self.assertEqual(plan_entry.exercise_id, exercise_id)
        self.assertEqual(session_entry.exercise_id, exercise_id)
        self.assertTrue(WorkoutSession.objects.filter(pk=session.pk, plan=plan).exists())
        self.assertEqual(
            list(
                exercise.muscle_links.filter(role=ExerciseMuscleGroup.Role.PRIMARY)
                .values_list("muscle_group__name", flat=True)
            ),
            ["Chest"],
        )
        self.assertEqual(MuscleGroup.objects.get(pk=shoulders_id).name_ar, "الأكتاف")

    def test_seed_does_not_overwrite_a_user_created_exercise_with_a_catalogue_name(self):
        admin = User.objects.create_user(username="exerciseadmin", password="pw12345678")
        custom = Exercise.objects.create(
            name="Incline Dumbbell Press",
            name_ar="اسمي الخاص",
            description="User-authored description.",
            instructions="User-authored instructions.",
            exercise_type="balance",
            difficulty="advanced",
            created_by=admin,
            image="custom/exercise.gif",
        )
        custom_id = custom.pk

        self.run_seed()

        custom.refresh_from_db()
        self.assertEqual(custom.pk, custom_id)
        self.assertEqual(custom.image, "custom/exercise.gif")
        self.assertEqual(custom.name_ar, "اسمي الخاص")
        self.assertEqual(custom.description, "User-authored description.")
        self.assertEqual(custom.instructions, "User-authored instructions.")
        self.assertEqual(custom.exercise_type, "balance")
        self.assertEqual(custom.difficulty, "advanced")
        self.assertFalse(custom.muscle_links.exists())
        self.assertFalse(custom.equipment_links.exists())
