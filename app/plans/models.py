"""Workout plan models (FREQ-4, FREQ-5, FREQ-6, FREQ-7)."""
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class WorkoutPlan(models.Model):
    """The WorkoutPlan table: a reusable workout plan owned by a user."""

    class Goal(models.TextChoices):
        STRENGTH = "strength", _("Strength")
        HYPERTROPHY = "hypertrophy", _("Hypertrophy")
        CARDIO = "cardio", _("Cardio")
        ENDURANCE = "endurance", _("Endurance")
        WEIGHT_LOSS = "weight_loss", _("Weight loss")
        MAINTENANCE = "maintenance", _("Maintenance")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="plans", db_column="User_ID"
    )
    name = models.CharField(max_length=120, db_column="Name", verbose_name=_("Name"))
    description = models.TextField(blank=True, db_column="Description", verbose_name=_("Description"))
    goal = models.CharField(max_length=20, choices=Goal.choices, default=Goal.STRENGTH, db_column="Goal", verbose_name=_("Goal"))
    estimated_duration_minutes = models.PositiveIntegerField(
        default=45, db_column="Estimated_Duration_Minutes", verbose_name=_("Estimated duration (minutes)")
    )
    created_at = models.DateTimeField(auto_now_add=True, db_column="Created_At", verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, db_column="Updated_At", verbose_name=_("Updated at"))

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("workout plan")
        verbose_name_plural = _("workout plans")

    def __str__(self):
        return self.name

    def total_sets(self):
        return sum(len(exercise.sets.all()) for exercise in self.exercises.all())

    def total_reps(self):
        return sum(
            set_obj.reps
            for exercise in self.exercises.all()
            for set_obj in exercise.sets.all()
        )

    def total_rest_seconds(self):
        return sum(exercise.rest_seconds for exercise in self.exercises.all())


class PlanExercise(models.Model):
    """The PlanExercise table: an exercise inside a plan."""

    plan = models.ForeignKey(
        WorkoutPlan, on_delete=models.CASCADE, related_name="exercises", db_column="Plan_ID"
    )
    exercise = models.ForeignKey(
        "exercises.Exercise", on_delete=models.CASCADE, related_name="plan_entries", db_column="Exercise_ID"
    )
    order = models.PositiveIntegerField(default=1, db_column="Order", verbose_name=_("Order"))
    notes = models.CharField(max_length=255, blank=True, db_column="Notes", verbose_name=_("Notes"))
    rest_seconds = models.PositiveIntegerField(default=90, db_column="Rest_Seconds", verbose_name=_("Rest seconds"))

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["plan", "exercise"], name="uniq_plan_exercise")
        ]
        verbose_name = _("plan exercise")
        verbose_name_plural = _("plan exercises")

    def __str__(self):
        return f"{self.plan.name} - {self.exercise.display_name()}"


class PlanSet(models.Model):
    """The PlanSet table: a planned set for an exercise in a plan."""

    class SetType(models.TextChoices):
        NORMAL = "normal", _("Normal")
        WARMUP = "warmup", _("Warm-up")
        DROP_SET = "drop_set", _("Drop set")
        FAILURE = "failure", _("To failure")

    plan_exercise = models.ForeignKey(
        PlanExercise, on_delete=models.CASCADE, related_name="sets", db_column="Plan_Exercise_ID"
    )
    set_number = models.PositiveIntegerField(default=1, db_column="Set_Number", verbose_name=_("Set number"))
    reps = models.PositiveIntegerField(default=10, db_column="Reps", verbose_name=_("Reps"))
    duration_seconds = models.PositiveIntegerField(default=0, db_column="Duration_Seconds", verbose_name=_("Duration (seconds)"))
    weight_kg = models.FloatField(default=0, db_column="Weight_Kg", verbose_name=_("Weight (kg)"))
    set_type = models.CharField(max_length=20, choices=SetType.choices, default=SetType.NORMAL, db_column="Set_Type", verbose_name=_("Set type"))

    class Meta:
        ordering = ["set_number", "id"]
        verbose_name = _("planned set")
        verbose_name_plural = _("planned sets")

    def __str__(self):
        return f"{self.plan_exercise.exercise.display_name()} set {self.set_number}"

    @property
    def volume(self):
        """Estimated volume for this set (weight x reps)."""
        return self.weight_kg * self.reps
