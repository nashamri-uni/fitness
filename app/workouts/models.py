"""Workout session models (FREQ-8, FREQ-10, FREQ-11)."""
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class WorkoutSession(models.Model):
    """The WorkoutSession table: a completed (or in-progress) training session."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sessions", db_column="User_ID"
    )
    plan = models.ForeignKey(
        "plans.WorkoutPlan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sessions",
        db_column="Plan_ID",
    )
    name = models.CharField(max_length=120, db_column="Name", verbose_name=_("Name"))
    started_at = models.DateTimeField(db_column="Started_At", verbose_name=_("Started at"))
    ended_at = models.DateTimeField(null=True, blank=True, db_column="Ended_At", verbose_name=_("Ended at"))
    duration_minutes = models.PositiveIntegerField(default=0, db_column="Duration_Minutes", verbose_name=_("Duration (minutes)"))
    notes = models.TextField(blank=True, db_column="Notes", verbose_name=_("Notes"))
    rating = models.PositiveSmallIntegerField(null=True, blank=True, db_column="Rating", verbose_name=_("Rating"))

    class Meta:
        ordering = ["-started_at"]
        verbose_name = _("workout session")
        verbose_name_plural = _("workout sessions")

    def __str__(self):
        return f"{self.name} ({self.started_at:%Y-%m-%d})"

    @property
    def is_finished(self):
        return self.ended_at is not None

    def total_volume(self):
        return sum(s.volume for entry in self.exercises.all() for s in entry.sets.all())

    def total_sets(self):
        return sum(entry.sets.count() for entry in self.exercises.all())

    def personal_records(self):
        return [s for entry in self.exercises.all() for s in entry.sets.all() if s.is_personal_record]

    def average_rpe(self):
        values = [s.rpe for entry in self.exercises.all() for s in entry.sets.all() if s.rpe]
        return round(sum(values) / len(values), 1) if values else None


class SessionExercise(models.Model):
    """The SessionExercise table: an exercise performed in a session."""

    session = models.ForeignKey(
        WorkoutSession, on_delete=models.CASCADE, related_name="exercises", db_column="Session_ID"
    )
    exercise = models.ForeignKey(
        "exercises.Exercise", on_delete=models.CASCADE, related_name="session_entries", db_column="Exercise_ID"
    )
    order = models.PositiveIntegerField(default=1, db_column="Order", verbose_name=_("Order"))
    notes = models.CharField(max_length=255, blank=True, db_column="Notes", verbose_name=_("Notes"))

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("session exercise")
        verbose_name_plural = _("session exercises")

    def completed_sets(self):
        return self.sets.all()

    def volume(self):
        return sum(s.volume for s in self.sets.all())


class SessionSet(models.Model):
    """The SessionSet table: a logged set with the actual performance data."""

    session_exercise = models.ForeignKey(
        SessionExercise, on_delete=models.CASCADE, related_name="sets", db_column="Session_Exercise_ID"
    )
    set_number = models.PositiveIntegerField(default=1, db_column="Set_Number", verbose_name=_("Set number"))
    reps_completed = models.PositiveIntegerField(default=0, db_column="Reps_Completed", verbose_name=_("Reps completed"))
    weight_kg = models.FloatField(default=0, db_column="Weight_Kg", verbose_name=_("Weight (kg)"))
    duration_seconds = models.PositiveIntegerField(default=0, db_column="Duration_Seconds", verbose_name=_("Duration (seconds)"))
    rpe = models.PositiveSmallIntegerField(null=True, blank=True, db_column="RPE", verbose_name=_("RPE"))
    is_personal_record = models.BooleanField(default=False, db_column="Is_Personal_Record", verbose_name=_("Personal record"))
    logged_at = models.DateTimeField(auto_now_add=True, db_column="Logged_At", verbose_name=_("Logged at"))

    class Meta:
        ordering = ["set_number", "id"]
        verbose_name = _("logged set")
        verbose_name_plural = _("logged sets")

    @property
    def volume(self):
        return self.weight_kg * self.reps_completed

    @property
    def session(self):
        return self.session_exercise.session

    @property
    def exercise(self):
        return self.session_exercise.exercise


class PersonalRecord(models.Model):
    """The PersonalRecord table: the best value achieved by a user for an exercise."""

    class RecordType(models.TextChoices):
        MAX_WEIGHT = "max_weight", _("Max weight")
        MAX_REPS = "max_reps", _("Max reps")
        MAX_VOLUME = "max_volume", _("Max volume")
        MAX_DURATION = "max_duration", _("Max duration")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="personal_records", db_column="User_ID"
    )
    exercise = models.ForeignKey(
        "exercises.Exercise", on_delete=models.CASCADE, related_name="personal_records", db_column="Exercise_ID"
    )
    record_type = models.CharField(
        max_length=20, choices=RecordType.choices, db_column="Record_Type", verbose_name=_("Record type")
    )
    value = models.FloatField(db_column="Value", verbose_name=_("Value"))
    session_set = models.ForeignKey(
        SessionSet,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="records",
        db_column="Session_Set_ID",
    )
    achieved_at = models.DateTimeField(db_column="Achieved_At", verbose_name=_("Achieved at"))

    class Meta:
        ordering = ["-achieved_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "exercise", "record_type"], name="uniq_user_exercise_record")
        ]
        verbose_name = _("personal record")
        verbose_name_plural = _("personal records")

    def __str__(self):
        return f"{self.user.username} - {self.exercise.display_name()} - {self.get_record_type_display()}"
