#from django.conf.urls import patterns, url, include
from django.urls import include, path
from rest import views
from rest_framework import routers
from rest_framework.authtoken import views as authtoken_views

router = routers.DefaultRouter()
router.register(r'payments', views.PaymentsViewSet)
router.register(r'assistances', views.AssistancesViewSet)
router.register(r'notifications', views.NotificationsViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('api-token-auth/', authtoken_views.obtain_auth_token),
]
