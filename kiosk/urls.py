from django.urls import path

from . import views

urlpatterns = [
    path('', views.terminal, name='kiosk-terminal'),
    path('login/', views.login, name='kiosk-login'),
    path('logout/', views.logout, name='kiosk-logout'),
    path('checkout/', views.checkout, name='kiosk-checkout'),
    path('tickets/<int:ticket_id>/', views.receipt, name='kiosk-receipt'),
]
