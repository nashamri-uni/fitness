from django.urls import path

from . import views

app_name = "workouts"

urlpatterns = [
    path("", views.session_list, name="sessions"),
    path("records/", views.personal_records, name="records"),
    path("start/<int:plan_pk>/", views.start_session_view, name="start"),
    path("<int:pk>/", views.active_session, name="active"),
    path("<int:pk>/complete/", views.complete_session, name="complete"),
    path("exercise/<int:pk>/log/", views.log_set, name="log_set"),
    path("history/<int:pk>/", views.session_detail, name="detail"),
]
