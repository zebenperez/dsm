# -*- encoding: utf-8 -*-

from studio.models import *
from studio.dsm_forms import *
from datetime import date, datetime, timezone
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from django.db.models import Q, Count, Min, Sum, Max, Avg
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.middleware import csrf
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect, reverse
from django.utils.translation import gettext as _
from django.utils import timezone as django_timezone
from django.utils.html import strip_tags
from web.utils import *

from operator import attrgetter

import calendar
from dateutil.relativedelta import relativedelta
 
from django import forms
from studio.dsm_forms import *
from studio.decorators import group_required
from studio.common_lib import get_student

#from push_notifications.models import APNSDevice, GCMDevice
from fcm_django.models import FCMDevice
from registration_forms.models import Form as RegistrationForm, FormSubmission

'''
	TPV
'''
@login_required
def index(request):
    if request.user.groups.filter(name="student").exists():
        return redirect("champs")
    return redirect("tpv")


@group_required("reception")
def registration_forms(request):
    state = request.GET.get('state', 'open')
    now = django_timezone.now()
    form_list = RegistrationForm.objects.annotate(response_count=Count('submissions'))
    if state == 'open':
        form_list = form_list.filter(is_published=True).filter(
            Q(deadline__isnull=True) | Q(deadline__gte=now)
        )
    elif state == 'closed':
        form_list = form_list.filter(
            Q(is_published=False) | Q(deadline__lt=now)
        )
    else:
        state = 'all'
    return render(request, 'forms/forms.html', {
        'form_list': form_list.order_by('-created_at'),
        'state': state,
    })


@group_required("reception")
def registration_form_responses(request, form_id):
    form = get_object_or_404(RegistrationForm, pk=form_id)
    questions = list(form.questions.all())
    submission_list = list(
        FormSubmission.objects.filter(form=form)
        .select_related('student')
        .prefetch_related('answers__question')
        .order_by('student__name')
    )
    for submission in submission_list:
        answers = {answer.question_id: answer.value for answer in submission.answers.all()}
        submission.answer_values = [answers.get(question.id, '—') for question in questions]
    return render(request, 'forms/form_responses.html', {
        'form': form,
        'questions': questions,
        'submission_list': submission_list,
    })

@group_required("reception")
def tpv(request, current_date = None, msg = None):
    if (current_date == None):
        current_date = date.today()
    else: 
        current_date = datetime.datetime.strptime(current_date, "%d-%m-%Y")
		  
    tab = request.GET.get('t', 'student')
    current_code = request.GET.get('current_code')
    msg = request.GET.get('msg')
    current_enrol = request.GET.get('current_enrol')
  
    # Se muestran los pagos del ultimo usuario que haya padado
    enrolment_list = None
    if current_code != None:
        enrolment_list = Enrolment.objects.filter(student__code = current_code, active = True)
    
    payment_list = Payment.objects.filter(date__gte = current_date).order_by('-id')
    article_payment_list = ArticlePayment.objects.order_by('-date').filter(date__gte = current_date)
    article_list = Article.objects.filter(publish=True)
    group_list = Group.objects.filter(active=True)
    concept_list = Concept.objects.all()
    context = {
        'tab':request.GET.get('t','student'),
        'payment_list': payment_list, 
        'article_payment_list': article_payment_list, 
        'current_date': current_date, 
        'article_list': article_list, 
        'concept_list': concept_list, 
        'enrolment_list': enrolment_list, 
        'group_list': group_list, 
        'current_code': current_code,
        'current_enrol': current_enrol,
        'msg': msg
    }
    return render(request, 'tpv/tpv.html', context)

@login_required
def search(request, code = None):
	if request.method == 'POST':
		code = "" if (request.POST["code"] == "") else request.POST["code"]
		name = "" if (request.POST["name"] == "") else request.POST["name"].lstrip()

	enrolment_list = Enrolment.objects.all();
	if len(code) > 0:
		enrolment_list = enrolment_list.filter(student__code = code).filter(active = True)
	if len(name) > 0:
		#enrolment_list = enrolment_list.filter(student__name__unaccent__icontains = name, active = True)
		enrolment_list = enrolment_list.filter(student__name__icontains = name, active = True)
	
	group_list = Group.objects.filter(active=True)
    
	return render(request, 'tpv/tpv_student_payment_form.html', {"enrolment_list": enrolment_list, "group_list": group_list})

@login_required
def pay(request):
	if request.method == 'POST':
		e = get_object_or_404(Enrolment, pk=request.POST["enrolment_id"])
		today = date.today()
		amount = Decimal(request.POST["amount"].replace(",", "."))
		pay_date = datetime.datetime.strptime(request.POST["pay_date"], "%d-%m-%Y")
		expire_date = datetime.datetime.strptime(request.POST["expire_date"], "%d-%m-%Y")
		payment = Payment(date = today, pay_date = pay_date, expire_date = expire_date, amount = amount, student = e.student, enrolment = e) 
		payment.save()
	return redirect('/studio/tpv/?current_code='+str(e.student.code))
	#return redirect('/studio/tpv/')

@login_required
def delete_payment(request, payment_id):
	a = get_object_or_404(Payment, pk=payment_id)
	code = a.student.code
	a.delete()
	return redirect('/studio/tpv/?current_code='+str(code))
	#return redirect('/studio/')

@login_required
def new_enrolment(request):
	if request.method == 'POST':
		try:
			group = Group.objects.get(pk=request.POST["group"])
			student = Student.objects.get(pk=request.POST["student"])
			enrolment = Enrolment(percent_studio=request.POST["studio"], percent_teacher=request.POST["teacher"], price=request.POST["price"], group=group, student=student)
			enrolment.save()
			return redirect('/studio/tpv/?current_code='+str(student.code))
		except Exception as e:
			print(e)
	return redirect('/studio/tpv/')

@login_required
def baja_enrolment(request):
	if request.method == 'POST':
		try:
			enrolment = Enrolment.objects.get(pk = request.POST["enrolment"])
			enrolment.active = False
			enrolment.save()
			return redirect('/studio/tpv/?current_code='+str(enrolment.student.code))
		except Exception as e:
			print(e)
	return redirect('/studio/tpv/')

@login_required
def student_profile(request):
	if request.method == 'POST':
		try:
			enrolment = Enrolment.objects.get(pk = request.POST["enrolment"])
			try:
				date = datetime.datetime.strptime(request.POST["born_date"], "%d-%m-%Y")
				student = enrolment.student
				student.code = request.POST["code"]
				student.pin = request.POST["pin"]
				student.born_date = date
				student.phone = request.POST["phone"]
				student.email = request.POST["email"]
				if "picture" in request.FILES:
					student.picture = request.FILES["picture"]
				student.save()
				msg = "OK"
			except Exception as e:
				#msg = '; '.join(e.messages) if e.messages != None else e
				msg = e.message
			return redirect('/studio/tpv/?current_code='+str(enrolment.student.code)+"&current_enrol="+str(enrolment.id)+"&msg="+msg)
		except Exception as e:
			print(e)
	return redirect('/studio/tpv/')

'''
    TEACHERS
'''
class TeacherPaymentView(object):
	def __init__(self, teacher, payments, total_amount, total_teacher, total_studio, total_payments, diff, student_payments):
		self.teacher = teacher
		self.payments = payments
		self.total_amount = total_amount
		self.total_teacher = total_teacher
		self.total_studio = total_studio
		self.total_payments = total_payments
		self.diff = diff
		self.student_payments = student_payments

@login_required
def teachers(request, teacher_id = None):
	if request.method == 'POST':
		ini_date = datetime.datetime.strptime(request.POST["ini_date"], "%d-%m-%Y") if (request.POST["ini_date"]) else date.today()
		end_date = datetime.datetime.strptime(request.POST["end_date"], "%d-%m-%Y") if (request.POST["end_date"]) else date.today()
		current_teacher = request.POST["name"]
		if current_teacher == "":
			teachers = Teacher.objects.filter(active=True)
		else:
			teachers = Teacher.objects.filter(id = current_teacher)
	else:
		today = date.today()
		ini_date = today.replace(day = 1)
		end_date = datetime.datetime(today.year, today.month, calendar.mdays[today.month], 23, 59, 59)
		current_teacher = ""
		teachers = Teacher.objects.filter(active=True)

	teacher_list = []
	for t in teachers:
		total = 0
		total_studio = 0
		payments = TeacherPayment.objects.filter(date__range=(ini_date, end_date)).filter(teacher = t)
		total_payments_query = TeacherPayment.objects.filter(date__range=(ini_date, end_date)).filter(teacher = t).values('teacher').annotate(total_amount = Sum('amount'))
		total_studio_payment = Payment.objects.filter(pay_date__range=(ini_date, end_date)).filter(enrolment__group__teacher = t)
		for p in total_studio_payment:
			total = total + p.amount
			aux = float(p.amount) * (float(p.enrolment.percent_studio) * float(0.01))
			total_studio = total_studio + round(float(aux), 2)

		total_payments = total_payments_query[0]['total_amount'] if (len(total_payments_query) > 0) else 0
		total_teacher = float(total) - total_studio
		diff = float(total) - float(total_payments) - total_studio

		tp = TeacherPaymentView(teacher = t, payments = payments, total_amount = total, total_teacher = total_teacher, total_studio = total_studio, total_payments = total_payments, diff = diff, student_payments = total_studio_payment)
		teacher_list.append(tp)

	form = TeacherPaymentForm()
	context = {
		'teacher_list': teacher_list, 
		'form': form, 
		'ini_date': ini_date, 
		'end_date': end_date,
		'current_teacher': current_teacher,
		'teacher_list_search': Teacher.objects.filter(active=True), 
		'concept_list': Concept.objects.all(),
		'current_teacher_id': teacher_id,
		'today': datetime.datetime.today(),
	}
	return render(request, 'teachers/teachers.html', context)

@login_required
def save_teacher_payment(request):
	if request.method == 'POST':
		form = TeacherPaymentForm(request.POST or None)
		if form.is_valid():
			new_obj = form.save(commit=False)
			teacher = Teacher.objects.get(pk=request.POST["teacher_id"])
			new_obj.teacher = teacher
			new_obj.save()
			return redirect('/studio/teachers/'+str(teacher.id)+'/')
	return redirect('/studio/teachers/')

@login_required
def delete_teacher_payment(request, teacher_payment_id):
	a = get_object_or_404(TeacherPayment, pk=teacher_payment_id)
	teacher = a.teacher
	a.delete()
	return redirect('/studio/teachers/'+str(teacher.id)+'/')

'''
    ARTICLES
'''
@login_required
def delete_article_payment(request, article_payment_id):
	a = get_object_or_404(ArticlePayment, pk=article_payment_id)
	art = a.article
	a.delete()

	art.stock += 1
	art.save()
	return redirect('/studio/tpv/?t=article')

@login_required
def article_search(request):
	if request.method == 'POST':
		#code = 0 if (request.POST["code_article"] == "") else request.POST["code_article"]
		name = request.POST["name_article"]
		concept_list = Concept.objects.all()
		#article_list = Article.objects.filter(Q(code__icontains = code) | Q(name__icontains = name))
		article_list = Article.objects.filter(Q(name__icontains = name), publish=True)
	return render(request, 'article_payment_form.html', {"article_list": article_list, "concept_list": concept_list})

@login_required
def article_pay(request):
	if request.method == 'POST':
		a = get_object_or_404(Article, pk=request.POST["article_id"])
		today = date.today()
		amount = Decimal(request.POST["amount"].replace(",", "."))
		concept = Concept.objects.get(code=request.POST["concept"])
		card = False
		if 'card' in request.POST:
			card = True
		
	article_payment = ArticlePayment(note = request.POST["note"], date = today, amount = amount, article = a, concept = concept, card = card) 
	article_payment.save()
	a.stock -= 1
	a.save()
	return redirect('/studio/tpv/?t=article')

'''
	CASH
'''
def calculate_amount(current_date, positive):
	date_min = datetime.datetime.combine(current_date, datetime.time.min)
	if positive:
		pays = Payment.objects.filter(date = current_date).filter(amount__gte = 0).filter(card = False).aggregate(Sum('amount'))['amount__sum']
		teacher_pays=TeacherPayment.objects.filter(date=current_date).filter(amount__gte=0).filter(card=False).aggregate(Sum('amount'))['amount__sum']
		article_pays=ArticlePayment.objects.filter(date__gt=date_min).filter(amount__gte=0).filter(card=False).aggregate(Sum('amount'))['amount__sum']
	else:
		pays = Payment.objects.filter(date = current_date).filter(amount__lt = 0).filter(card = False).aggregate(Sum('amount'))['amount__sum']
		teacher_pays=TeacherPayment.objects.filter(date=current_date).filter(amount__lt=0).filter(card=False).aggregate(Sum('amount'))['amount__sum']
		article_pays=ArticlePayment.objects.filter(date__gt=date_min).filter(amount__lt=0).filter(card=False).aggregate(Sum('amount'))['amount__sum']

	pay_amounts = pays if pays != None else 0
	teacher_pay_amounts = teacher_pays if teacher_pays != None else 0
	article_pay_amounts = article_pays if article_pays != None else 0

	return (pay_amounts + teacher_pay_amounts + article_pay_amounts)

def calculate_card(current_date):
	pays = Payment.objects.filter(date = current_date).filter(card = True).aggregate(Sum('amount'))['amount__sum']
	article_pays = ArticlePayment.objects.filter(date = current_date).filter(card = True).aggregate(Sum('amount'))['amount__sum']

	pay_amounts = pays if pays != None else 0
	article_pay_amounts = article_pays if article_pays != None else 0

	return (pay_amounts + article_pay_amounts)

@login_required
def cash(request, current_date = None, msg = None):
	if current_date == None:
		current_date = date.today()
	else: 
		current_date = datetime.datetime.strptime(current_date, "%d-%m-%Y")

	cashs = Cash.objects.order_by("id").filter(date__gte=current_date)
	#cashs = Cash.objects.order_by("id").filter(date__year=current_date.year, date__month=current_date.month, date__day=current_date.day)
	if len(cashs) > 0:
		cash = cashs[0]
	else:
		cash = Cash(date = current_date)
		cash.save()

	billing_positive = calculate_amount(current_date, True)
	billing_negative = calculate_amount(current_date, False)
	billing_card = calculate_card(current_date)

	i_total = cash.i_total if cash.i_total != None else 0
	e_total = cash.e_total if cash.e_total != None else 0
	e_card = cash.e_total if cash.e_total != None else 0

	total_billing = billing_positive + billing_negative
	total = i_total + billing_positive + billing_negative #Falta por controlar los pagos por tarjeta
	total_cash = e_total + e_card
	diff = total - total_cash

	form = CashForm(instance = cash)
	return render(request, 'cash.html', {'form': form, 'cash': cash, 'current_date': current_date, 'amounts_positive': billing_positive, 'amounts_negative': billing_negative, 'total': total, 'total_cash': total_cash, 'total_billing': total_billing, 'billing_card': billing_card, 'diff': diff, 'msg': msg})

@login_required
def save_cash(request, cash_id):
    instance = get_object_or_404(Cash, id=cash_id)
    form = CashForm(request.POST or None, instance=instance)
    d = instance.date.strftime("%d-%m-%Y")
    if form.is_valid():
        form.save()
        return redirect(reverse('save_cash_date', args=[d]))
    else:
        msg = "Post invalid: %s" % (form.errors)
        return redirect(reverse('save_cash_date_msg', args=[d, msg]))

@login_required
def cash_test(request, msg):
    return render(request, 'cash_test.html', {'msg': msg})

'''
	Students
'''
@login_required
def add_enrolment(request):
	if request.user.is_staff:
		last_code = Student.objects.all().order_by('-code')
		last_code = last_code[0].code
		last_code = int(last_code) + 1
		enrolment_form = EnrolmentForm()
		enrolment_form.fields["group"].queryset = Group.objects.filter(active = True)
		context ={
			'form_enrolment': enrolment_form,
			'form_student' : StudentForm(),
			'code_default' : last_code,
		}

	if request.method == 'POST':
		create_student = request.POST.get('create_student',False)
		if create_student == "True" : 
			msg = "Ha habido algun problema al crear la matricula"
			form_student = StudentForm(request.POST)
			if form_student.is_valid():
				student = form_student.save();
				post = request.POST.copy()
				post['student'] = student.id
				form_enrolment = EnrolmentForm(post)
				if form_enrolment.is_valid():
					form_enrolment.save()
					messages.add_message(request, messages.INFO, _("Matricula creada correctamente!"))
					#return redirect(add_enrolment, form_enrolment)
				context['form_enrolment'] = form_enrolment
				msg = "%s (%s)" % (msg, form_enrolment.errors)
			context['form_student'] = form_student
			msg = "%s (%s)" % (msg, form_student.errors)
			messages.add_message(request, messages.ERROR, msg)
		else:
			form_enrolment = EnrolmentForm(request.POST)
			if form_enrolment.is_valid():
				form_enrolment.save();
				messages.add_message(request, messages.INFO, _("Matricula creada correctamente"))
				#return redirect(add_enrolment, form_enrolment)
		
	return render(request,'enrolment_form.html', context)

@login_required
def edit_student(request, student_id):
	if request.user.is_superuser:
		student = get_element(Student,int(student_id)) 
		context={}
		if student != False:
			form  = StudentForm(instance=student);
			if request.method == 'POST':
				form = StudentForm(request.POST, request.FILES, instance=student)
				if form.is_valid():
					student = form.save();
					msg = _("Edicion realizada con exito")
					messages.add_message(request, messages.INFO, msg)
				else:
					#msg = _("Ha habido algun problema al guardar el formulario (%s)" % (form.errors))
					msg = _("Ha habido algun problema al guardar el formulario")
					messages.add_message(request, messages.ERROR, msg)
			context['form_student'] = form
			context['picture'] = student.picture
			#context['student'] = student
	
	return render(request, "edit_student.html", context);

@login_required
def set_pins(request):
	students = Student.objects.all()
	chars = string.ascii_uppercase + string.digits
	for s in students:
		new_pin = ""
		while True:
			new_pin = ''.join(random.choice(chars) for i in range(4))
			if not Student.objects.filter(pin=new_pin).exists():
				break
		s.pin = new_pin
		s.save()
	return redirect('/studio/')

'''
    Payments
'''
@login_required
def payments(request):	
	current_teacher = ""
	current_group = ""
	current_student = ""
	teacher_list = Teacher.objects.filter(user = request.user)
	if len(teacher_list) > 0:
		current_teacher = teacher_list[0].id
	else:
		teacher_list = Teacher.objects.filter(active=True)
	if request.method == 'POST':
		ini_date = datetime.datetime.strptime(request.POST["ini_date"], "%d-%m-%Y") if (request.POST["ini_date"]) else date.today()
		end_date = datetime.datetime.strptime(request.POST["end_date"], "%d-%m-%Y") if (request.POST["end_date"]) else date.today()
		current_teacher = request.POST["teacher"]
		current_group = request.POST["group"]
		current_student = request.POST["student"]
	else: 
		today = date.today()
		ini_date = today.replace(day = 1)
		end_date = datetime.datetime(today.year, today.month, calendar.mdays[today.month], 23, 59, 59)

	kwargs = {'pay_date__range': (ini_date, end_date), 'amount__gt': 0,}
	if current_teacher != "":
		kwargs['enrolment__group__teacher__id'] = current_teacher
	if current_group != "":
		kwargs['enrolment__group__id'] = current_group
	if current_student != "":
		if current_student.isdigit():
			kwargs['enrolment__student__code'] = current_student
		else:
			kwargs['enrolment__student__name__unaccent__icontains'] = current_student
	payment_list = Payment.objects.filter(**kwargs).order_by('enrolment__student__name', 'pay_date', 'enrolment__group__name')

	context = {
		'teacher_list': teacher_list,
		'group_list': Group.objects.filter(active = True),
		'ini_date': ini_date,
		'end_date': end_date,
		'current_teacher': current_teacher,
		'current_group': current_group,
		'current_student': current_student,
		'payment_list': payment_list
	}

	return render(request, 'payments/payments.html', context)

@login_required
def article_payments(request):	
    if request.method == 'POST':
        ini_date = datetime.datetime.strptime(request.POST["ini_date"], "%d-%m-%Y") if (request.POST["ini_date"]) else date.today()
        end_date = datetime.datetime.strptime(request.POST["end_date"], "%d-%m-%Y") if (request.POST["end_date"]) else date.today()
        period_end = end_date + datetime.timedelta(days=1)
    else: 
        today = date.today()
        ini_date = today.replace(day = 1)
        end_date = datetime.datetime(today.year, today.month, calendar.mdays[today.month], 23, 59, 59)
        period_end = end_date + datetime.timedelta(seconds=1)

    article_list = Article.objects.filter(publish=True).order_by('name')
    sales_by_article = {
        sale['article_id']: sale['total']
        for sale in ArticlePayment.objects.filter(
            date__gte=ini_date,
            date__lt=period_end,
        ).values('article_id').annotate(total=Sum('amount'))
    }
    article_sales = [
        {
            'article': article,
            'total': sales_by_article.get(article.id, Decimal('0.00')),
            'inventory_value': article.stock * article.cost,
        }
        for article in article_list
    ]

    context = {
        'article_sales': article_sales,
        'ini_date': ini_date,
        'end_date': end_date,
    }

    return render(request, 'payments/article_payments.html', context)

@login_required
def bad_debt(request):	
	if request.method == 'POST':
		ini_date = datetime.datetime.strptime(request.POST["ini_date"], "%d-%m-%Y") if (request.POST["ini_date"]) else date.today()
		end_date = datetime.datetime.strptime(request.POST["end_date"], "%d-%m-%Y") if (request.POST["end_date"]) else date.today()
	else: 
		today = date.today()
		ini_date = today.replace(day = 1)
		end_date = datetime.datetime(today.year, today.month, calendar.mdays[today.month], 23, 59, 59)
	#ini_date = date.today().replace(day = 1)
	#end_date = date.today()
	enrolment_list = []
	total_amount = 0
	#Asistencias en el mes actual
	assistance_list = Assistance.objects.filter(date__range = (ini_date, end_date))
	for assistance in assistance_list:
		for enrolment in assistance.enrolments.all():
			if enrolment not in enrolment_list:
				payments = Payment.objects.filter(expire_date__gte = end_date, enrolment = enrolment)	
				if len(payments) == 0:
					enrolment_list.append(enrolment)
					total_amount = total_amount + enrolment.price

	enrolment_list = sorted(enrolment_list, key=attrgetter('student.name'))
	context = {
		'enrolment_list': enrolment_list,
		'total_amount': total_amount,
		'ini_date': ini_date,
		'end_date': end_date,
	}
	return render(request, 'payments/bad_debt.html', context)
 
'''
    Assistances
'''
def get_enrolment_list(current_group):
	kwargs = {'active': True,}
	if current_group != "":
		kwargs['group__id'] = current_group
		return Enrolment.objects.filter(**kwargs).order_by('student__name')
	return {}

@login_required
def assistances(request, assistance_id = None, search_date = None):	
	a_date = date.today() if search_date == None else datetime.datetime.strptime(search_date, "%d-%m-%Y")
	current_teacher = ""
	current_group = ""
	current_assistance = ""
	enrolment_list = {}

	#Estamos modificando una asistencia
	if assistance_id != None:
		assistance = Assistance.objects.get(pk = assistance_id)
		current_assistance = assistance
		a_date = assistance.date
		current_teacher = assistance.group.teacher.id
		current_group = assistance.group.id
		enrolment_list = get_enrolment_list(current_group)
	else:
		#Estamos creando una asistencia
		if request.method == 'POST':
			a_date = datetime.datetime.strptime(request.POST["date"], "%d-%m-%Y") if (request.POST["date"]) else date.today()
			current_teacher = request.POST["teacher"]
			current_group = request.POST["group"]
			enrolment_list = get_enrolment_list(current_group)

	context = {
		'date': a_date,
		'current_teacher': current_teacher,
		'current_group': current_group,
		'current_assistance': current_assistance,
		'enrolment_list': enrolment_list,
		'assistance_list': Assistance.objects.filter(date=a_date),
		'teacher_list': Teacher.objects.filter(active=True),
		'group_list': Group.objects.filter(active=True),
	}
	return render(request, 'assistances/assistances.html', context)
 
@login_required
def assistances_save(request):	
	c_date = date.today()
	if request.method == 'POST':
		#Estamos editando
		if "assistance_id" in request.POST.keys():
			assistance = Assistance.objects.get(pk = request.POST["assistance_id"])
			assistance.enrolments.clear()
			assistance.save()
			c_date = assistance.date
		#Estamos creando
		else:
			c_date = datetime.datetime.strptime(request.POST["new_date"], "%d-%m-%Y")
			group = Group.objects.get(id = request.POST['new_group'])
			assistance = Assistance(date = c_date, group = group)
			assistance.save()
		for key in request.POST.keys():
			if key.startswith('check_'):
				enrol_id = key.split('_')[1]
				if request.POST[key] != "0":
					enrol = Enrolment.objects.get(id=enrol_id)
					assistance.enrolments.add(enrol_id)
				assistance.save()
	return redirect('/studio/assistances/'+c_date.strftime("%d-%m-%Y")+"/")

@login_required
def assistances_delete(request, assistance_id):	
	assistance = Assistance.objects.get(id = assistance_id)
	assistance.delete()
	return redirect('/studio/assistances/')

@login_required
def no_assistance(request):	
	ini_date = date.today().replace(day=1)
	ini_date = ini_date - relativedelta(months=1)
	end_date = date.today()
	#end_date = end_date - relativedelta(months=1)
	enrolment_list = []
	#Asistencias en el mes actual
	enrolments = Enrolment.objects.filter(active = True)
	for enrolment in enrolments:
		assistance_list = Assistance.objects.filter(date__range = (ini_date, end_date), enrolments__in = [enrolment])
		if len(assistance_list) == 0:
			enrolment_list.append(enrolment)
		else:
			print("%s %s" % (enrolment.student, enrolment))

	context = {
		'enrolment_list': enrolment_list,
		'ini_date': ini_date,
		'end_date': end_date,
	}
	return render(request, 'assistances/no_assistance.html', context)

@login_required
def assistances_baja(request):	
	if request.method == 'POST':
		for key in request.POST.keys():
			if key.startswith('enrol_'):
				enrol_id = key.split('_')[1]
				enrol = Enrolment.objects.get(id=enrol_id)
				enrol.active = False
				enrol.save()
	return redirect('/studio/no_assistance/')

'''
    Notifications
'''
def get_student_list(teacher, group):
	kwargs = {'enrolment__active': True,}
	if teacher != "":
		kwargs['enrolment__group__teacher__id'] = teacher
	if group != "":
		kwargs['enrolment__group__id'] = group
	return Student.objects.filter(**kwargs).distinct()

@login_required
def notifications(request):	
	if request.method == 'POST':
		ini_date = datetime.datetime.strptime(request.POST["ini_date"], "%d-%m-%Y") if (request.POST["ini_date"]) else date.today()
		end_date = datetime.datetime.strptime(request.POST["end_date"], "%d-%m-%Y") if (request.POST["end_date"]) else date.today()
	else:
		today = date.today()
		ini_date = today.replace(day = 1)
		end_date = datetime.datetime(today.year, today.month, calendar.mdays[today.month], 23, 59, 59)
	notification_list = Notification.objects.filter(date__range = (ini_date, end_date))

	context = {
		'ini_date': ini_date,
		'end_date': end_date,
		'notification_list': notification_list,
	}
	return render(request, 'notifications/notifications.html', context)
 
@login_required
def notification_add(request):	
	current_teacher = ""
	current_group = ""
	if request.method == 'POST':
		current_teacher = request.POST["teacher"]
		current_group = request.POST["group"]
		#student_list = Student.objects.filter(enrolment__active = True, enrolment__group = current_group).distinct()
	#else:
	#	student_list = Student.objects.filter(enrolment__active = True).distinct()
	student_list = get_student_list(current_teacher, current_group)

	context = {
		'current_teacher': current_teacher,
		'current_group': current_group,
		'student_list': student_list,
		'teacher_list': Teacher.objects.filter(active=True),
		'group_list': Group.objects.filter(active=True),
	}
	return render(request, 'notifications/notification_add.html', context)

@login_required
def notification_save(request):	
	if request.method == 'POST':
		msg = request.POST['msg']
		notification = Notification(msg = msg)
		notification.save()
		for key in request.POST.keys():
			if key.startswith('check_'):
				student_id = key.split('_')[1]
				if request.POST[key] != "0":
					student = Student.objects.get(id=student_id)
					notification.students.add(student)
				notification.save()
	return redirect('/studio/notifications/')

@login_required
def notification_delete(request, notification_id):	
	notification = Notification.objects.get(id = notification_id)
	notification.delete()
	return redirect('/studio/notifications/')

@login_required
def notification_send(request, notification_id):	
	try:
		notification = Notification.objects.get(id = notification_id)
		for student in notification.students.all():
			devices = FCMDevice.objects.filter(name=student.pin)
			devices.send_message("5db informa:", "%s..." % (strip_tags(notification.msg[0:60])))
	except Exception as e:
		print(e)
	return redirect('/studio/notifications/')

'''
    Pulseras
'''
@login_required
def wristbands(request):	
	student = None
	assistance_list = []
	today = datetime.datetime.today()
	week = ["monday", "tuesday", "wednesday", "thursday", "friday"]
	if request.POST:
		student = Student.objects.filter(band=request.POST["band"]).first()
		for item in student.enrolment.all():
			#print(getattr(item.group, week[int(now.weekday())]))
			if getattr(item.group, week[int(today.weekday())]):
				assistance, created = Assistance.objects.get_or_create(date=today, group=item.group)
				assistance.enrolments.add(item)
				assistance_list.append(assistance)
	return render(request, 'wristbands/wristbands.html', {"student": student, "assistance_list": assistance_list})
 
