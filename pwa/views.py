from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.urls import reverse
from django.shortcuts import get_object_or_404, render, redirect
from django.http import FileResponse
from django.utils.translation import gettext as _
from django.utils import timezone
from django.db import IntegrityError, transaction
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, ROUND_UP

from studio.models import Article, Student, Payment, Assistance, Enrolment
from champs.models import ChampCost, Championship, Registration, TravelCompanion
from registration_forms.models import Form, FormAnswer, FormQuestion, FormSubmission
from pwa.forms import ComplementaryDataForm, StudentDocumentUploadForm
from pwa.models import DocumentTemplate, StudentDocument


def get_current_student(request):
	student_id = request.session.get("student_id")
	if student_id:
		return Student.objects.filter(pk=student_id).first()

	# Conserva las sesiones iniciadas antes de migrar de PIN a student_id.
	legacy_pin = request.session.pop("pin", None)
	if not legacy_pin:
		return None
	student = Student.objects.filter(pin=legacy_pin).first()
	if student:
		request.session["student_id"] = student.pk
	return student


def check_student(request):
	return get_current_student(request) is not None

def login(request):
	return render (request,'pwa/login.html',{})

def logout(request):
	request.session.flush()
	return redirect(login)

def set_pin(request):
	try:
		pin = request.POST["pin"].strip().upper()
		student = Student.objects.filter(pin=pin).first()
		if student == None:
			return render (request,'pwa/login.html',{'err': 'Pin no encontrado!'})
		request.session.cycle_key()
		request.session.pop("pin", None)
		request.session["student_id"] = student.pk
		return redirect(index)
	except Exception as e:
		return render (request,'pwa/login.html',{"err": e})

def index(request):
	if not check_student(request):
		return redirect(login)
	student = get_current_student(request)
	submitted_form_ids = set(
		FormSubmission.objects.filter(student=student).values_list('form_id', flat=True)
	)
	upcoming_championships = list(Championship.objects.for_student(student).filter(
		publish=True,
		date__gte=timezone.now().date(),
	).prefetch_related('categories__category').order_by('date'))
	registration_by_championship = {
		registration['champ_id']: registration['id']
		for registration in Registration.objects.filter(
			student=student,
			champ_id__in=[championship.id for championship in upcoming_championships],
		).values('id', 'champ_id')
	}
	for championship in upcoming_championships:
		championship.registration_id = registration_by_championship.get(championship.id)
	return render(request, 'pwa/index.html', {
		"student": student,
		"wallet_balance": student.wallet_balance,
		"promotions": Article.objects.filter(
			publish=True, is_promo=True, promo_price__isnull=False, stock__gt=0,
		).order_by('name'),
		"published_forms": Form.objects.filter(is_published=True).for_student(student).order_by('-created_at')[:3],
		"submitted_form_ids": submitted_form_ids,
		"upcoming_championships": upcoming_championships,
	})

def payments(request):
	if not check_student(request):
		return redirect(login)
	student = get_current_student(request)
	payment_list = Payment.objects.filter(student=student, date__year=timezone.now().year)
	return render (request,'pwa/payments.html',{'student': student, 'payment_list': payment_list})

def assistances(request):
	if not check_student(request):
		return redirect(login)
	student = get_current_student(request)
	enrolment_list = Enrolment.objects.filter(student=student, active=True)
	assistance_list = Assistance.objects.filter(enrolments__in=enrolment_list, date__year=timezone.now().year).order_by('-date')
	return render (request,'pwa/assistances.html',{'student': student, 'assistance_list': assistance_list})


def activity(request):
	if not check_student(request):
		return redirect(login)
	student = get_current_student(request)
	enrolment_list = Enrolment.objects.filter(student=student, active=True)
	return render(request, 'pwa/activity.html', {
		'student': student,
		'payment_list': Payment.objects.filter(student=student, date__year=timezone.now().year),
		'assistance_list': Assistance.objects.filter(
			enrolments__in=enrolment_list,
			date__year=timezone.now().year,
		).order_by('-date'),
	})


def wallet(request):
	if not check_student(request):
		return redirect(login)
	student = get_current_student(request)
	return render(request, 'pwa/wallet.html', {
		'student': student,
		'wallet_balance': student.wallet_balance,
		'movement_list': student.wallet_movements.select_related('created_by').all(),
	})


def forms(request):
	if not check_student(request):
		return redirect(login)
	student = get_current_student(request)
	return render(request, 'pwa/forms.html', {
		'student': student,
		'form_list': Form.objects.filter(is_published=True).for_student(student).order_by('-created_at'),
		'submitted_form_ids': set(FormSubmission.objects.filter(student=student).values_list('form_id', flat=True)),
	})


def form_detail(request, form_id):
	if not check_student(request):
		return redirect(login)
	student = get_current_student(request)
	form = get_object_or_404(Form.objects.filter(is_published=True).for_student(student), pk=form_id)
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
			elif question.answer_type == FormQuestion.ANSWER_TYPE_SELECT and value not in question.select_options:
				errors[question.id] = _('Selecciona una opción válida.')
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
	if not check_student(request):
		return redirect(login)
	student = get_current_student(request)
	return render(request, 'pwa/licence.html', {'student': student})


def complementary_data(request):
	if not check_student(request):
		return redirect(login)
	student = get_current_student(request)
	if request.method == 'POST':
		form = ComplementaryDataForm(request.POST, request.FILES, instance=student)
		if form.is_valid():
			form.save()
			messages.success(request, _("Datos guardados correctamente."))
			return redirect('pwa-complementary-data')
	else:
		form = ComplementaryDataForm(instance=student)
	return render(request, 'pwa/complementary_data.html', {'student': student, 'form': form})


def documents(request):
	if not check_student(request):
		return redirect(login)
	student = get_current_student(request)
	if request.method == 'POST':
		form = StudentDocumentUploadForm(request.POST, request.FILES, student=student)
		if form.is_valid():
			template = form.cleaned_data['template']
			uploaded_file = form.cleaned_data['file']
			document, created = StudentDocument.objects.get_or_create(
				student=student, template=template,
				defaults={'file': uploaded_file, 'original_filename': uploaded_file.name[:255]},
			)
			if not created:
				document.file = uploaded_file
				document.original_filename = uploaded_file.name[:255]
				document.save()
			return redirect('pwa-documents')
	else:
		form = StudentDocumentUploadForm(student=student)
	return render(request, 'pwa/documents.html', {
		'student': student,
		'form': form,
		'templates': DocumentTemplate.available_for_student(student),
		'selected_template_id': request.POST.get('template', '') if request.method == 'POST' else '',
		'documents': StudentDocument.objects.filter(student=student).select_related('template'),
	})


def download_document(request, document_id):
	if not check_student(request):
		return redirect(login)
	document = get_object_or_404(
		StudentDocument, pk=document_id, student=get_current_student(request),
	)
	return FileResponse(document.file.open('rb'), as_attachment=True, filename=document.original_filename)


def download_document_template(request, template_id):
	if not check_student(request):
		return redirect(login)
	template = get_object_or_404(
		DocumentTemplate.available_for_student(get_current_student(request)), pk=template_id,
	)
	return FileResponse(template.template_file.open('rb'), as_attachment=True, filename='%s.pdf' % template.title)

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
	registration_companions = companions_by_registration[registration.id]
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

		registration_included = registration in cost_registrations
		included_companions = [
			companion for companion in registration_companions
			if companion in cost_companions
		]
		if registration_included:
			registration_costs[registration.id] += amount_per_person

		for companion in included_companions:
			companion_costs[companion.id] += amount_per_person

		participant_count = int(registration_included) + len(included_companions)
		if participant_count:
			if registration_included and included_companions:
				applies_to = _('Competidora y %(count)s acompañante(s)') % {
					'count': len(included_companions),
				}
			elif included_companions:
				applies_to = _('%(count)s acompañante(s)') % {'count': len(included_companions)}
			elif cost.scope == ChampCost.SCOPE_CATEGORY and cost.category_id and cost.category.category:
				applies_to = cost.category.category.name
			else:
				applies_to = _('Competidora')
			cost_details.append({
				'name': cost.cost.name if cost.cost else _('Coste'),
				'applies_to': applies_to,
				'amount': amount_per_person * participant_count,
			})

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

	companion_total_amount = sum(
		(companion_costs[companion.id] for companion in registration_companions),
		Decimal("0.00"),
	)
	companion_paid_amount = sum(
		(companion.paid_amount for companion in registration_companions),
		Decimal("0.00"),
	)
	student_total_amount = registration_costs[registration.id] + category_cost_total
	total_amount = student_total_amount + companion_total_amount
	paid_amount = registration.paid_amount + companion_paid_amount
	participant_cost_details = [{
		'name': registration.student.name if registration.student else _('Alumna'),
		'role': _('Alumna'),
		'amount': student_total_amount,
		'icon': 'fa-user',
	}]
	companion_details = []
	for companion in registration_companions:
		participant_cost_details.append({
			'name': companion.full_name,
			'role': _('Acompañante'),
			'amount': companion_costs[companion.id],
			'icon': 'fa-user-friends',
		})
		companion_details.append({
			'companion': companion,
		})
	return {
		'category_details': category_details,
		'cost_details': cost_details,
		'participant_cost_details': participant_cost_details,
		'companion_details': companion_details,
		'total_amount': total_amount,
		'paid_amount': paid_amount,
		'pending_amount': max(total_amount - paid_amount, Decimal("0.00")),
	}


def championships(request):
	if not check_student(request):
		return redirect(login)
	student = get_current_student(request)
	registration_list = Registration.objects.filter(
		student=student,
		champ__in=Championship.objects.for_student(student),
	).select_related('champ').order_by('-champ__date')
	return render(request, 'pwa/championships.html', {
		'student': student,
		'registration_list': registration_list,
	})


def championship_detail(request, registration_id):
	if not check_student(request):
		return redirect(login)
	student = get_current_student(request)
	registration = get_object_or_404(
		Registration.objects.select_related('champ').prefetch_related('categories', 'travel_companions'),
		pk=registration_id,
		student=student,
		champ__in=Championship.objects.for_student(student),
	)
	return render(request, 'pwa/championship-detail.html', {
		'student': student,
		'registration': registration,
		'summary': get_championship_registration_summary(registration),
	})


def available_championship_detail(request, championship_id):
	"""Show a published championship the current student may enter."""
	if not check_student(request):
		return redirect(login)
	student = get_current_student(request)
	championship = get_object_or_404(
		Championship.objects.for_student(student).filter(
			publish=True, date__gte=timezone.now().date(),
		).prefetch_related('categories__category'),
		pk=championship_id,
	)
	registration = Registration.objects.filter(student=student, champ=championship).first()
	if registration:
		return redirect('pwa-championship-detail', registration_id=registration.id)

	available_categories = [
		champ_category.category for champ_category in championship.categories.all()
		if champ_category.category_id
	]
	if request.method == 'POST':
		selected_category_ids = {int(category_id) for category_id in request.POST.getlist('categories') if category_id.isdigit()}
		valid_categories = [category for category in available_categories if category.id in selected_category_ids]
		if valid_categories:
			registration = Registration.objects.create(student=student, champ=championship)
			registration.categories.add(*valid_categories)
			return redirect('pwa-championship-detail', registration_id=registration.id)
		return render(request, 'pwa/available_championship_detail.html', {
			'student': student,
			'championship': championship,
			'categories': available_categories,
			'error': _('Selecciona al menos una categoría para inscribirte.'),
		})
	return render(request, 'pwa/available_championship_detail.html', {
		'student': student,
		'championship': championship,
		'categories': available_categories,
	})


def upload_championship_payment_proof(request, registration_id):
	if not check_student(request):
		return redirect(login)
	student = get_current_student(request)
	registration = get_object_or_404(
		Registration,
		pk=registration_id,
		student=student,
		champ__in=Championship.objects.for_student(student),
	)
	if request.method == 'POST' and request.FILES.get('payment_proof'):
		registration.payment_proof = request.FILES['payment_proof']
		registration.save(update_fields=['payment_proof'])
	return redirect('%s#costs' % reverse('pwa-championship-detail', args=[registration.id]))


def add_championship_companion(request, registration_id):
	if not check_student(request):
		return redirect(login)
	student = get_current_student(request)
	registration = get_object_or_404(
		Registration,
		pk=registration_id,
		student=student,
		champ__in=Championship.objects.for_student(student),
	)
	if request.method == 'POST':
		full_name = request.POST.get('full_name', '').strip()
		birth_date = request.POST.get('birth_date', '')
		dni = request.POST.get('dni', '').strip().upper()
		is_canary_resident = request.POST.get('is_canary_resident') == 'on'
		municipality = request.POST.get('municipality', '').strip()
		try:
			birth_date = datetime.strptime(birth_date, '%Y-%m-%d').date()
			if full_name and dni and municipality:
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
	if not check_student(request):
		return redirect(login)
	student = get_current_student(request)
	registration = get_object_or_404(
		Registration,
		pk=registration_id,
		student=student,
		champ__in=Championship.objects.for_student(student),
	)
	if request.method == 'POST':
		TravelCompanion.objects.filter(pk=companion_id, registration=registration).delete()
	return redirect('%s#companions' % reverse('pwa-championship-detail', args=[registration.id]))

def change_photo(request):
	if not check_student(request):
		return redirect(login)
	if request.method == 'POST' and request.FILES.get("photo"):
		student = get_current_student(request)
		student.picture = request.FILES["photo"]
		student.save()
	return redirect(index)


def change_pin(request):
	if not check_student(request):
		return redirect(login)

	student = get_current_student(request)
	context = {'student': student}
	if request.method != 'POST':
		return render(request, 'pwa/change_pin.html', context)

	current_pin = request.POST.get('current_pin', '').strip().upper()
	new_pin = request.POST.get('new_pin', '').strip().upper()
	confirmation = request.POST.get('new_pin_confirmation', '').strip().upper()

	if current_pin != student.pin:
		context['error'] = _('El PIN actual no es correcto.')
	elif len(new_pin) != 4 or not new_pin.isalnum():
		context['error'] = _('El nuevo PIN debe tener cuatro caracteres alfanuméricos.')
	elif new_pin != confirmation:
		context['error'] = _('Los PIN nuevos no coinciden.')
	elif new_pin == student.pin:
		context['error'] = _('El nuevo PIN debe ser distinto del actual.')
	else:
		try:
			student.pin = new_pin
			student.save(update_fields=['pin'])
		except IntegrityError:
			context['error'] = _('Ese PIN ya está en uso. Elige otro.')
		else:
			request.session.cycle_key()
			context['success'] = _('Tu PIN se ha actualizado correctamente.')

	return render(request, 'pwa/change_pin.html', context)
