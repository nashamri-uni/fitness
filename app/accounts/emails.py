"""Normalize email addresses consistently with the SQLite uniqueness guards."""
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models.functions import Lower, Trim
from django.utils.translation import gettext_lazy as _


def normalize_email(value):
    value = value.strip()
    validate_email(value)
    local, domain = value.rsplit("@", 1)
    try:
        email = f"{local.lower()}@{domain.encode('idna').decode('ascii').lower()}"
    except UnicodeError as error:
        raise ValidationError(_("Enter a valid email address.")) from error
    if not email.isascii() or len(email) > 254:
        raise ValidationError(_("Enter a valid email address."))
    return email


def users_with_email(email):
    from .models import User

    return User.objects.alias(normalized_email=Lower(Trim("email"))).filter(normalized_email=email)
