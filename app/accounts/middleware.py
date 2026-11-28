from django.shortcuts import redirect
from django.urls import reverse


class GoogleProfileMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.user.requires_google_profile:
            allowed_paths = {
                reverse("accounts:complete_google_profile"), reverse("accounts:logout"),
                reverse("set_language"),
            }
            if request.path_info not in allowed_paths:
                return redirect("accounts:complete_google_profile")
        return self.get_response(request)
