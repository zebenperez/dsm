from studio.models import *
from studio.dsm_forms import *
from django import forms
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.admin import DateFieldListFilter
from django.utils.timezone import utc
from django.utils.translation import ugettext as _  
from django.db.models import Max
from dateutil.relativedelta import relativedelta
from datetime import date, datetime
from django.utils.timezone import utc
import datetime 
import logging

#reload(sys)
#sys.setdefaultencoding("utf-8")
'''
    FILTERS
'''
class ExpiredFilter(SimpleListFilter):
    title = _('Bad debt')
    parameter_name = 'expire_date'

    def lookups(self, request, model_admin):
        return (
            ('bad_debt', _('bad debt')),
            ('in day', _('in day'))
        )

    def queryset(self, request, queryset):
        if self.value() == 'bad_debt':
            return queryset.exclude(payment__expire_date__gte = date.today()).distinct()
        if self.value() == 'in day':
            return queryset.filter(payment__expire_date__gte = date.today()).distinct()

'''
    INLINES
'''
class PaymentInLine(admin.TabularInline):
    model = Payment
    fields = ['enrolment', 'amount', 'date', 'expire_date']
    form = PaymentModelForm
    ordering = ['-date']
    extra = 1

'''
    MODEL ADMINS
'''
class TeacherAdmin(admin.ModelAdmin):
    fields = ['active', 'code', 'name', 'phone', 'email', 'user']
    list_display = ('name', 'code')

    def add_view(self, request, form_url="", extra_context=None):
        data = request.GET.copy()
        last_code = Teacher.objects.all().aggregate(Max('code'))['code__max'] 
        data['code'] = (last_code+1) if last_code != None else 1
        request.GET = data
        return super(TeacherAdmin, self).add_view(request, form_url="", extra_context=extra_context)

class StudentAdmin(admin.ModelAdmin):
	fields = ['code', 'pin', 'name', 'born_date', 'phone', 'email', 'picture', 'user']
	list_display = ('code', 'name', 'pin', 'phone')
	search_fields = ['name', 'code']
	#inlines = [PaymentInLine,]

	def add_view(self, request, form_url="", extra_context=None):
		data = request.GET.copy()
		last_code = Student.objects.all().aggregate(Max('code'))['code__max'] 
		data['code'] = (last_code+1) if last_code != None else 1
		request.GET = data
		return super(StudentAdmin, self).add_view(request, form_url="", extra_context=extra_context)

class GroupAdmin(admin.ModelAdmin):
	fieldsets = (
		(None, { 
			'fields': ('active', 'name', ('monday', 'tuesday', 'wednesday' ,'thursday', 'friday', 'saturday', 'sunday'), 'ini_time', 'end_time', 'teacher'), 
		}),
	)
	list_display = ('name', 'teacher', 'active')
	list_filter = ('active',)

class EnrolmentAdmin(admin.ModelAdmin):
	fieldsets = (
		(None, { 
			'fields': ('active', ('percent_studio', 'percent_teacher', 'price'), 'group', 'student'), 
		}),
	)
	#list_display = ('get_student_code', 'student', 'group', 'last_payment', 'last_payment_date', 'last_payment_expire', 'get_student_pin')
	list_display = ('get_student_code', 'student', 'group', 'last_payment', 'last_payment_date', 'get_student_pin', 'active')
	list_filter = (ExpiredFilter, 'active', 'group__name')
	search_fields = ['student__name', 'student__code']
	actions = ['active_enrolemnt', 'unactive_enrolment']
        
	def get_student_code(self, obj):
		return obj.student.code
	get_student_code.short_description = 'Code' 

	def get_student_pin(self, obj):
		return obj.student.pin
	get_student_pin.short_description = 'Pin' 

	def last_payment(self, obj):
		try:
			return obj.payment_set.all()[len(obj.payment_set.all())-1]
		except:
			return ""
	last_payment.short_description = 'Last payment amount'
	last_payment.allow_tags = True
	#last_payment.admin_order_field = 'manager'

	def last_payment_date(self, obj):
		try:
			payments = Payment.objects.filter(enrolment=obj).order_by("-pay_date")
			return payments[0].pay_date.strftime("%d - %B - %Y")
			#return obj.payment_set.all().order_by('date')[len(obj.payment_set.all())-1].date.strftime("%d - %B - %Y")
		except:
			return ""
	last_payment_date.short_description = 'Last payment date'
	last_payment_date.allow_tags = True

	def last_payment_expire(self, obj):
		try:
			lp = obj.payment_set.all()[len(obj.payment_set.all())-1]
			if lp.expire_date.date() < date.today():
				return "<span style='color: red'> %s </span>" % (lp.expire_date.strftime("%d - %B - %Y"))
			else:
				return "<span style='color: green'> %s </span>" % (lp.expire_date.strftime("%d - %B - %Y"))
		except Exception as e:
			print(e)
		return ""
	last_payment_expire.short_description = 'Last payment expire'
	last_payment_expire.allow_tags = True

	def active_enrolment(self, request, queryset):
		queryset.update(active=True)
	active_enrolment.short_description = "Mark selected stories as active"

	def unactive_enrolment(self, request, queryset):
		queryset.update(active=False)
	unactive_enrolment.short_description = "Mark selected stories as unactive"

	def formfield_for_foreignkey(self, db_field, request, **kwargs):
		if db_field.name == "group":
			kwargs["queryset"] = Group.objects.filter(active=True)
		return super(EnrolmentAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

class ConceptAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, { 
	    'fields': ('code', 'name'), 
	}),
    )

class PaymentAdmin(admin.ModelAdmin):
	fields = ['date', 'expire_date', 'amount', 'student', 'enrolment']
	#list_display = ('student', 'enrolment', 'date', 'expire_date', 'check_date')
	list_display = ('student', 'enrolment', 'pay_date', 'expire_date')
	list_filter = (('date', DateFieldListFilter),)
	search_fields = ['student__name', 'student__code']
	now = datetime.datetime.utcnow().replace(tzinfo=utc)

#    def check_date(self, obj):
#        return '<div style="color:green">Debtor</div>' if obj.expire_date < datetime.datetime.utcnow().replace(tzinfo=utc) else '<div style="color:green">On date</div>'
#    check_date.short_description = 'Inpayment'  
#    check_date.allow_tags = True

	def add_view(self, request, form_url="", extra_context=None):
		data = request.GET.copy()
		next_month = datetime.datetime.utcnow().replace(tzinfo=utc) + relativedelta(months=+1)
		data['expire_date'] = next_month
		request.GET = data
		return super(PaymentAdmin, self).add_view(request, form_url="", extra_context=extra_context)

class TeacherPaymentAdmin(admin.ModelAdmin):
	fieldsets = (
		(None, { 
			'fields': ('note', 'date', 'amount', 'teacher', 'concept'), 
		}),
	)

class ArticleAdmin(admin.ModelAdmin):
	fieldsets = (
		(None, { 
			'fields': ('code', 'name', 'cost', 'pvp', 'stock'), 
		}),
	)
	list_display = ('code', 'name')

class ArticlePaymentAdmin(admin.ModelAdmin):
	fieldsets = (
		(None, { 
			'fields': ('note', 'date', 'amount', 'article', 'concept'), 
		}),
	)

class CashAdmin(admin.ModelAdmin):
	fieldsets = (
		(None, { 
			'fields': ('date', ('i_card', 'e_card'), ('i_50000', 'i_20000', 'i_10000', 'i_05000', 'i_02000', 'i_01000', 'i_00500', 'i_00200', 'i_00100', 'i_00050', 'i_00020', 'i_00010', 'i_00005', 'i_00002', 'i_00001'), ('e_50000', 'e_20000', 'e_10000', 'e_05000', 'e_02000', 'e_01000', 'e_00500', 'e_00200', 'e_00100', 'e_00050', 'e_00020', 'e_00010', 'e_00005', 'e_00002', 'e_00001'), ('i_total', 'e_total'), ('i_note', 'e_note')), 
		}),
	)

class NotificationAdmin (admin.ModelAdmin):
	list_display = ('date', 'msg')

admin.site.register(Article, ArticleAdmin)
admin.site.register(ArticlePayment, ArticlePaymentAdmin)
admin.site.register(Assistance)
admin.site.register(Cash, CashAdmin)
admin.site.register(Concept, ConceptAdmin)
admin.site.register(Enrolment, EnrolmentAdmin)
admin.site.register(Group, GroupAdmin)
admin.site.register(Notification, NotificationAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(Student, StudentAdmin)
admin.site.register(Teacher, TeacherAdmin)
admin.site.register(TeacherPayment, TeacherPaymentAdmin)
