"""Admin interface for managing users (FREQ-16)."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, UserProfile


@admin.register(User)
class ProjectUserAdmin(UserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "role", "date_joined")
    list_filter = ("role", "gender")
    fieldsets = UserAdmin.fieldsets + (("Project fields", {"fields": ("gender", "role")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Project fields", {"fields": ("gender", "role")}),)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "fitness_goal", "height_cm", "weight_kg", "date_of_birth")
    list_filter = ("fitness_goal",)
