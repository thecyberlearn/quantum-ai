from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.homepage_view, name='homepage'),
    path('pricing/', views.pricing_view, name='pricing'),
    path('digital-branding/', views.digital_branding_view, name='digital_branding'),
    path('contact/', views.contact_form_view, name='contact_form'),
    path('health/', views.health_check_view, name='health_check'),
]