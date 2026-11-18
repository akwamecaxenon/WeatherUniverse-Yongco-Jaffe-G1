from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class SupportedLocation(models.Model):
    """Master list of supported cities/municipalities managed by Admins."""
    name = models.CharField(max_length=120, unique=True)
    region = models.CharField(max_length=120, default='Central Visayas')
    latitude = models.DecimalField(max_digits=8, decimal_places=5, null=True, blank=True)
    longitude = models.DecimalField(max_digits=8, decimal_places=5, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'supported_locations'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.region})"


class UserLocation(models.Model):
    """Locations saved by a specific user for monitoring (CRUD)."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saved_locations',
    )
    location = models.ForeignKey(
        SupportedLocation,
        on_delete=models.CASCADE,
        related_name='subscribers',
    )
    nickname = models.CharField(max_length=80, blank=True, help_text="e.g., Home, Campus, Office")
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_locations'
        unique_together = ('user', 'location')
        ordering = ['-is_default', 'location__name']

    def save(self, *args, **kwargs):
        # Enforce only one default location per user
        if self.is_default:
            UserLocation.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        label = f" ({self.nickname})" if self.nickname else ""
        return f"{self.user.email} -> {self.location.name}{label}"


class WeatherReading(models.Model):
    """Recorded weather conditions for a supported location."""
    class Condition(models.TextChoices):
        SUNNY = 'SUNNY', 'Sunny / Clear'
        CLOUDY = 'CLOUDY', 'Partly Cloudy'
        RAINY = 'RAINY', 'Rainy'
        THUNDERSTORM = 'THUNDERSTORM', 'Thunderstorm'
        TYPHOON = 'TYPHOON', 'Typhoon / Severe Storm'

    location = models.ForeignKey(
        SupportedLocation,
        on_delete=models.CASCADE,
        related_name='readings',
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='recorded_readings',
    )
    temperature_c = models.DecimalField(
        max_digits=4, decimal_places=1,
        validators=[MinValueValidator(-50.0), MaxValueValidator(60.0)],
    )
    humidity_pct = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    rain_probability_pct = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    wind_speed_kmh = models.DecimalField(
        max_digits=5, decimal_places=1,
        validators=[MinValueValidator(0.0), MaxValueValidator(400.0)],
    )
    condition = models.CharField(max_length=20, choices=Condition.choices, default=Condition.SUNNY)
    is_severe = models.BooleanField(default=False, help_text="Flagged for Disaster Universe sharing")
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'weather_readings'
        ordering = ['-recorded_at']

    def save(self, *args, **kwargs):
        # Business rule: mark severe automatically if thresholds or severe condition are met
        if (
            self.condition in (self.Condition.THUNDERSTORM, self.Condition.TYPHOON)
            or self.wind_speed_kmh >= 60
            or self.rain_probability_pct >= 85
            or self.temperature_c >= 38
        ):
            self.is_severe = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.location.name}: {self.temperature_c}°C, {self.get_condition_display()}"


class WeatherAlertRule(models.Model):
    """User-configured alert thresholds for a saved location (CRUD)."""
    class Metric(models.TextChoices):
        TEMP = 'TEMP', 'Temperature (°C) >='
        RAIN = 'RAIN', 'Rain Probability (%) >='
        WIND = 'WIND', 'Wind Speed (km/h) >='

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='alert_rules',
    )
    user_location = models.ForeignKey(
        UserLocation,
        on_delete=models.CASCADE,
        related_name='alert_rules',
    )
    metric = models.CharField(max_length=10, choices=Metric.choices)
    threshold_value = models.DecimalField(max_digits=5, decimal_places=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'weather_alert_rules'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} | {self.user_location.location.name} ({self.get_metric_display()} {self.threshold_value})"