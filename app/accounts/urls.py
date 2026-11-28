from django.contrib.auth import views as auth_views
from django.urls import path

from . import security, views
from .forms import LoginForm

app_name = "accounts"

urlpatterns = [
    path("register/", views.register, name="register"),
    path(
        "login/",
        auth_views.LoginView.as_view(
            authentication_form=LoginForm,
            template_name="accounts/login.html",
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("profile/", views.profile, name="profile"),
    path("profile/complete-google/", views.complete_google_profile, name="complete_google_profile"),
    path("profile/security/", security.security, name="security"),
    path("profile/security/password/", security.change_password, name="password"),
    path("profile/security/email/", security.change_email, name="change_email"),
    path("profile/security/email/confirm/<str:token>/", security.confirm_email, name="confirm_email"),
    path("profile/security/reauthenticate/", security.reauthenticate_google, name="reauthenticate_google"),
]
