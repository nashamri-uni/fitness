from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

WEEKLY_WORKOUT_GOAL_CHOICES = tuple((days, str(days)) for days in range(1, 8))


class User(AbstractUser):
    """Application user (report schema: User)."""

    class Role(models.TextChoices):
        USER = "user", _("User")
        ADMIN = "admin", _("Administrator")

    class Gender(models.TextChoices):
        MALE = "male", _("Male")
        FEMALE = "female", _("Female")

    gender = models.CharField(max_length=20, choices=Gender.choices, default=Gender.MALE, db_column="Gender", verbose_name=_("Gender"))
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.USER,
        db_column="Role",
        verbose_name=_("Role"),
    )

    @property
    def is_project_admin(self):
        return self.role == self.Role.ADMIN or self.is_staff

    class Meta(AbstractUser.Meta):
        ordering = ["username"]
        verbose_name = _("user")
        verbose_name_plural = _("users")

    def __str__(self):
        return self.username


class UserProfile(models.Model):
    """Fitness preferences for a user (report schema: User_Profile)."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        db_column="User_ID",
    )
    date_of_birth = models.DateField(blank=True, null=True, db_column="Date_Of_Birth", verbose_name=_("Date of birth"))
    height_cm = models.FloatField(blank=True, null=True, db_column="Height_Cm", verbose_name=_("Height (cm)"))
    weight_kg = models.FloatField(blank=True, null=True, db_column="Weight_Kg", verbose_name=_("Weight (kg)"))
    fitness_goal = models.CharField(max_length=100, blank=True, db_column="Fitness_Goal", verbose_name=_("Fitness goal"))
    weekly_workout_goal = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        choices=WEEKLY_WORKOUT_GOAL_CHOICES,
        db_column="Weekly_Workout_Goal",
        validators=[MinValueValidator(1), MaxValueValidator(7)],
        verbose_name=_("Weekly workout goal (days)"),
    )

    class Meta:
        db_table = "User_Profile"
        ordering = ["user"]
        constraints = [
            models.CheckConstraint(
                condition=Q(weekly_workout_goal__isnull=True)
                | Q(weekly_workout_goal__gte=1, weekly_workout_goal__lte=7),
                name="profile_weekly_goal_1_7",
            )
        ]
        verbose_name = _("user profile")
        verbose_name_plural = _("user profiles")

    def __str__(self):
        return f"Profile of {self.user.username}"


class WeeklyWorkoutGoalHistory(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="weekly_workout_goal_history",
        db_column="User_ID",
    )
    goal_days = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        choices=WEEKLY_WORKOUT_GOAL_CHOICES,
        db_column="Goal_Days",
        validators=[MinValueValidator(1), MaxValueValidator(7)],
        verbose_name=_("Weekly workout goal (days)"),
    )
    effective_at = models.DateTimeField(
        default=timezone.now,
        db_column="Effective_At",
        verbose_name=_("Effective at"),
    )

    class Meta:
        db_table = "Weekly_Workout_Goal_History"
        ordering = ["-effective_at", "-pk"]
        constraints = [
            models.CheckConstraint(
                condition=Q(goal_days__isnull=True) | Q(goal_days__gte=1, goal_days__lte=7),
                name="weekly_goal_history_days_1_7",
            )
        ]
        verbose_name = _("weekly workout goal history")
        verbose_name_plural = _("weekly workout goal history")
