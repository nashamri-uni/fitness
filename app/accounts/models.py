from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


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

    class Meta:
        db_table = "User_Profile"
        ordering = ["user"]
        verbose_name = _("user profile")
        verbose_name_plural = _("user profiles")

    def __str__(self):
        return f"Profile of {self.user.username}"
