from django.db import migrations, models


def snapshot_active_sessions(apps, schema_editor):
    SessionExercise = apps.get_model("workouts", "SessionExercise")
    PlanExercise = apps.get_model("plans", "PlanExercise")
    database = schema_editor.connection.alias
    entries = (
        SessionExercise.objects.using(database)
        .filter(session__ended_at__isnull=True)
        .select_related("session")
    )
    for entry in entries.iterator():
        planned = (
            PlanExercise.objects.using(database)
            .filter(plan_id=entry.session.plan_id, exercise_id=entry.exercise_id)
            .first()
        )
        entry.targets = {
            "rest_seconds": planned.rest_seconds if planned else 0,
            "sets": [
                {
                    "set_number": number,
                    "reps_completed": item.reps,
                    "weight_kg": item.weight_kg,
                    "duration_seconds": item.duration_seconds,
                }
                for number, item in enumerate(planned.sets.all(), start=1)
            ] if planned else [],
        }
        entry.save(using=database, update_fields=["targets"])


class Migration(migrations.Migration):
    dependencies = [
        ("plans", "0002_workoutprogram_and_day_order"),
        ("workouts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="sessionexercise",
            name="targets",
            field=models.JSONField(blank=True, db_column="Targets", null=True, verbose_name="Workout targets"),
        ),
        migrations.RunPython(snapshot_active_sessions, migrations.RunPython.noop),
    ]
