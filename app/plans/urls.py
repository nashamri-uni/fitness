from django.urls import path

from . import views

app_name = "plans"

urlpatterns = [
    path("", views.plan_list, name="list"),
    path("new/", views.create_plan, name="create"),
    path("<int:pk>/", views.plan_detail, name="detail"),
    path("<int:pk>/edit/", views.edit_plan, name="edit"),
    path("<int:pk>/delete/", views.delete_plan, name="delete"),
    path("exercise/<int:pk>/edit/", views.edit_plan_exercise, name="edit_exercise"),
    path("exercise/<int:pk>/delete/", views.remove_plan_exercise, name="delete_exercise"),
    path("exercise/<int:pk>/sets/", views.add_set, name="add_set"),
    path("set/<int:pk>/delete/", views.delete_set, name="delete_set"),
]
