from django import forms
from .models import SupportedLocation, UserLocation, WeatherAlertRule, WeatherReading


class SupportedLocationForm(forms.ModelForm):
    class Meta:
        model = SupportedLocation
        fields = ('name', 'region', 'latitude', 'longitude', 'is_active')

    def clean_name(self):
        name = ' '.join(self.cleaned_data['name'].split())
        qs = SupportedLocation.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('This location is already registered in Weather Universe.')
        return name


class UserLocationForm(forms.ModelForm):
    class Meta:
        model = UserLocation
        fields = ('location', 'nickname', 'is_default')

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields['location'].queryset = SupportedLocation.objects.filter(is_active=True)
        self.fields['nickname'].widget.attrs.update(placeholder='e.g., Home, University, Office')

    def clean_location(self):
        location = self.cleaned_data['location']
        qs = UserLocation.objects.filter(user=self.user, location=location)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('You are already monitoring this location.')
        return location


class WeatherReadingForm(forms.ModelForm):
    class Meta:
        model = WeatherReading
        fields = (
            'location',
            'temperature_c',
            'humidity_pct',
            'rain_probability_pct',
            'wind_speed_kmh',
            'condition',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['location'].queryset = SupportedLocation.objects.filter(is_active=True)


class WeatherAlertRuleForm(forms.ModelForm):
    class Meta:
        model = WeatherAlertRule
        fields = ('user_location', 'metric', 'threshold_value', 'is_active')

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields['user_location'].queryset = UserLocation.objects.filter(user=user).select_related('location')
        self.fields['user_location'].label = 'Saved Location'

    def clean(self):
        cleaned = super().clean()
        metric = cleaned.get('metric')
        val = cleaned.get('threshold_value')
        if metric and val is not None:
            if metric == WeatherAlertRule.Metric.RAIN and not (0 <= val <= 100):
                self.add_error('threshold_value', 'Rain probability threshold must be between 0% and 100%.')
            elif metric == WeatherAlertRule.Metric.TEMP and not (-20 <= val <= 55):
                self.add_error('threshold_value', 'Temperature threshold must be between -20°C and 55°C.')
            elif metric == WeatherAlertRule.Metric.WIND and not (0 <= val <= 350):
                self.add_error('threshold_value', 'Wind speed threshold must be between 0 and 350 km/h.')
        return cleaned