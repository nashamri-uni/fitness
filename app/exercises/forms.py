"""Forms for administrator exercise library management (FREQ-15)."""
from django import forms

from .models import Equipment, Exercise, ExerciseEquipment, ExerciseMuscleGroup, MuscleGroup


class ExerciseForm(forms.ModelForm):
    """Add or update an exercise, including its muscle group and equipment links."""

    muscle_groups = forms.ModelMultipleChoiceField(
        queryset=MuscleGroup.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "select-multiple"}),
    )
    equipment = forms.ModelMultipleChoiceField(
        queryset=Equipment.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "select-multiple"}),
    )

    class Meta:
        model = Exercise
        fields = [
            "name",
            "description",
            "instructions",
            "difficulty",
            "exercise_type",
            "image",
            "video_url",
            "is_active",
        ]

    def __init__(self, *args, **kwargs):
        instance = kwargs.get("instance")
        super().__init__(*args, **kwargs)
        if instance and instance.pk:
            self.initial["muscle_groups"] = [
                link.muscle_group_id for link in instance.muscle_links.all()
            ]
            self.initial["equipment"] = [link.equipment_id for link in instance.equipment_links.all()]

    def save(self, commit=True):
        exercise = super().save(commit)
        if commit:
            selected_groups = list(self.cleaned_data.get("muscle_groups", []))
            for group in selected_groups:
                ExerciseMuscleGroup.objects.update_or_create(
                    exercise=exercise,
                    muscle_group=group,
                    defaults={"role": ExerciseMuscleGroup.Role.PRIMARY},
                )
            exercise.muscle_links.exclude(muscle_group__in=selected_groups).delete()

            selected_equipment = list(self.cleaned_data.get("equipment", []))
            for item in selected_equipment:
                ExerciseEquipment.objects.get_or_create(exercise=exercise, equipment=item)
            exercise.equipment_links.exclude(equipment__in=selected_equipment).delete()
        return exercise
