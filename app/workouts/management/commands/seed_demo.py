"""Create a sample user with a plan, logged sessions and personal records.

Usage:
    python manage.py seed_demo                       # user "demo"
    python manage.py seed_demo --user nasser         # existing user, keeps its password
    python manage.py seed_demo --user nasser --password 123123
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User, UserProfile
from exercises.models import Exercise
from plans.models import PlanExercise, PlanSet, WorkoutPlan
from workouts.models import SessionExercise, SessionSet, WorkoutSession
from workouts.services import evaluate_personal_record

DEMO_USER = "demo"
DEMO_PASSWORD = "demo12345678"

# exercise name -> (starting weight, weekly increase)
PROGRESSION = {
    "Barbell Bench Press": (60, 2.5),
    "Back Squat": (80, 5),
    "Romanian Deadlift": (100, 5),
    "Pull-up": (0, 0),
}


class Command(BaseCommand):
    help = "Create a sample user with a workout plan and 10 weeks of logged sessions."

    def add_arguments(self, parser):
        parser.add_argument("--user", default=DEMO_USER, help="Username to seed (created if it does not exist).")
        parser.add_argument("--password", default=DEMO_PASSWORD, help="Password used only when the user is created.")

    def handle(self, *args, **options):
        username = options["user"]
        password = options["password"]

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": f"{username}@example.com",
                "first_name": username.capitalize(),
                "last_name": "Sample",
                "role": User.Role.USER,
            },
        )
        if created:
            user.set_password(password)
            user.save()
            UserProfile.objects.create(user=user, fitness_goal="strength", height_cm=178, weight_kg=82)
        else:
            UserProfile.objects.get_or_create(user=user)

        plan, _ = WorkoutPlan.objects.get_or_create(
            user=user,
            name=username,
            defaults={"goal": "strength", "estimated_duration_minutes": 60},
        )

        entries = {}
        for name in PROGRESSION:
            exercise = Exercise.objects.filter(name=name).first()
            if exercise is None:
                continue
            entry, _ = PlanExercise.objects.get_or_create(
                plan=plan, exercise=exercise, defaults={"order": len(entries) + 1, "rest_seconds": 180}
            )
            entries[name] = entry
            if not entry.sets.exists():
                for set_number in range(1, 4):
                    start, weekly_gain = PROGRESSION[name]
                    PlanSet.objects.create(
                        plan_exercise=entry,
                        set_number=set_number,
                        reps=10 - set_number + 1,
                        weight_kg=start + weekly_gain * 4,
                        set_type="normal",
                    )

        if not WorkoutSession.objects.filter(user=user).exists():
            now = timezone.now()
            for week in range(9, -1, -1):
                day = now - timedelta(weeks=week, days=1)
                session = WorkoutSession.objects.create(
                    user=user,
                    plan=plan,
                    name=f"{day:%Y-%m-%d}",
                    started_at=day,
                    ended_at=day + timedelta(minutes=62),
                    duration_minutes=62,
                    rating=4 if week > 3 else 5,
                    notes="",
                )
                for name, entry in entries.items():
                    start, weekly_gain = PROGRESSION[name]
                    weight = start + weekly_gain * (10 - week)
                    session_entry = SessionExercise.objects.create(
                        session=session, exercise=entry.exercise, order=entry.order
                    )
                    for set_number in range(1, 4):
                        set_obj = SessionSet.objects.create(
                            session_exercise=session_entry,
                            set_number=set_number,
                            reps_completed=max(5, 11 - set_number - (week // 3)),
                            weight_kg=weight,
                            duration_seconds=45,
                            rpe=min(10, 6 + (10 - week) // 2),
                        )
                        evaluate_personal_record(set_obj)

        # One in-progress session so the active-session page has something to show.
        active = WorkoutSession.objects.filter(user=user, ended_at__isnull=True).order_by("-started_at").first()
        if active is None:
            started = timezone.now() - timedelta(minutes=35)
            active = WorkoutSession.objects.create(
                user=user,
                plan=plan,
                name=f"{timezone.now():%Y-%m-%d}",
                started_at=started,
            )
            for name, entry in entries.items():
                start, weekly_gain = PROGRESSION[name]
                session_entry = SessionExercise.objects.create(
                    session=active, exercise=entry.exercise, order=entry.order
                )
                set_obj = SessionSet.objects.create(
                    session_exercise=session_entry,
                    set_number=1,
                    reps_completed=10,
                    weight_kg=start + weekly_gain * 10,
                    duration_seconds=45,
                    rpe=9,
                )
                evaluate_personal_record(set_obj)

        self.stdout.write(
            f"Seeded '{username}': {WorkoutSession.objects.filter(user=user).count()} sessions, "
            f"{SessionSet.objects.filter(session_exercise__session__user=user).count()} logged sets, "
            f"{WorkoutPlan.objects.filter(user=user).count()} plan(s)."
        )
