# -*- encoding: utf-8 -*-

from dateutil.relativedelta import relativedelta
from django import template
from datetime import date, datetime
from django.utils.timezone import utc
from studio.models import *

register = template.Library()

@register.filter
def contains(value, arg):
    return value in arg

@register.simple_tag
def get_color(enrolment):
    payments = Payment.objects.order_by("-pay_date").filter(enrolment = enrolment)
    if (len(payments) == 0):
        return "blue"
    elif (payments[0].expire_date.date() < date.today()):
        return "red"
    else:
        return "green"

    return color

@register.simple_tag
def get_expire_date(enrolment):
    payments = Payment.objects.order_by("-pay_date").filter(enrolment = enrolment)
    #expire_date = enrolment.creation_date + relativedelta(months=+1) if (len(payments) == 0) else payments[0].expire_date
    DATE_FORMAT = "%d-%m-%Y"
    #return expire_date.strftime(DATE_FORMAT)
    #Si no ha pagado nunca
    if (len(payments) == 0):
        expire_date = enrolment.creation_date + relativedelta(months=+1)
        #expire_date = datetime(expire_date.year, expire_date.month, 15)
    else:
        #expire_date = payments[0].expire_date + relativedelta(months=+1)
        expire_date =  payments[0].pay_date + relativedelta(months=+2)

    return expire_date.strftime(DATE_FORMAT)

@register.simple_tag
def get_expire_date2(enrolment):
	payments = Payment.objects.order_by("-pay_date").filter(enrolment = enrolment)
	DATE_FORMAT = "%d-%m-%Y"
	#Si no ha pagado nunca
	if (len(payments) == 0):
		#date = enrolment.creation_date + relativedelta(months=+1)
		date = datetime.datetime(enrolment.creation_date.year, enrolment.creation_date.month, 1) + relativedelta(months=+1)
		return date.strftime(DATE_FORMAT)
	else:
		# Si el pago es del mes actual, devuelve hoy
		today = datetime.datetime.today()
		if (payments[0].expire_date.month == today.month) and (payments[0].expire_date.year == today.year):
			#date = today + relativedelta(months=+1)
			date = datetime.datetime(today.year, today.month, 1) + relativedelta(months=+1)
			return date.strftime(DATE_FORMAT)
		else:
			#Si el ultimo pago es del mes actual, el proximo pago es el 1 del mes que viene
			if (payments[0].pay_date.month == today.month) and (payments[0].pay_date.year == today.year):
				pay_date = payments[0].pay_date  + relativedelta(months=+1)
				pay_date = datetime.datetime(pay_date.year, pay_date.month, 1) + relativedelta(months=+1)
				return pay_date.strftime(DATE_FORMAT)
			#Si faltan meses por pagar
			else:
				#pay_date = payments[0].pay_date  + relativedelta(months=+2)
				pay_date = datetime.datetime(payments[0].pay_date.year, payments[0].pay_date.month, 1) + relativedelta(months=+2)
				return pay_date.strftime(DATE_FORMAT)


@register.simple_tag
def get_pay_date(enrolment):
    payments = Payment.objects.order_by("-pay_date").filter(enrolment = enrolment)
    DATE_FORMAT = "%d-%m-%Y"
    #Si no ha pagado nunca
    if (len(payments) == 0):
        return enrolment.creation_date.strftime(DATE_FORMAT)
    else:
        # Si el pago es del mes actual, devuelve hoy
        today = datetime.datetime.today()
        if (payments[0].expire_date.month == today.month) and (payments[0].expire_date.year == today.year):
            return today.strftime(DATE_FORMAT)
        else:
            #Si el ultimo pago es del mes actual, el proximo pago es el 1 del mes que viene
            if (payments[0].pay_date.month == today.month) and (payments[0].pay_date.year == today.year):
                pay_date = payments[0].pay_date  + relativedelta(months=+1)
                pay_date = datetime.datetime(pay_date.year, pay_date.month, 1)
                return pay_date.strftime(DATE_FORMAT)
            #Si faltan meses por pagar
            else:
                pay_date = payments[0].pay_date  + relativedelta(months=+1)
                return pay_date.strftime(DATE_FORMAT)

@register.simple_tag
def get_total_amount(payment_list):
    total = 0
    for p in payment_list:
        total += p.amount
    return total

@register.simple_tag
def get_teacher_amount(teacher_id, group_id, student, ini_date, end_date):
	total = 0
	if teacher_id:
		#total_studio_payment = Payment.objects.filter(pay_date__range=(ini_date, end_date), enrolment__group__teacher__id = teacher_id)
		kwargs = {'pay_date__range': (ini_date, end_date), 'amount__gt': 0,}
		if teacher_id != "":
			kwargs['enrolment__group__teacher__id'] = teacher_id
		if group_id != "":
			kwargs['enrolment__group__id'] = group_id
		if student != "":
			if student.isdigit():
				kwargs['enrolment__student__code'] = student
			else:
				kwargs['enrolment__student__name__unaccent__icontains'] = student
		total_studio_payment = Payment.objects.filter(**kwargs).order_by('enrolment__student__name', 'pay_date', 'enrolment__group__name')

		for p in total_studio_payment:
			aux = float(p.amount) * (float(p.enrolment.percent_teacher) * float(0.01))
			total = total + round(float(aux), 2)
	return total

@register.simple_tag
def check_assistance(enrol, assistance):
	if assistance != "":
		for ae in assistance.enrolments.all():
			if ae == enrol:
				return "1"
	return "0"

@register.simple_tag
def check_assistance_class(enrol, assistance):
	if assistance != "":
		for ae in assistance.enrolments.all():
			if ae == enrol:
				return "list-group-item-success"
	return ""
	
@register.simple_tag
def get_no_assistances(assistance):
	assistances = len(assistance.enrolments.all())
	total_enrolments = Enrolment.objects.filter(active = True, group__id = assistance.group.id)
	return len(total_enrolments) - assistances

@register.simple_tag
def get_group_name(group_id):
	try:
		return Group.objects.get(pk = group_id)
	except:
		return ""

@register.simple_tag
def get_student_age(born_date):
	try:
		print(born_date)
		res = date.today() - born_date
		return "(%.0f años)" % (res.days / 365)
	except:
		return ""

