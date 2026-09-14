from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.shortcuts import get_object_or_404, render, redirect
from django.utils.translation import gettext as _
from django.utils import timezone
from django.db import transaction
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, ROUND_UP

from studio.models import Student, Payment, Assistance, Enrolment
from champs.models import ChampCost, Registration, TravelCompanion
from registration_forms.models import Form, FormAnswer, FormQuestion, FormSubmission


def check_pin(request):
	return ("pin" in request.session and request.session["pin"] != "")

def login(request):
	return render (request,'pwa/login.html',{})

def logout(request):
	request.session["pin"] = ""
	return redirect(login)

def set_pin(request):
	try:
		pin = request.POST["pin"]
		student = Student.objects.filter(pin=pin).first()
		if student == None:
			return render (request,'pwa/login.html',{'err': 'Pin no encontrado!'})
		request.session["pin"] = pin
		return redirect(index)
	except Exception as e:
		return render (request,'pwa/login.html',{"err": e})

def index(request):
	if not check_pin(request):
		return redirect(login)
	student = Student.objects.filter(pin=request.session["pin"]).first()
	submitted_form_ids = set(
		FormSubmission.objects.filter(student=student).values_list('form_id', flat=True)
	)
	return render(request, 'pwa/index.html', {
		"student": student,
		"published_forms": Form.objects.filter(is_published=True).order_by('-created_at')[:3],
		"submitted_form_ids": submitted_form_ids,
		"upcoming_registrations": Registration.objects.filter(
			student=student,
			champ__publish=True,
			champ__date__gte=timezone.now().date(),
		).select_related('champ').order_by('champ__date')[:3],
	})

def payments(request):
	if not check_pin(request):
		return redirect(login)
	student = Student.objects.filter(pin=request.session["pin"]).first()
	payment_list = Payment.objects.filter(student=student, date__year=timezone.now().year)
	return render (request,'pwa/payments.html',{'student': student, 'payment_list': payment_list})

def assistances(request):
	if not check_pin(request):
		return redirect(login)
	student = Student.objects.filter(pin=request.session["pin"]).first()
	enrolment_list = Enrolment.objects.filter(student=student, active=True)
	assistance_list = Assistance.objects.filter(enrolments__in=enrolment_list, date__year=timezone.now().year).order_by('-date')
	return render (request,'pwa/assistances.html',{'student': student, 'assistance_list': assistance_list})


def activity(request):
	if not check_pin(request):
		return redirect(login)
	student = Student.objects.filter(pin=request.session["pin"]).first()
	enrolment_list = Enrolment.objects.filter(student=student, active=True)
	return render(request, 'pwa/activity.html', {
		'student': student,
		'payment_list': Payment.objects.filter(student=student, date__year=timezone.now().year),
		'assistance_list': Assistance.objects.filter(
			enrolments__in=enrolment_list,
			date__year=timezone.now().year,
		).order_by('-date'),
	})


def forms(request):
	if not check_pin(request):
		return redirect(login)
	student = Student.objects.filter(pin=request.session["pin"]).first()
	return render(request, 'pwa/forms.html', {
		'student': student,
		'form_list': Form.objects.filter(is_published=True).order_by('-created_at'),
		'submitted_form_ids': set(FormSubmission.objects.filter(student=student).values_list('form_id', flat=True)),
	})


def form_detail(request, form_id):
	if not check_pin(request):
		return redirect(login)
	student = Student.objects.filter(pin=request.session["pin"]).first()
	form = get_object_or_404(Form.objects.filter(is_published=True), pk=form_id)
	questions = list(form.questions.all())
	submission = FormSubmission.objects.filter(form=form, student=student).prefetch_related('answers__question').first()
	can_edit = form.is_open and (not submission or form.allow_response_changes)

	if request.method == 'POST' and can_edit:
		errors = {}
		values = {}
		for question in questions:
			value = request.POST.get('question_%s' % question.id, '').strip()
			values[question.id] = value
			if question.required and not value:
				errors[question.id] = _('Esta pregunta es obligatoria.')
			elif question.answer_type == FormQuestion.ANSWER_TYPE_YES_NO and value not in ('yes', 'no', ''):
				errors[question.id] = _('Selecciona Sí o No.')
		if not errors:
			with transaction.atomic():
				if not submission:
					submission = FormSubmission.objects.create(form=form, student=student)
				existing_answers = {answer.question_id: answer for answer in submission.answers.all()}
				for question in questions:
					answer = existing_answers.get(question.id, FormAnswer(submission=submission, question=question))
					if question.answer_type == FormQuestion.ANSWER_TYPE_YES_NO:
						answer.yes_no = values[question.id] == 'yes' if values[question.id] else None
						answer.short_text = ''
					else:
						answer.short_text = values[question.id]
						answer.yes_no = None
					answer.save()
			return redirect('pwa-form-detail', form_id=form.id)
		for question in questions:
			question.submitted_value = values.get(question.id, '')
			question.error = errors.get(question.id)
		return render(request, 'pwa/form_detail.html', {
			'student': student, 'form': form, 'questions': questions, 'can_edit': can_edit,
		})

	answers_by_question = {answer.question_id: answer for answer in submission.answers.all()} if submission else {}
	for question in questions:
		question.answer_value = answers_by_question[question.id].value if question.id in answers_by_question else ''
		answer = answers_by_question.get(question.id)
		if answer and question.answer_type == FormQuestion.ANSWER_TYPE_YES_NO:
			question.submitted_value = 'yes' if answer.yes_no else 'no' if answer.yes_no is not None else ''
		elif answer:
			question.submitted_value = answer.short_text
	return render(request, 'pwa/form_detail.html', {
		'student': student, 'form': form, 'questions': questions, 'submission': submission,
		'can_edit': can_edit,
	})


def licence(request):
	if not check_pin(request):
		return redirect(login)
	student = Student.objects.filter(pin=request.session["pin"]).first()
	return render(request, 'pwa/licence.html', {'student': student})

def get_championship_registration_summary(registration):
	champ = registration.champ
	cost_list = list(champ.costs.select_related('cost', 'category__category')) if champ else []
	champ_categories = {
		champ_category.category_id: champ_category
		for champ_category in champ.categories.select_related('category').all()
	} if champ else {}
	registrations = list(Registration.objects.filter(champ=champ).prefetch_related('categories', 'travel_companions').order_by('student__name')) if champ else []
	registrations_by_category = defaultdict(list)
	companions_by_registration = defaultdict(list)
	companions = []
	for champ_registration in registrations:
		for category in champ_registration.categories.all():
			registrations_by_category[category.id].append(champ_registration)
		for companion in champ_registration.travel_companions.all():
			companions_by_registration[champ_registration.id].append(companion)
			companions.append(companion)

	registration_costs = defaultdict(lambda: Decimal("0.00"))
	companion_costs = defaultdict(lambda: Decimal("0.00"))
	cost_details = []
	for cost in cost_list:
		if cost.scope == ChampCost.SCOPE_CATEGORY:
			cost_registrations = registrations_by_category.get(cost.category.category_id, []) if cost.category_id else []
			cost_companions = []
		elif cost.scope == ChampCost.SCOPE_COMPANIONS:
			cost_registrations = []
			cost_companions = companions
		else:
			cost_registrations = registrations
			cost_companions = companions
		participant_units = len(cost_registrations) + len(cost_companions)

		if cost.amount_type == ChampCost.AMOUNT_TYPE_GLOBAL:
			amount_per_person = (cost.amount / participant_units).quantize(Decimal("0.01"), rounding=ROUND_UP) if participant_units else Decimal("0.00")
		else:
			amount_per_person = cost.amount

		if registration in cost_registrations:
			registration_costs[registration.id] += amount_per_person
			if cost.scope == ChampCost.SCOPE_CATEGORY and cost.category_id and cost.category.category:
				applies_to = cost.category.category.name
			elif cost.scope == ChampCost.SCOPE_ALL_TRAVELERS:
				applies_to = _('Todos los viajeros')
			else:
				applies_to = _('Solo acompañantes')
			cost_details.append({
				'name': cost.cost.name if cost.cost else _('Coste'),
				'applies_to': applies_to,
				'amount': amount_per_person,
			})

		for companion in companions_by_registration[registration.id]:
			if companion in cost_companions:
				companion_costs[companion.id] += amount_per_person

	category_details = []
	category_cost_total = Decimal("0.00")
	for category in registration.categories.all():
		champ_category = champ_categories.get(category.id)
		category_cost = champ_category.amount if champ_category else Decimal("0.00")
		category_cost_total += category_cost
		category_details.append({'category': category, 'amount': category_cost})
		if category_cost:
			cost_details.append({
				'name': _("Inscripción: %(category)s") % {'category': category.name},
				'applies_to': category.name,
				'amount': category_cost,
			})

	total_amount = registration_costs[registration.id] + category_cost_total
	companion_details = []
	for companion in companions_by_registration[registration.id]:
		companion_total_amount = companion_costs[companion.id]
		companion_details.append({
			'companion': companion,
			'total_amount': companion_total_amount,
			'pending_amount': max(companion_total_amount - companion.paid_amount, Decimal("0.00")),
		})
	return {
		'category_details': category_details,
		'cost_details': cost_details,
		'companion_details': companion_details,
		'total_amount': total_amount,
		'pending_amount': max(total_amount - registration.paid_amount, Decimal("0.00")),
	}


def championships(request):
	if not check_pin(request):
		return redirect(login)
	student = Student.objects.filter(pin=request.session["pin"]).first()
	registration_list = Registration.objects.filter(student=student).select_related('champ').order_by('-champ__date')
	return render(request, 'pwa/championships.html', {
		'student': student,
		'registration_list': registration_list,
	})


def championship_detail(request, registration_id):
	if not check_pin(request):
		return redirect(login)
	student = Student.objects.filter(pin=request.session["pin"]).first()
	registration = get_object_or_404(
		Registration.objects.select_related('champ').prefetch_related('categories', 'travel_companions'),
		pk=registration_id,
		student=student,
	)
	return render(request, 'pwa/championship-detail.html', {
		'student': student,
		'registration': registration,
		'summary': get_championship_registration_summary(registration),
	})


def upload_championship_payment_proof(request, registration_id):
	if not check_pin(request):
		return redirect(login)
	student = Student.objects.filter(pin=request.session["pin"]).first()
	registration = get_object_or_404(Registration, pk=registration_id, student=student)
	if request.method == 'POST' and request.FILES.get('payment_proof'):
		registration.payment_proof = request.FILES['payment_proof']
		registration.save(update_fields=['payment_proof'])
	return redirect('%s#costs' % reverse('pwa-championship-detail', args=[registration.id]))


def add_championship_companion(request, registration_id):
	if not check_pin(request):
		return redirect(login)
	student = Student.objects.filter(pin=request.session["pin"]).first()
	registration = get_object_or_404(Registration, pk=registration_id, student=student)
	if request.method == 'POST':
		full_name = request.POST.get('full_name', '').strip()
		birth_date = request.POST.get('birth_date', '')
		dni = request.POST.get('dni', '').strip().upper()
		is_canary_resident = request.POST.get('is_canary_resident') == 'on'
		municipality = request.POST.get('municipality', '').strip() if is_canary_resident else ''
		try:
			birth_date = datetime.strptime(birth_date, '%Y-%m-%d').date()
			if full_name and dni and (not is_canary_resident or municipality):
				TravelCompanion.objects.create(
					registration=registration,
					full_name=full_name,
					is_canary_resident=is_canary_resident,
					municipality=municipality,
					birth_date=birth_date,
					dni=dni,
				)
		except (TypeError, ValueError):
			pass
	return redirect('%s#companions' % reverse('pwa-championship-detail', args=[registration.id]))


def delete_championship_companion(request, registration_id, companion_id):
	if not check_pin(request):
		return redirect(login)
	student = Student.objects.filter(pin=request.session["pin"]).first()
	registration = get_object_or_404(Registration, pk=registration_id, student=student)
	if request.method == 'POST':
		TravelCompanion.objects.filter(pk=companion_id, registration=registration).delete()
	return redirect('%s#companions' % reverse('pwa-championship-detail', args=[registration.id]))

def change_photo(request):
	if not check_pin(request):
		return redirect(login)
	if request.POST:
		student = Student.objects.get(pk=request.POST["student"])
		#print(request.FILES["photo"])
		student.picture = request.FILES["photo"]
		student.save()
	return redirect(index)
