from django.contrib import admin

from .models import PersonalRecord, SessionExercise, SessionSet, WorkoutSession


class SessionExerciseInline(admin.TabularInline):
    model = SessionExercise
    extra = 1


@admin.register(WorkoutSession)
class WorkoutSessionAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "started_at", "duration_minutes", "rating")
    list_filter = ("user", "started_at")
    search_fields = ("name", "user__username")
    inlines = [SessionExerciseInline]


@admin.register(SessionSet)
class SessionSetAdmin(admin.ModelAdmin):
    list_display = ("session_exercise", "set_number", "reps_completed", "weight_kg", "rpe", "is_personal_record")
    list_filter = ("is_personal_record",)


@admin.register(PersonalRecord)
class PersonalRecordAdmin(admin.ModelAdmin):
    list_display = ("user", "exercise", "record_type", "value", "achieved_at")
    list_filter = ("record_type",)
