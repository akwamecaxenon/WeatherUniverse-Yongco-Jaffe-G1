from django.urls import path
from . import views

app_name = 'weather'

urlpatterns = [
    # Subscriber routes
    path('locations/', views.my_locations, name='my_locations'),
    path('locations/add/', views.add_user_location, name='add_user_location'),
    path('locations/<int:pk>/edit/', views.edit_user_location, name='edit_user_location'),
    path('locations/<int:pk>/delete/', views.delete_user_location, name='delete_user_location'),

    path('alerts/', views.my_alerts, name='my_alerts'),
    path('alerts/add/', views.add_alert_rule, name='add_alert_rule'),
    path('alerts/<int:pk>/edit/', views.edit_alert_rule, name='edit_alert_rule'),
    path('alerts/<int:pk>/delete/', views.delete_alert_rule, name='delete_alert_rule'),

    # Administrator routes
    path('admin/locations/', views.manage_locations, name='manage_locations'),
    path('admin/readings/', views.manage_readings, name='manage_readings'),
]