"""Forms for registration and profile management (FREQ-1, FREQ-13)."""
from django import forms

from .models import User, UserProfile


class RegisterForm(forms.ModelForm):
    """UC-1: Register a new account."""

    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email", "gender"]

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("The two password fields do not match.")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            UserProfile.objects.create(user=user)
        return user


class ProfileForm(forms.ModelForm):
    """UC-28/UC-29: Update profile information and fitness preferences."""

    class Meta:
        model = UserProfile
        fields = ["date_of_birth", "height_cm", "weight_kg", "fitness_goal"]
        widgets = {"date_of_birth": forms.DateInput(attrs={"type": "date"})}


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "gender"]
