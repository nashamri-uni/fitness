from django.urls import path

from . import views

app_name = "exercises"

urlpatterns = [
    path("", views.library, name="library"),
    path("<int:pk>/", views.exercise_detail, name="detail"),
    # Administrator management (FREQ-15)
    path("manage/", views.manage_exercises, name="manage"),
    path("manage/add/", views.create_exercise, name="create"),
    path("manage/<int:pk>/edit/", views.edit_exercise, name="edit"),
    path("manage/<int:pk>/delete/", views.delete_exercise, name="delete"),
]
