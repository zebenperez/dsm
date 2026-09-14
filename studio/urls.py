from django.urls import path, re_path
from django.views.generic.base import RedirectView
from studio import views

urlpatterns = [
	#path('', RedirectView.as_view(url='tpv/')),
	path('', views.index, name="index"),
	path('tpv/', views.tpv, name="tpv"),
	path('search/', views.search, name="search"),
	path('pay/', views.pay, name="pay"),
	path('<int:payment_id>/delete_payment/', views.delete_payment, name="delete_payment"),
	re_path('tpv/(?P<current_date>\d{2}-\d{2}-\d{4})/', views.tpv),
	path ('pin/', views.set_pins, name='pins'),
	path ('new_enrolment/', views.new_enrolment, name='new_enrolment'),
	path ('baja_enrolment/', views.baja_enrolment, name='baja_enrolment'),
	path ('student_profile/', views.student_profile, name='student_profile'),

	## TEACHERS
	path('teachers/', views.teachers, name="teachers"),
	path('teachers/<int:teacher_id>/', views.teachers, name="teachers"),
	#path('teachers/(?P<code>d+)/(?P<name>w+)/(?P<ini_date>\d{2}-\d{2}-\d{4})/(?P<end_date>\d{2}-\d{2}-\d{4})/$', 'studio.views.teachers'),
	path('save_teacher_payment/', views.save_teacher_payment, name="save_teacher_payment"),
	path('<int:teacher_payment_id>/delete_teacher_payment/', views.delete_teacher_payment, name="delete_teacher_payment"),

	## ARTICLES
	path('<int:article_payment_id>/delete_article_payment/', views.delete_article_payment, name="delete_article_payment"),
	path('article_search/', views.article_search, name="article_search"),
	path('article_pay/', views.article_pay, name="article_pay"),

	## CASH
	path('cash/', views.cash, name="cash"),
	path('<int:cash_id>/save_cash/', views.save_cash, name="save_cash"),
	#path('(?P<current_date>\d{2}-\d{2}-\d{4})/', views.cash),
	re_path('cash/(?P<current_date>\d{2}-\d{2}-\d{4})/', views.cash, name="save_cash_date"),
	path('cash/(?P<current_date>\d{2}-\d{2}-\d{4})/<slug:msg>/', views.cash, name="save_cash_date_msg"),
	re_path('cash_test/(?P<msg>.*)$', views.cash_test),

	## ENROLMENTS
	path ('enrolment/add/', views.add_enrolment, name='add_enrolment'),

	## PAYMENTS
	path ('payments/', views.payments,name='payments'),
	path ('article_payments/', views.article_payments,name='article_payments'),
	path ('bad_debt/', views.bad_debt, name='bad_debt'),

	##STUDENTS
	path ('student/edit/<int:student_id>/', views.edit_student,name="edit_student"),

	##ASSISTANCES
	re_path ('assistances/(?P<search_date>\d{2}-\d{2}-\d{4})/', views.assistances, name='assistances'),
	path ('assistances/<int:assistance_id>/', views.assistances, name='assistances'),
	path ('assistances/', views.assistances, name='assistances'),
	path ('assistances_save/', views.assistances_save,name='assistances_save'),
	path ('assistances_delete/<int:assistance_id>/', views.assistances_delete,name='assistances_delete'),
	path ('no_assistance/', views.no_assistance, name='no_assistance'),
	path ('assistances_baja/', views.assistances_baja, name='assistances_baja'),

	##NOTIFICATIONS
	path ('notifications/', views.notifications, name='notifications'),
	path ('notification_add/', views.notification_add, name='notification_add'),
	path ('notification_save/', views.notification_save, name='notification_save'),
	path ('notification_delete/<int:notification_id>/', views.notification_delete, name='notification_delete'),
	path ('notification_send/<int:notification_id>/', views.notification_send, name='notification_send'),

	## FORMULARIOS
	path('forms/', views.registration_forms, name='registration_forms'),
	path('forms/<int:form_id>/', views.registration_form_responses, name='registration_form_responses'),

	##PULSERAS
	path ('wristbands/', views.wristbands, name='wristbands'),
]
