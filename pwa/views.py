from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.shortcuts import get_object_or_404, render, redirect
from django.utils.translation import gettext as _
from django.utils import timezone
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, ROUND_UP

from studio.models import Student, Payment, Assistance, Enrolment
from champs.models import ChampCost, Registration, TravelCompanion


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
	return render (request,'pwa/index.html',{"student": student})

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
