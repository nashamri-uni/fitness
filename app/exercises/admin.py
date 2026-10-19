"""Admin interface for the exercise library (FREQ-15)."""
from django.contrib import admin

from .models import Equipment, Exercise, ExerciseEquipment, ExerciseMuscleGroup, MuscleGroup


class ExerciseMuscleGroupInline(admin.TabularInline):
    model = ExerciseMuscleGroup
    extra = 1


class ExerciseEquipmentInline(admin.TabularInline):
    model = ExerciseEquipment
    extra = 1


@admin.register(MuscleGroup)
class MuscleGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "body_region")
    list_filter = ("body_region",)


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ("name",)


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ("name", "exercise_type", "difficulty", "is_active", "created_by")
    list_filter = ("exercise_type", "difficulty", "is_active")
    search_fields = ("name", "description")
    inlines = [ExerciseMuscleGroupInline, ExerciseEquipmentInline]
