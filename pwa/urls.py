from django.urls import path, re_path
from django.views.generic.base import RedirectView
from pwa import views

urlpatterns = [
	path('', RedirectView.as_view(url='payments')),
	path('login', views.login, name="pwa-login"),
	path('logout', views.logout, name="pwa-logout"),
	#path('index', views.index, name="pwa-index"),
	path('payments', views.payments, name="pwa-payments"),
	path('assistances', views.assistances, name="pwa-assistances"),
	path('set-pin', views.set_pin, name="pwa-set-pin"),
]

