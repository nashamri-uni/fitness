from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import ValidationError

from .emails import normalize_email, users_with_email
from .models import User


class IdentifierBackend(ModelBackend):
    """Authenticate an identifier only when it resolves to exactly one account."""

    def authenticate(self, request, identifier=None, password=None):
        if identifier is None or password is None:
            return None

        matches = User.objects.filter(username=identifier)
        try:
            email = normalize_email(identifier)
        except ValidationError:
            pass
        else:
            matches = matches | users_with_email(email)

        candidates = list(matches.order_by("pk")[:2])
        if len(candidates) != 1:
            User().set_password(password)
            return None
        user = candidates[0]
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
