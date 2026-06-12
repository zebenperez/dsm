from django.urls import path, re_path
from django.views.generic.base import RedirectView
from pwa import views

urlpatterns = [
	#path('', RedirectView.as_view(url='payments')),
	path('', RedirectView.as_view(url='index')),
	path('index', views.index, name="pwa-index"),
	path('login', views.login, name="pwa-login"),
	path('logout', views.logout, name="pwa-logout"),
	#path('index', views.index, name="pwa-index"),
	path('payments', views.payments, name="pwa-payments"),
	path('assistances', views.assistances, name="pwa-assistances"),
	path('set-pin', views.set_pin, name="pwa-set-pin"),
	path('change-photo', views.change_photo, name="pwa-change-photo"),
]

