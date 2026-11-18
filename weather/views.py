from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User
from .forms import (
    SupportedLocationForm,
    UserLocationForm,
    WeatherAlertRuleForm,
    WeatherReadingForm,
)
from .models import SupportedLocation, UserLocation, WeatherAlertRule, WeatherReading


# --- USER: Monitored Locations CRUD ---

@role_required(User.Role.USER)
def my_locations(request):
    locations = (
        UserLocation.objects.filter(user=request.user)
        .select_related('location')
        .prefetch_related('location__readings')
    )
    # Attach latest reading per location
    location_cards = []
    for ul in locations:
        latest = ul.location.readings.first()
        location_cards.append({'user_loc': ul, 'latest': latest})
    return render(request, 'weather/my_locations.html', {'location_cards': location_cards})


@role_required(User.Role.USER)
def add_user_location(request):
    if request.method == 'POST':
        form = UserLocationForm(request.POST, user=request.user)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            messages.success(request, f'{obj.location.name} added to your monitored locations.')
            return redirect('weather:my_locations')
        messages.error(request, 'Could not add location. Please fix the errors below.')
    else:
        form = UserLocationForm(user=request.user)
    return render(request, 'weather/user_location_form.html', {'form': form, 'title': 'Add Monitored Location'})


@role_required(User.Role.USER)
def edit_user_location(request, pk):
    user_loc = get_object_or_404(UserLocation, pk=pk, user=request.user)
    if request.method == 'POST':
        form = UserLocationForm(request.POST, instance=user_loc, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Monitored location updated.')
            return redirect('weather:my_locations')
        messages.error(request, 'Could not update location. Please fix the errors below.')
    else:
        form = UserLocationForm(instance=user_loc, user=request.user)
    return render(request, 'weather/user_location_form.html', {'form': form, 'title': 'Edit Monitored Location'})


@role_required(User.Role.USER)
@require_POST
def delete_user_location(request, pk):
    user_loc = get_object_or_404(UserLocation, pk=pk, user=request.user)
    name = user_loc.location.name
    user_loc.delete()
    messages.success(request, f'Removed {name} from your monitored locations.')
    return redirect('weather:my_locations')


# --- USER: Weather Alert Rules CRUD & Triggered Alerts ---

@role_required(User.Role.USER)
def my_alerts(request):
    rules = WeatherAlertRule.objects.filter(user=request.user).select_related('user_location__location')
    triggered = []
    for rule in rules.filter(is_active=True):
        latest = rule.user_location.location.readings.first()
        if not latest:
            continue
        val = None
        if rule.metric == WeatherAlertRule.Metric.TEMP:
            val = latest.temperature_c
        elif rule.metric == WeatherAlertRule.Metric.RAIN:
            val = latest.rain_probability_pct
        elif rule.metric == WeatherAlertRule.Metric.WIND:
            val = latest.wind_speed_kmh
        if val is not None and val >= rule.threshold_value:
            triggered.append({'rule': rule, 'reading': latest, 'actual_value': val})
    return render(request, 'weather/my_alerts.html', {'rules': rules, 'triggered': triggered})


@role_required(User.Role.USER)
def add_alert_rule(request):
    if not UserLocation.objects.filter(user=request.user).exists():
        messages.warning(request, 'Please add at least one monitored location before creating an alert rule.')
        return redirect('weather:add_user_location')

    if request.method == 'POST':
        form = WeatherAlertRuleForm(request.POST, user=request.user)
        if form.is_valid():
            rule = form.save(commit=False)
            rule.user = request.user
            rule.save()
            messages.success(request, 'Weather alert rule created.')
            return redirect('weather:my_alerts')
        messages.error(request, 'Could not create alert rule. Please check your inputs.')
    else:
        form = WeatherAlertRuleForm(user=request.user)
    return render(request, 'weather/alert_rule_form.html', {'form': form, 'title': 'Create Weather Alert Rule'})


@role_required(User.Role.USER)
def edit_alert_rule(request, pk):
    rule = get_object_or_404(WeatherAlertRule, pk=pk, user=request.user)
    if request.method == 'POST':
        form = WeatherAlertRuleForm(request.POST, instance=rule, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Weather alert rule updated.')
            return redirect('weather:my_alerts')
        messages.error(request, 'Could not update alert rule. Please check your inputs.')
    else:
        form = WeatherAlertRuleForm(instance=rule, user=request.user)
    return render(request, 'weather/alert_rule_form.html', {'form': form, 'title': 'Edit Weather Alert Rule'})


@role_required(User.Role.USER)
@require_POST
def delete_alert_rule(request, pk):
    rule = get_object_or_404(WeatherAlertRule, pk=pk, user=request.user)
    rule.delete()
    messages.success(request, 'Weather alert rule deleted.')
    return redirect('weather:my_alerts')


# --- ADMIN: Supported Locations & Weather Readings ---

@role_required(User.Role.ADMIN)
def manage_locations(request):
    locations = SupportedLocation.objects.all()
    if request.method == 'POST':
        form = SupportedLocationForm(request.POST)
        if form.is_valid():
            loc = form.save()
            messages.success(request, f'Supported location "{loc.name}" added.')
            return redirect('weather:manage_locations')
        messages.error(request, 'Failed to add location. Check the form errors.')
    else:
        form = SupportedLocationForm()
    return render(request, 'weather/manage_locations.html', {'locations': locations, 'form': form})


@role_required(User.Role.ADMIN)
def manage_readings(request):
    readings = WeatherReading.objects.select_related('location', 'recorded_by')[:25]
    if request.method == 'POST':
        form = WeatherReadingForm(request.POST)
        if form.is_valid():
            reading = form.save(commit=False)
            reading.recorded_by = request.user
            reading.save()
            msg = f'Weather reading recorded for {reading.location.name}.'
            if reading.is_severe:
                msg += ' Flagged as SEVERE for Disaster Universe.'
            messages.success(request, msg)
            return redirect('weather:manage_readings')
        messages.error(request, 'Failed to record weather reading. Please fix the errors below.')
    else:
        form = WeatherReadingForm()
    return render(request, 'weather/manage_readings.html', {'readings': readings, 'form': form})