from django.urls import path
from django.views.generic.base import RedirectView
from champs import views, auto_views


urlpatterns = [
    path('', RedirectView.as_view(url='champs/')),
    path('champs/', views.champs, name="champs"),
    path('save_reg/', views.save_reg, name="save_reg"),
    path('remove_reg/<int:reg_id>/', views.remove_reg, name="remove_reg"),
    path('upload_docs/', views.upload_docs, name="upload_docs"),
    path('profile/', views.profile, name="profile"),

    path('autosave_field/', auto_views.autosave_field, name='autosave_field'),
    path('autoremove_obj/', auto_views.autoremove_obj, name='autoremove_obj'),
    path('upload_file/', auto_views.upload_file, name="upload_file"),
    path('remove_file/', auto_views.remove_file, name="remove_file"),
]

