from django import forms
from django.db import models
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from studio.models import *

import datetime

class CashForm(forms.ModelForm):
	i_note = forms.CharField(widget=forms.Textarea(attrs={'cols': 60, 'rows': 5}), required=False)
	e_note = forms.CharField(widget=forms.Textarea(attrs={'cols': 60, 'rows': 5}), required=False)
	i_card = forms.IntegerField(widget=forms.HiddenInput(), required=False)

	class Meta:
		model = Cash 
		fields = "__all__"

class EnrolmentForm (forms.ModelForm):
	active = forms.BooleanField(initial=True)
	#creation_date = forms.DateTimeField(initial=datetime.datetime.now())
	percent_studio = forms.IntegerField(initial=50, label=_("Studio"))
	percent_teacher = forms.IntegerField(initial=50, label=_("Teacher"))
	price = forms.DecimalField(initial=30)
	
	class Meta:
		model = Enrolment;
		fields = "__all__"

class PaymentModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(PaymentModelForm, self).__init__(*args, **kwargs)
        next_month = datetime.datetime.utcnow().replace(tzinfo=utc) + relativedelta(months=+1)
        self.initial['expire_date'] = next_month

    class Meta:
        model = Payment
        fields = "__all__"

class StudentForm (forms.ModelForm):
	#creation_date = forms.DateTimeField(initial=datetime.datetime.now())
	#born_date = forms.DateTimeField(initial=None, required=False) 
	born_date = forms.DateField(input_formats=settings.DATE_INPUT_FORMATS) 
	#user = forms.IntegerField(initial=None, required=False)
	#email = forms.EmailField(required=False)
	
	class Meta:
		model = Student;
		fields = "__all__"

class TeacherPaymentForm(forms.ModelForm):
	date = forms.DateField(input_formats=settings.DATE_INPUT_FORMATS) 
	#def __init__(self, *args, **kwargs):
		#super(ModelForm, self).__init__(*args, **kwargs)
		#self.fields['date'].widget.format = '%d-%m-%Y'

	class Meta:
		model = TeacherPayment
		exclude = ['teacher']
	
