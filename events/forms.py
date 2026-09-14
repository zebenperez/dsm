from datetime import datetime, time

from django import forms

from .models import Event


class EventForm(forms.ModelForm):
    starts_at = forms.DateField(
        label='Fecha de inicio',
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={'class': 'form-control', 'type': 'date'},
        ),
    )
    starts_time = forms.TimeField(
        label='Hora de inicio',
        required=False,
        widget=forms.TimeInput(
            format='%H:%M',
            attrs={'class': 'form-control', 'type': 'time'},
        ),
    )

    class Meta:
        model = Event
        fields = ('title', 'starts_at', 'ends_at', 'description')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'autofocus': True}),
            'ends_at': forms.DateTimeInput(
                format='%Y-%m-%dT%H:%M',
                attrs={'class': 'form-control', 'type': 'datetime-local'},
            ),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['starts_at'].input_formats = ('%Y-%m-%d',)
        self.fields['starts_time'].input_formats = ('%H:%M',)
        self.fields['ends_at'].input_formats = ('%Y-%m-%dT%H:%M',)
        if self.instance.pk:
            self.initial['starts_at'] = self.instance.starts_at.date()
            if self.instance.starts_at_has_time:
                self.initial['starts_time'] = self.instance.starts_at.time()
                if self.instance.ends_at:
                    self.initial['ends_at'] = self.instance.ends_at.replace(
                        hour=self.instance.starts_at.hour,
                        minute=self.instance.starts_at.minute,
                        second=0,
                        microsecond=0,
                    )

    def clean(self):
        cleaned_data = super().clean()
        starts_date = cleaned_data.get('starts_at')
        starts_time = cleaned_data.get('starts_time')
        starts_at = (
            datetime.combine(starts_date, starts_time or time.min)
            if starts_date else None
        )
        cleaned_data['starts_at'] = starts_at
        ends_at = cleaned_data.get('ends_at')
        if ends_at and starts_time:
            ends_at = ends_at.replace(
                hour=starts_time.hour,
                minute=starts_time.minute,
                second=0,
                microsecond=0,
            )
            cleaned_data['ends_at'] = ends_at
        if starts_at and ends_at and ends_at < starts_at:
            self.add_error('ends_at', 'La fecha de fin debe ser posterior al inicio.')
        return cleaned_data

    def save(self, commit=True):
        self.instance.starts_at_has_time = bool(self.cleaned_data.get('starts_time'))
        return super().save(commit=commit)
