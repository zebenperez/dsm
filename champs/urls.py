from django.urls import path
from django.views.generic.base import RedirectView
from champs import views, auto_views


urlpatterns = [
    path('', RedirectView.as_view(url='champs/')),
    path('champs/', views.champs, name="champs"),
    path('champs-list/', views.champs_list, name="champs-list"),
    path('reconciliation/', views.bank_reconciliation, name="bank-reconciliation"),
    path('reconciliation/import/', views.import_bank_transactions, name="import-bank-transactions"),
    path('reconciliation/<int:transaction_id>/confirm/', views.confirm_bank_allocation, name="confirm-bank-allocation"),
    path('champs-form/', views.champs_form, name="champs-form"),
    path('champs-name-form/', views.champ_name_form, name="champs-name-form"),
    path('save-champ-name/', views.save_champ_name, name="save-champ-name"),
    path('champs-delete-form/', views.champ_delete_form, name="champs-delete-form"),
    path('delete-champ/', views.delete_champ, name="delete-champ"),
    path('champs-category-form/', views.champ_category_form, name="champs-category-form"),
    path('save-champ-category/', views.save_champ_category, name="save-champ-category"),
    path('champs-category-delete-form/', views.champ_category_delete_form, name="champs-category-delete-form"),
    path('delete-champ-category/', views.delete_champ_category, name="delete-champ-category"),
    path('champs-form/<int:obj_id>/', views.champs_details, name="champs-details"),
    path('champs-info-form/', views.champ_info_form, name="champs-info-form"),
    path('save-champ-info/', views.save_champ_info, name="save-champ-info"),
    path('champs-registration-form/', views.champ_registration_form, name="champs-registration-form"),
    path('add-champ-registration/', views.add_champ_registration, name="add-champ-registration"),
    path('champs-registration-payment-form/', views.champ_registration_payment_form, name="champs-registration-payment-form"),
    path('add-champ-registration-payment/', views.add_champ_registration_payment, name="add-champ-registration-payment"),
    path('champs-companion-payment-form/', views.champ_companion_payment_form, name="champs-companion-payment-form"),
    path('add-champ-companion-payment/', views.add_champ_companion_payment, name="add-champ-companion-payment"),
    path('champs-registration-delete-form/', views.champ_registration_delete_form, name="champs-registration-delete-form"),
    path('delete-champ-registration/', views.delete_champ_registration, name="delete-champ-registration"),
    path('champs-cost-form/', views.champ_cost_form, name="champs-cost-form"),
    path('save-champ-cost/', views.save_champ_cost, name="save-champ-cost"),
    path('champs-cost-delete-form/', views.champ_cost_delete_form, name="champs-cost-delete-form"),
    path('delete-champ-cost/', views.delete_champ_cost, name="delete-champ-cost"),

    path('save_reg/', views.save_reg, name="save_reg"),
    path('remove_reg/<int:reg_id>/', views.remove_reg, name="remove_reg"),
    path('upload_docs/', views.upload_docs, name="upload_docs"),
    path('profile/', views.profile, name="profile"),

    path('autosave_field/', auto_views.autosave_field, name='autosave_field'),
    path('autosave_fields/', auto_views.autosave_fields, name='autosave_fields'),
    path('autoremove_obj/', auto_views.autoremove_obj, name='autoremove_obj'),
    path('upload_file/', auto_views.upload_file, name="upload_file"),
    path('remove_file/', auto_views.remove_file, name="remove_file"),
]
