"""URL configuration for the project."""
from django.contrib import admin
from django.urls import include, path
from django.views.generic.base import RedirectView
from django.views.i18n import set_language

from accounts import google

urlpatterns = [
    # The provider reverses these names without the project namespace.
    path("accounts/google/login/", google.google_login, name="google_login"),
    path("accounts/google/login/callback/", google.google_callback, name="google_callback"),
    path("admin/", admin.site.urls),
    path(
        "",
        RedirectView.as_view(pattern_name="analytics:dashboard", permanent=False),
        name="home",
    ),
    path("accounts/", include("accounts.urls")),
    path("exercises/", include("exercises.urls")),
    path("plans/", include("plans.urls")),
    path("sessions/", include("workouts.urls")),
    path("analytics/", include("analytics.urls")),
    path("i18n/setlang/", set_language, name="set_language"),
]
