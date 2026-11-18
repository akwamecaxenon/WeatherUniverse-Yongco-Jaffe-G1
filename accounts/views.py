from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from .decorators import role_required
from .forms import LoginForm, ProfileForm, RegistrationForm
from .models import User


def dashboard_url_for(user):
    """Name of the dashboard that belongs to the user's role."""
    return 'accounts:admin_dashboard' if user.role == User.Role.ADMIN else 'accounts:user_dashboard'


def register(request):
    if request.user.is_authenticated:
        return redirect(dashboard_url_for(request.user))
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your account was created. You can log in now.')
            return redirect('accounts:login')
        messages.error(request, 'Registration failed. Please fix the errors below.')
    else:
        form = RegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})


class WeatherLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True
    next_page = reverse_lazy('accounts:redirect')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Welcome back, {form.get_user().get_short_name()}!')
        return response

    def form_invalid(self, form):
        messages.error(self.request, 'Login failed. Check your email and password.')
        return super().form_invalid(form)


@require_POST
def logout_view(request):
    logout(request)  # ends the session
    messages.success(request, 'You have been logged out.')
    return redirect('accounts:login')


@login_required
def role_redirect(request):
    """Send each user to the dashboard for their role."""
    return redirect(dashboard_url_for(request.user))


@role_required(User.Role.USER)
def user_dashboard(request):
    return render(request, 'accounts/user_dashboard.html')


@role_required(User.Role.ADMIN)
def admin_dashboard(request):
    context = {
        'total_users': User.objects.count(),
        'total_admins': User.objects.filter(role=User.Role.ADMIN).count(),
        'total_members': User.objects.filter(role=User.Role.USER).count(),
        'recent_users': User.objects.order_by('-created_at')[:8],
    }
    return render(request, 'accounts/admin_dashboard.html', context)


@login_required
def profile(request):
    # Always the logged-in user's own record: there is no user id in the URL.
    return render(request, 'accounts/profile.html', {'profile_user': request.user})


@login_required
def profile_edit(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile was updated.')
            return redirect('accounts:profile')
        messages.error(request, 'Your profile was not saved. Please fix the errors below.')
    else:
        form = ProfileForm(instance=request.user)
    return render(request, 'accounts/profile_edit.html', {'form': form})
