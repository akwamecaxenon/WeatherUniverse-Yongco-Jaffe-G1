from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User

MAX_PHOTO_BYTES = 2 * 1024 * 1024  # 2 MB


class RegistrationForm(UserCreationForm):
    """Public sign-up. The role is never taken from the form: new accounts are always USER."""

    class Meta:
        model = User
        fields = ('full_name', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['full_name'].required = True
        self.fields['email'].required = True
        self.fields['full_name'].widget.attrs.update(autocomplete='name', placeholder='Juan Dela Cruz')
        self.fields['email'].widget.attrs.update(autocomplete='email', placeholder='you@example.com')
        self.fields['password1'].label = 'Password'
        self.fields['password2'].label = 'Confirm password'
        self.fields['password2'].help_text = 'Enter the same password again.'

    def clean_full_name(self):
        name = ' '.join(self.cleaned_data['full_name'].split())
        if len(name) < 2:
            raise forms.ValidationError('Please enter your full name.')
        return name

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.USER
        user.is_staff = False
        user.is_superuser = False
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'autofocus': True, 'autocomplete': 'email', 'placeholder': 'you@example.com'}),
    )
    error_messages = {
        'invalid_login': 'Invalid email or password. Please try again.',
        'inactive': 'This account is inactive.',
    }

    def clean_username(self):
        return self.cleaned_data['username'].strip().lower()


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('full_name', 'email', 'contact_number', 'profile_photo')
        widgets = {'profile_photo': forms.FileInput(attrs={'accept': 'image/*'})}

    def clean_full_name(self):
        name = ' '.join(self.cleaned_data['full_name'].split())
        if len(name) < 2:
            raise forms.ValidationError('Please enter your full name.')
        return name

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Another account already uses this email.')
        return email

    def clean_profile_photo(self):
        photo = self.cleaned_data.get('profile_photo')
        if photo and hasattr(photo, 'size') and photo.size > MAX_PHOTO_BYTES:
            raise forms.ValidationError('The photo must be 2 MB or smaller.')
        return photo
