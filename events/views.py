from datetime import date, datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import EventForm
from .models import Event

MONTH_NAMES = (
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
)
WEEKDAY_NAMES = ('Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo')


def _add_months(year, month, offset):
    absolute_month = year * 12 + (month - 1) + offset
    return absolute_month // 12, absolute_month % 12 + 1


@login_required
def month(request, year=None, month=None):
    today = date.today()
    year = int(year or request.GET.get('year', today.year))
    month = int(month or request.GET.get('month', today.month))
    if month not in range(1, 13):
        return redirect('events:month')

    first_day = date(year, month, 1)
    next_year, next_month = _add_months(year, month, 1)
    next_first_day = date(next_year, next_month, 1)
    grid_start = first_day - timedelta(days=first_day.weekday())
    grid_end = next_first_day + timedelta(days=(6 - next_first_day.weekday()) % 7)

    events = Event.objects.filter(
        Q(starts_at__date__gte=grid_start, starts_at__date__lt=grid_end)
    )
    events_by_day = {}
    for event in events:
        events_by_day.setdefault(event.starts_at.date(), []).append(event)

    weeks = []
    current_day = grid_start
    while current_day < grid_end:
        week = []
        for _ in range(7):
            week.append({
                'date': current_day,
                'in_month': current_day.month == month,
                'events': events_by_day.get(current_day, []),
            })
            current_day += timedelta(days=1)
        weeks.append(week)

    previous = _add_months(year, month, -1)
    following = _add_months(year, month, 1)
    return render(request, 'calendar/month.html', {
        'weeks': weeks,
        'month_name': MONTH_NAMES[month - 1],
        'year': year,
        'previous': previous,
        'following': following,
        'weekday_names': WEEKDAY_NAMES,
        'today': today,
    })


@login_required
def event_add(request):
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save()
            return redirect(reverse('events:month_by_date', args=(event.starts_at.year, event.starts_at.month)))
    else:
        selected_date = request.GET.get('date')
        initial = {}
        try:
            initial['starts_at'] = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except (TypeError, ValueError):
            pass
        form = EventForm(initial=initial)
    return render(request, 'calendar/event_form.html', {
        'form': form,
        'page_title': 'Añadir evento',
    })


@login_required
def event_edit(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if request.method == 'POST':
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            event = form.save()
            return redirect(reverse('events:month_by_date', args=(event.starts_at.year, event.starts_at.month)))
    else:
        form = EventForm(instance=event)
    return render(request, 'calendar/event_form.html', {
        'form': form,
        'event': event,
        'page_title': 'Editar evento',
    })


@login_required
def event_delete(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if request.method == 'POST':
        year, month = event.starts_at.year, event.starts_at.month
        event.delete()
        return redirect(reverse('events:month_by_date', args=(year, month)))
    return render(request, 'calendar/event_confirm_delete.html', {'event': event})
