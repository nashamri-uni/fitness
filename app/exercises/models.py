from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import get_language


def localized_name(language, english, arabic):
    """Return the Arabic name when Arabic is active, otherwise the stored name."""
    if (language or "").startswith("ar") and arabic:
        return arabic
    return english


class NameMixin(models.Model):
    """Optional Arabic name + language-aware display name."""

    name_ar = models.CharField(max_length=120, blank=True, db_column="Name_Ar")

    class Meta:
        abstract = True

    def display_name(self):
        return localized_name(get_language(), self.name, self.name_ar)


class MuscleGroup(NameMixin):
    class BodyRegion(models.TextChoices):
        UPPER = "upper", _("Upper body")
        LOWER = "lower", _("Lower body")
        CORE = "core", _("Core")

    name = models.CharField(max_length=80, unique=True, db_column="Name", verbose_name=_("Name"))
    body_region = models.CharField(
        max_length=20,
        choices=BodyRegion.choices,
        default=BodyRegion.UPPER,
        db_column="Body_Region",
        verbose_name=_("Body region"),
    )

    class Meta:
        db_table = "Muscle_Group"
        ordering = ["name"]
        verbose_name = _("muscle group")
        verbose_name_plural = _("muscle groups")

    def __str__(self):
        return self.display_name()


class Equipment(NameMixin):
    name = models.CharField(max_length=80, unique=True, db_column="Name", verbose_name=_("Name"))

    class Meta:
        db_table = "Equipment"
        ordering = ["name"]
        verbose_name = _("equipment")
        verbose_name_plural = _("equipment")

    def __str__(self):
        return self.display_name()


class Exercise(NameMixin):
    """Exercise definition in the library (report schema: Exercise)."""

    class ExerciseType(models.TextChoices):
        STRENGTH = "strength", _("Strength")
        CARDIO = "cardio", _("Cardio")
        FLEXIBILITY = "flexibility", _("Flexibility")
        BALANCE = "balance", _("Balance")

    class Difficulty(models.TextChoices):
        BEGINNER = "beginner", _("Beginner")
        INTERMEDIATE = "intermediate", _("Intermediate")
        ADVANCED = "advanced", _("Advanced")

    name = models.CharField(max_length=120, unique=True, db_column="Name", verbose_name=_("Name"))
    description = models.TextField(blank=True, db_column="Description", verbose_name=_("Description"))
    instructions = models.TextField(blank=True, db_column="Instructions", verbose_name=_("Instructions"))
    difficulty = models.CharField(
        max_length=20,
        choices=Difficulty.choices,
        default=Difficulty.BEGINNER,
        db_column="Difficulty",
        verbose_name=_("Difficulty"),
    )
    exercise_type = models.CharField(
        max_length=20,
        choices=ExerciseType.choices,
        default=ExerciseType.STRENGTH,
        db_column="Exercise_Type",
        verbose_name=_("Exercise type"),
    )
    image = models.CharField(max_length=255, blank=True, db_column="Image", verbose_name=_("Image"))
    video_url = models.URLField(max_length=255, blank=True, db_column="Video_URL", verbose_name=_("Video URL"))
    is_active = models.BooleanField(default=True, db_column="Is_Active", verbose_name=_("Active"))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_exercises",
        db_column="Created_By",
        verbose_name=_("Created by"),
    )

    class Meta:
        db_table = "Exercise"
        ordering = ["name"]
        verbose_name = _("exercise")
        verbose_name_plural = _("exercises")

    def primary_muscles(self):
        return [
            link.muscle_group
            for link in self.muscle_links.all()
            if link.role == ExerciseMuscleGroup.Role.PRIMARY
        ]

    def secondary_muscles(self):
        return [
            link.muscle_group
            for link in self.muscle_links.all()
            if link.role != ExerciseMuscleGroup.Role.PRIMARY
        ]

    def equipment_list(self):
        return [link.equipment for link in self.equipment_links.all()]

    def __str__(self):
        return self.display_name()


class ExerciseMuscleGroup(models.Model):
    """Exercise ↔ Muscle_Group link (report schema: Exercise_Muscle_Group)."""

    class Role(models.TextChoices):
        PRIMARY = "primary", _("Primary")
        SECONDARY = "secondary", _("Secondary")

    exercise = models.ForeignKey(
        Exercise,
        on_delete=models.CASCADE,
        related_name="muscle_links",
        db_column="Exercise_ID",
        verbose_name=_("Exercise"),
    )
    muscle_group = models.ForeignKey(
        MuscleGroup,
        on_delete=models.CASCADE,
        related_name="exercise_links",
        db_column="Muscle_Group_ID",
        verbose_name=_("Muscle group"),
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.PRIMARY,
        db_column="Role",
        verbose_name=_("Role"),
    )

    class Meta:
        db_table = "Exercise_Muscle_Group"
        ordering = ["role", "muscle_group"]
        constraints = [models.UniqueConstraint(fields=["exercise", "muscle_group"], name="uniq_exercise_muscle_group")]
        verbose_name = _("exercise muscle group")
        verbose_name_plural = _("exercise muscle groups")

    def __str__(self):
        return f"{self.exercise.display_name()} → {self.muscle_group.display_name()}"


class ExerciseEquipment(models.Model):
    """Exercise ↔ Equipment link (report schema: Exercise_Equipment)."""

    exercise = models.ForeignKey(
        Exercise,
        on_delete=models.CASCADE,
        related_name="equipment_links",
        db_column="Exercise_ID",
        verbose_name=_("Exercise"),
    )
    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.CASCADE,
        related_name="exercise_links",
        db_column="Equipment_ID",
        verbose_name=_("Equipment"),
    )

    class Meta:
        db_table = "Exercise_Equipment"
        ordering = ["equipment"]
        constraints = [models.UniqueConstraint(fields=["exercise", "equipment"], name="uniq_exercise_equipment")]
        verbose_name = _("exercise equipment")
        verbose_name_plural = _("exercise equipment")

    def __str__(self):
        return f"{self.exercise.display_name()} → {self.equipment.display_name()}"
