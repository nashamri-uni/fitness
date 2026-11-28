from django.conf import settings


def auth_options(request):
    return {
        "google_auth_enabled": settings.GOOGLE_AUTH_ENABLED,
        "show_google_setup_hint": settings.DEBUG and not settings.GOOGLE_AUTH_ENABLED,
    }
