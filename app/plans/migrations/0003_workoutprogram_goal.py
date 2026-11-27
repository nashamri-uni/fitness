from django.db import migrations, models


def derive_program_goals(apps, schema_editor):
    Program = apps.get_model("plans", "WorkoutProgram")
    Day = apps.get_model("plans", "WorkoutPlan")
    database = schema_editor.connection.alias
    for program in Program.objects.using(database).iterator():
        goals = list(
            Day.objects.using(database).filter(program=program, user_id=program.user_id)
            .order_by().values_list("goal", flat=True).distinct()[:2]
        )
        if len(goals) == 1 and goals[0]:
            Program.objects.using(database).filter(pk=program.pk).update(goal=goals[0])


class Migration(migrations.Migration):
    dependencies = [("plans", "0002_workoutprogram_and_day_order")]

    operations = [
        migrations.AddField(
            model_name="workoutprogram",
            name="goal",
            field=models.CharField(
                max_length=20, db_column="Goal", null=True, blank=True, verbose_name="Training goal",
                choices=[
                    ("strength", "Strength"), ("hypertrophy", "Hypertrophy"), ("cardio", "Cardio"),
                    ("endurance", "Endurance"), ("weight_loss", "Weight loss"), ("maintenance", "Maintenance"),
                ],
            ),
        ),
        migrations.RunPython(derive_program_goals, migrations.RunPython.noop),
    ]
