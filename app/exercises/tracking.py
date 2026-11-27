"""Shared tracking modes for the workout builder and active sessions."""

from .models import Exercise


def exercise_kind(exercise):
    name = f"{exercise.name} {exercise.name_ar}".casefold()
    equipment = " ".join(link.equipment.name.casefold() for link in exercise.equipment_links.all())
    timed_terms = ("plank", "wall sit", "hollow hold", "static hold", "dead hang")
    cardio_terms = ("treadmill", "elliptical", "stationary bike", "rowing machine", "stepper")
    if any(term in name for term in timed_terms):
        return "timed"
    if exercise.exercise_type == Exercise.ExerciseType.CARDIO or any(
        term in name or term in equipment for term in cardio_terms
    ):
        return "cardio"
    if not equipment or equipment == "bodyweight":
        return "bodyweight"
    return "resistance"
