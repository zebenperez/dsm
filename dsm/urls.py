from django.conf import settings
from django.contrib import admin
#from django.conf.urls.i18n import i18n_patterns
from django.urls import path, include
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.views.generic.base import RedirectView

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = [ 
	#url(r'^i18n/', include('django.conf.urls.i18n')),
	path('', RedirectView.as_view(url='studio/')),
	path('studio/', include('studio.urls')),
	path('champs/', include('champs.urls')),
	path('app/', include('pwa.urls')),
	path('rest-api/', include('rest.urls')),
	#path('accounts/login/$', auth_views.login, {'template_name': 'login.html'}, name="auth_login"),
	#path('logout/$', auth_views.logout, {'next_page': '/studio/'}),

    path('accounts/login/', auth_views.LoginView.as_view(template_name='login.html'), name="auth_login"),
    path('logout/', auth_views.LogoutView.as_view(next_page='/studio/')),
    path('admin/', admin.site.urls),
]

from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
urlpatterns += staticfiles_urlpatterns()
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

#] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

#urlpatterns += i18n_patterns(
#	url(r'^$', RedirectView.as_view(url='studio/')),
#	url(r'^studio/', include('studio.urls')),
#	url(r'^web/',include('web.urls')),
#)
