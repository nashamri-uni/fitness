import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def group_existing_plans(apps, schema_editor):
    WorkoutPlan = apps.get_model("plans", "WorkoutPlan")
    WorkoutProgram = apps.get_model("plans", "WorkoutProgram")
    database = schema_editor.connection.alias

    user_ids = (
        WorkoutPlan.objects.using(database)
        .order_by()
        .values_list("user_id", flat=True)
        .distinct()
    )
    for user_id in user_ids:
        program = WorkoutProgram.objects.using(database).create(
            user_id=user_id,
            name="My Program",
        )
        plans = WorkoutPlan.objects.using(database).filter(user_id=user_id).order_by("created_at", "pk")
        for day_order, plan in enumerate(plans, start=1):
            WorkoutPlan.objects.using(database).filter(pk=plan.pk).update(
                program_id=program.pk,
                program_order=day_order,
            )


class Migration(migrations.Migration):

    dependencies = [
        ("plans", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="WorkoutProgram",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(db_column="Name", max_length=120, verbose_name="Name")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_column="Created_At", verbose_name="Created at")),
                ("updated_at", models.DateTimeField(auto_now=True, db_column="Updated_At", verbose_name="Updated at")),
                ("user", models.ForeignKey(db_column="User_ID", on_delete=django.db.models.deletion.CASCADE, related_name="workout_programs", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "workout program",
                "verbose_name_plural": "workout programs",
                "ordering": ["-updated_at", "id"],
            },
        ),
        migrations.AddField(
            model_name="workoutplan",
            name="program",
            field=models.ForeignKey(db_column="Program_ID", null=True, on_delete=django.db.models.deletion.CASCADE, related_name="days", to="plans.workoutprogram"),
        ),
        migrations.AddField(
            model_name="workoutplan",
            name="program_order",
            field=models.PositiveIntegerField(db_column="Program_Order", default=1, verbose_name="Day order"),
        ),
        migrations.RunPython(group_existing_plans, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="workoutplan",
            name="program",
            field=models.ForeignKey(db_column="Program_ID", on_delete=django.db.models.deletion.CASCADE, related_name="days", to="plans.workoutprogram"),
        ),
        migrations.AlterModelOptions(
            name="workoutplan",
            options={
                "verbose_name": "workout plan",
                "verbose_name_plural": "workout plans",
                "ordering": ["program_order", "id"],
            },
        ),
    ]
