from django.contrib import admin

from .models import PlanExercise, PlanSet, WorkoutPlan


class PlanExerciseInline(admin.TabularInline):
    model = PlanExercise
    extra = 1


@admin.register(WorkoutPlan)
class WorkoutPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "goal", "estimated_duration_minutes", "created_at")
    list_filter = ("goal",)
    search_fields = ("name", "user__username")
    inlines = [PlanExerciseInline]


@admin.register(PlanSet)
class PlanSetAdmin(admin.ModelAdmin):
    list_display = ("plan_exercise", "set_number", "reps", "weight_kg", "set_type")
