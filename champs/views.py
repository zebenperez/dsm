from django.shortcuts import render, redirect

from datetime import date, datetime
from collections import defaultdict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, ROUND_UP

from studio.decorators import group_required
from studio.models import Student
from .models import Category, ChampCategory, ChampCost, Championship, ChampFile, ChampioshipInfo, Cost, Registration, RegistrationFile, TravelCompanion
from .commons import show_exc, get_or_none, get_param


def global_cost_per_person(amount, participants_count):
    if not participants_count:
        return Decimal('0.00')
    return (amount / participants_count).quantize(Decimal('0.01'), rounding=ROUND_UP)


def get_cost_scope_participants(cost, registrations, registrations_by_category, companions):
    if cost.scope == ChampCost.SCOPE_CATEGORY:
        return registrations_by_category.get(cost.category.category_id, []) if cost.category_id else [], []
    if cost.scope == ChampCost.SCOPE_COMPANIONS:
        return [], companions
    return registrations, companions


def champ_category_is_empty(champ_category):
    if not champ_category:
        return False
    return not (
        Registration.objects.filter(champ=champ_category.champ, categories=champ_category.category).exists()
        or ChampCost.objects.filter(category=champ_category).exists()
    )


def champ_has_related_data(champ):
    return (
        ChampCategory.objects.filter(champ=champ).exists()
        or ChampCost.objects.filter(champ=champ).exists()
        or ChampFile.objects.filter(champ=champ).exists()
        or Registration.objects.filter(champ=champ).exists()
        or ChampioshipInfo.objects.filter(champ=champ).exists()
    )


def get_champ_list_context(publish_filter='all'):
    champ_list = Championship.objects.all()
    if publish_filter == 'true':
        champ_list = champ_list.filter(publish=True)
    elif publish_filter == 'false':
        champ_list = champ_list.filter(publish=False)

    champ_list = list(champ_list.prefetch_related('categories__category', 'costs__cost').order_by('date', 'name'))
    for champ in champ_list:
        champ.can_delete = not champ_has_related_data(champ)
    return {'champ_list': champ_list, 'publish_filter': publish_filter}


def get_champ_details_context(obj):
    registrations = Registration.objects.filter(champ=obj).select_related('student').prefetch_related('categories').order_by('student__name') if obj else []
    registrations_count = registrations.count() if obj else 0
    categories = list(obj.categories.select_related('category').order_by('category__name')) if obj else []
    cost_list = list(obj.costs.select_related('cost', 'category__category').order_by('category__category__name', 'cost__name')) if obj else []
    companion_list = list(TravelCompanion.objects.filter(registration__champ=obj).select_related('registration__student').order_by('registration__student__name', 'full_name')) if obj else []
    registrations_by_category = {}
    categories_by_id = {champ_category.category_id: champ_category for champ_category in categories}
    registration_costs = defaultdict(lambda: Decimal("0.00"))
    companion_costs = defaultdict(lambda: Decimal("0.00"))
    champ_total_amount = Decimal("0.00")
    champ_paid_amount = Decimal("0.00")
    champ_pending_amount = Decimal("0.00")
    today = date.today()

    for reg in registrations:
        for category in reg.categories.all():
            registrations_by_category.setdefault(category.id, []).append(reg)

    for cost in cost_list:
        cost_registrations, cost_companions = get_cost_scope_participants(
            cost, registrations, registrations_by_category, companion_list
        )
        cost.participant_units = len(cost_registrations) + len(cost_companions)

        if cost.amount_type == ChampCost.AMOUNT_TYPE_GLOBAL:
            amount_per_person = global_cost_per_person(cost.amount, cost.participant_units)
            cost.has_global_participants = bool(cost.participant_units)
            cost.total_part_amount = cost.amount
            cost.global_share_min = amount_per_person
            cost.global_share_max = amount_per_person
            for registration in cost_registrations:
                registration_costs[registration.id] += amount_per_person
            for companion in cost_companions:
                companion_costs[companion.id] += amount_per_person
        else:
            cost.per_competitor_amount = cost.amount
            cost.total_part_amount = cost.amount * cost.participant_units
            for registration in cost_registrations:
                registration_costs[registration.id] += cost.amount
            for companion in cost_companions:
                companion_costs[companion.id] += cost.amount

    for reg in registrations:
        if reg.student and reg.student.born_date:
            born_date = reg.student.born_date
            reg.birth_year = born_date.year
            reg.current_age = today.year - born_date.year - ((today.month, today.day) < (born_date.month, born_date.day))
        else:
            reg.birth_year = None
            reg.current_age = None

        registration_category_ids = {category.id for category in reg.categories.all()}
        category_fees = sum(
            (categories_by_id[category_id].amount for category_id in registration_category_ids if category_id in categories_by_id),
            Decimal("0.00"),
        )
        reg.total_amount = registration_costs[reg.id] + category_fees
        reg.pending_amount = max(reg.total_amount - reg.paid_amount, Decimal("0.00"))
        champ_total_amount += reg.total_amount
        champ_paid_amount += reg.paid_amount
        champ_pending_amount += reg.pending_amount

    category_list = []
    general_cost_per_competitor = sum(
        (
            cost.amount
            if cost.amount_type == ChampCost.AMOUNT_TYPE_PER_COMPETITOR
            else global_cost_per_person(cost.amount, len(registrations) + len(companion_list))
            for cost in cost_list
            if cost.scope == ChampCost.SCOPE_ALL_TRAVELERS
        ),
        Decimal("0.00"),
    )
    for champ_category in categories:
        category = champ_category.category
        category_registrations = registrations_by_category.get(category.id, []) if category else []
        category_specific_cost = sum(
            (
                cost.amount
                if cost.amount_type == ChampCost.AMOUNT_TYPE_PER_COMPETITOR
                else global_cost_per_person(cost.amount, len(category_registrations))
                for cost in cost_list
                if cost.scope == ChampCost.SCOPE_CATEGORY and cost.category_id == champ_category.id
            ),
            Decimal("0.00"),
        )
        category_list.append({
            'champ_category': champ_category,
            'category': category,
            'cost_per_competitor': (general_cost_per_competitor + champ_category.amount + category_specific_cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            'registrations': category_registrations,
            'can_delete': champ_category_is_empty(champ_category),
        })

    companion_total_amount = Decimal("0.00")
    companion_paid_amount = Decimal("0.00")
    companion_pending_amount = Decimal("0.00")
    for companion in companion_list:
        companion.total_amount = companion_costs[companion.id]
        companion.pending_amount = max(companion.total_amount - companion.paid_amount, Decimal("0.00"))
        companion_total_amount += companion.total_amount
        companion_paid_amount += companion.paid_amount
        companion_pending_amount += companion.pending_amount

    champ_total_amount += companion_total_amount
    champ_paid_amount += companion_paid_amount
    champ_pending_amount += companion_pending_amount

    return {
        'obj': obj,
        'champ_info': ChampioshipInfo.objects.filter(champ=obj).first() if obj else None,
        'companion_list': companion_list,
        'companion_total_amount': companion_total_amount,
        'category_list': category_list,
        'cost_list': cost_list,
        'registrations_count': registrations_count,
        'champ_total_amount': champ_total_amount,
        'champ_paid_amount': champ_paid_amount,
        'champ_pending_amount': champ_pending_amount,
    }


'''
    Championship studen
'''
@group_required("admins")
def champs(request):
    return render(request, 'champs/champs.html', get_champ_list_context())

@group_required("admins")
def champs_list(request):
    publish_filter = get_param(request.GET, 'value', get_param(request.GET, 'publish_filter', 'all'))
    if publish_filter not in ('all', 'true', 'false'):
        publish_filter = 'all'
    return render(request, 'champs/champs-list.html', get_champ_list_context(publish_filter))

@group_required("admins")
def champs_form(request):
    try:
        obj = get_or_none(Championship, get_param(request.GET, "obj_id"))
        date = obj.date if obj != None else datetime.now()
        return render(request, "champs/champs-form.html", {'obj': obj, 'date': date})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins")
def champ_name_form(request):
    try:
        champ = get_or_none(Championship, get_param(request.GET, "champ_id"))
        return render(request, "champs/champs-name-form.html", {'champ': champ})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins")
def save_champ_name(request):
    try:
        champ = get_or_none(Championship, get_param(request.GET, "champ_id"))
        name = get_param(request.GET, "name").strip()
        if champ and name:
            champ.name = name
            champ.save(update_fields=['name'])
        return render(request, 'champs/champs-list.html', get_champ_list_context())
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins")
def champ_delete_form(request):
    try:
        champ = get_or_none(Championship, get_param(request.GET, "champ_id"))
        return render(request, "champs/champs-delete-form.html", {
            'champ': champ,
            'can_delete': bool(champ) and not champ_has_related_data(champ),
        })
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins")
def delete_champ(request):
    try:
        champ = get_or_none(Championship, get_param(request.GET, "champ_id"))
        if champ and not champ_has_related_data(champ):
            champ.delete()
        return render(request, 'champs/champs-list.html', get_champ_list_context())
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins")
def champ_category_form(request):
    try:
        champ = get_or_none(Championship, get_param(request.GET, "champ_id"))
        champ_category = get_or_none(ChampCategory, get_param(request.GET, "champ_category_id"))
        if champ_category and champ_category.champ_id != getattr(champ, 'id', None):
            champ_category = None
        return render(request, "champs/champs-category-form.html", {
            'champ': champ,
            'champ_category': champ_category,
        })
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins")
def save_champ_category(request):
    try:
        champ = get_or_none(Championship, get_param(request.GET, "champ_id"))
        champ_category = get_or_none(ChampCategory, get_param(request.GET, "champ_category_id"))
        name = get_param(request.GET, "name").strip()

        if champ_category and champ_category.champ_id != getattr(champ, 'id', None):
            champ_category = None

        if champ and name:
            if champ_category:
                if not champ_category.category:
                    champ_category.category = Category.objects.create(name=name)
                    champ_category.save(update_fields=['category'])
                else:
                    champ_category.category.name = name
                    champ_category.category.save(update_fields=['name'])
            else:
                category, created = Category.objects.get_or_create(name=name)
                if not ChampCategory.objects.filter(champ=champ, category=category).exists():
                    ChampCategory.objects.create(champ=champ, category=category)

        return render(request, "champs/champs-details-content.html", get_champ_details_context(champ))
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins")
def champ_category_delete_form(request):
    try:
        champ = get_or_none(Championship, get_param(request.GET, "champ_id"))
        champ_category = get_or_none(ChampCategory, get_param(request.GET, "champ_category_id"))
        if champ_category and champ_category.champ_id != getattr(champ, 'id', None):
            champ_category = None
        return render(request, "champs/champs-category-delete-form.html", {
            'champ': champ,
            'champ_category': champ_category,
            'can_delete': champ_category_is_empty(champ_category),
        })
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins")
def delete_champ_category(request):
    try:
        champ = get_or_none(Championship, get_param(request.GET, "champ_id"))
        champ_category = get_or_none(ChampCategory, get_param(request.GET, "champ_category_id"))
        if champ_category and champ_category.champ_id == getattr(champ, 'id', None) and champ_category_is_empty(champ_category):
            champ_category.delete()
        return render(request, "champs/champs-details-content.html", get_champ_details_context(champ))
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins")
def champs_details(request, obj_id):
    try:
        obj = get_or_none(Championship, obj_id)
        return render(request, "champs/champs-details.html", get_champ_details_context(obj))
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins")
def champ_info_form(request):
    try:
        champ = get_or_none(Championship, get_param(request.GET, "champ_id"))
        champ_info = ChampioshipInfo.objects.filter(champ=champ).first() if champ else None
        return render(request, "champs/champs-info-form.html", {'champ': champ, 'champ_info': champ_info})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins")
def save_champ_info(request):
    try:
        champ = get_or_none(Championship, get_param(request.GET, "champ_id"))
        if champ:
            champ_info, created = ChampioshipInfo.objects.get_or_create(champ=champ)
            outbound_date = get_param(request.GET, "outbound_date")
            return_date = get_param(request.GET, "return_date")

            champ_info.outbound_date = datetime.strptime(outbound_date, "%Y-%m-%d").date() if outbound_date else None
            champ_info.return_date = datetime.strptime(return_date, "%Y-%m-%d").date() if return_date else None
            champ_info.carrier_name = get_param(request.GET, "carrier_name")
            champ_info.details = get_param(request.GET, "details")
            champ_info.accommodation_name = get_param(request.GET, "accommodation_name")
            champ_info.save()

        return render(request, "champs/champs-details-content.html", get_champ_details_context(champ))
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins")
def champ_registration_form(request):
    try:
        champ = get_or_none(Championship, get_param(request.GET, "champ_id"))
        category = get_or_none(Category, get_param(request.GET, "category_id"))
        registered_students = Registration.objects.filter(champ=champ, categories=category).values_list('student_id', flat=True)
        student_list = Student.objects.filter(enrolment__active=True).exclude(id__in=registered_students).distinct().order_by('name')
        today = date.today()

        for student in student_list:
            if student.born_date:
                student.birth_year = student.born_date.year
                student.current_age = today.year - student.born_date.year - ((today.month, today.day) < (student.born_date.month, student.born_date.day))
            else:
                student.birth_year = None
                student.current_age = None

        context = {'champ': champ, 'category': category, 'student_list': student_list}
        return render(request, "champs/champs-registration-form.html", context)
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins")
def add_champ_registration(request):
    try:
        champ = get_or_none(Championship, get_param(request.GET, "champ_id"))
        category = get_or_none(Category, get_param(request.GET, "category_id"))
        student = get_or_none(Student, get_param(request.GET, "value"))

        if champ and category and student:
            reg = Registration.objects.filter(champ=champ, student=student).first()
            if not reg:
                reg = Registration.objects.create(champ=champ, student=student)
            reg.categories.add(category)

        return render(request, "champs/champs-details-content.html", get_champ_details_context(champ))
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins")
def champ_registration_payment_form(request):
    try:
        champ = get_or_none(Championship, get_param(request.GET, "champ_id"))
        registration = get_or_none(Registration, get_param(request.GET, "registration_id"))
        if not registration or registration.champ_id != getattr(champ, 'id', None):
            registration = None
        return render(request, "champs/champs-registration-payment-form.html", {
            'champ': champ,
            'registration': registration,
        })
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins")
def add_champ_registration_payment(request):
    try:
        champ = get_or_none(Championship, get_param(request.GET, "champ_id"))
        registration = get_or_none(Registration, get_param(request.GET, "registration_id"))
        amount = get_param(request.GET, "amount", "0").replace(",", ".")

        if registration and registration.champ_id == getattr(champ, 'id', None):
            try:
                payment_amount = Decimal(amount)
            except InvalidOperation:
                payment_amount = Decimal("0.00")

            if payment_amount > 0:
                registration.paid_amount += payment_amount
                registration.save(update_fields=['paid_amount'])

        return render(request, "champs/champs-details-content.html", get_champ_details_context(champ))
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins")
def champ_companion_payment_form(request):
    try:
        champ = get_or_none(Championship, get_param(request.GET, "champ_id"))
        companion = get_or_none(TravelCompanion, get_param(request.GET, "companion_id"))
        if not companion or companion.registration.champ_id != getattr(champ, 'id', None):
            companion = None
        return render(request, "champs/champs-companion-payment-form.html", {'champ': champ, 'companion': companion})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins")
def add_champ_companion_payment(request):
    try:
        champ = get_or_none(Championship, get_param(request.GET, "champ_id"))
        companion = get_or_none(TravelCompanion, get_param(request.GET, "companion_id"))
        amount = get_param(request.GET, "amount", "0").replace(",", ".")

        if companion and companion.registration.champ_id == getattr(champ, 'id', None):
            try:
                payment_amount = Decimal(amount)
            except InvalidOperation:
                payment_amount = Decimal("0.00")
            if payment_amount > 0:
                companion.paid_amount += payment_amount
                companion.save(update_fields=['paid_amount'])

        return render(request, "champs/champs-details-content.html", get_champ_details_context(champ))
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins")
def champ_registration_delete_form(request):
    try:
        champ = get_or_none(Championship, get_param(request.GET, "champ_id"))
        registration = get_or_none(Registration, get_param(request.GET, "registration_id"))
        category = get_or_none(Category, get_param(request.GET, "category_id"))
        if not registration or registration.champ_id != getattr(champ, 'id', None):
            registration = None
        return render(request, "champs/champs-registration-delete-form.html", {
            'champ': champ,
            'registration': registration,
            'category': category,
        })
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins")
def delete_champ_registration(request):
    try:
        champ = get_or_none(Championship, get_param(request.GET, "champ_id"))
        registration = get_or_none(Registration, get_param(request.GET, "registration_id"))
        category = get_or_none(Category, get_param(request.GET, "category_id"))

        if (
            registration
            and category
            and registration.champ_id == getattr(champ, 'id', None)
            and registration.categories.filter(pk=category.pk).exists()
        ):
            registration.categories.remove(category)
            if not registration.categories.exists():
                registration.delete()

        return render(request, "champs/champs-details-content.html", get_champ_details_context(champ))
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins")
def champ_cost_form(request):
    try:
        champ = get_or_none(Championship, get_param(request.GET, "champ_id"))
        champ_cost = get_or_none(ChampCost, get_param(request.GET, "champ_cost_id"))
        context = {
            'champ': champ,
            'champ_cost': champ_cost,
            'cost_list': Cost.objects.all().order_by('name'),
            'category_list': champ.categories.select_related('category').order_by('category__name') if champ else [],
        }
        return render(request, "champs/champs-cost-form.html", context)
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins")
def save_champ_cost(request):
    try:
        champ = get_or_none(Championship, get_param(request.GET, "champ_id"))
        champ_cost = get_or_none(ChampCost, get_param(request.GET, "champ_cost_id"))
        cost = get_or_none(Cost, get_param(request.GET, "cost_id"))
        category = get_or_none(ChampCategory, get_param(request.GET, "category_id"))
        cost_name = get_param(request.GET, "cost_name").strip()
        amount = get_param(request.GET, "amount", "0").replace(",", ".")

        if cost_name:
            cost, created = Cost.objects.get_or_create(name=cost_name)

        if champ and cost:
            try:
                amount = Decimal(amount)
            except InvalidOperation:
                amount = Decimal("0")

            if not champ_cost:
                champ_cost = ChampCost(champ=champ)

            amount_type = get_param(request.GET, "amount_type", ChampCost.AMOUNT_TYPE_PER_COMPETITOR)
            valid_amount_types = [choice[0] for choice in ChampCost.AMOUNT_TYPE_CHOICES]
            if amount_type not in valid_amount_types:
                amount_type = ChampCost.AMOUNT_TYPE_PER_COMPETITOR

            champ_cost.cost = cost
            champ_cost.amount = amount
            champ_cost.amount_type = amount_type
            scope = get_param(request.GET, "scope", ChampCost.SCOPE_ALL_TRAVELERS)
            valid_scopes = [choice[0] for choice in ChampCost.SCOPE_CHOICES]
            if scope not in valid_scopes:
                scope = ChampCost.SCOPE_ALL_TRAVELERS
            champ_cost.scope = scope
            champ_cost.category = category if scope == ChampCost.SCOPE_CATEGORY else None
            champ_cost.save()

        return render(request, "champs/champs-details-content.html", get_champ_details_context(champ))
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins")
def champ_cost_delete_form(request):
    try:
        champ = get_or_none(Championship, get_param(request.GET, "champ_id"))
        champ_cost = get_or_none(ChampCost, get_param(request.GET, "champ_cost_id"))
        return render(request, "champs/champs-cost-delete-form.html", {'champ': champ, 'champ_cost': champ_cost})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins")
def delete_champ_cost(request):
    try:
        champ = get_or_none(Championship, get_param(request.GET, "champ_id"))
        champ_cost = get_or_none(ChampCost, get_param(request.GET, "champ_cost_id"))

        if champ_cost:
            champ_cost.delete()

        return render(request, "champs/champs-details-content.html", get_champ_details_context(champ))
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})


'''
    Championship studen
'''
@group_required("student")
def champs_student(request):
    reg_list = Registration.objects.filter(student=request.student)
    reg_champ_list = [item.champ.id for item in reg_list]
    champ_list = Championship.objects.filter(publish=True).exclude(id__in=reg_champ_list)
    context = {'champ_list': champ_list, 'reg_list': reg_list}
    return render(request, 'champs/champs.html', context)

@group_required("student")
def save_reg(request):
    if request.POST:
        if "categories" in request.POST:
            champ = Championship.objects.get(pk=request.POST["champ"])
            reg = Registration.objects.create(student=request.student, champ=champ)
            for item in request.POST.getlist("categories"):
                reg.categories.add(item)
    return redirect(champs)
 
@group_required("student")
def remove_reg(request, reg_id):
    reg = Registration.objects.get(pk=reg_id)
    reg.delete()
    return redirect(champs)

@group_required("student")
def upload_docs(request):
    if request.POST:
        reg = Registration.objects.get(pk=request.POST["reg"])
        print(request.FILES)
        for key in request.FILES.keys():
            if "file_" in key:
                f_id = key.split("_")[1]
                champ_file = ChampFile.objects.get(pk=f_id)
                rf = RegistrationFile.objects.create(file=request.FILES[key], champ_file=champ_file, reg=reg)
    return redirect(champs)

'''
    Profile
'''
@group_required("student")
def profile(request):
    return render(request, 'profile/profile.html', {'student': request.student})
