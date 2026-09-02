from django.urls import path

from . import views

app_name = 'events'

urlpatterns = [
    path('', views.month, name='month'),
    path('<int:year>/<int:month>/', views.month, name='month_by_date'),
    path('events/add/', views.event_add, name='event_add'),
    path('events/<int:pk>/edit/', views.event_edit, name='event_edit'),
    path('events/<int:pk>/delete/', views.event_delete, name='event_delete'),
]
