from django.conf.urls import patterns, include, url
from django.views.generic.base import RedirectView
from web import views


urlpatterns = [
	url(r'^$', views.index, name="web_home"),

]

