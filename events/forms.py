from django import forms

from .models import Event


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ('title', 'starts_at', 'ends_at', 'description')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'autofocus': True}),
            'starts_at': forms.DateTimeInput(
                format='%Y-%m-%dT%H:%M',
                attrs={'class': 'form-control', 'type': 'datetime-local'},
            ),
            'ends_at': forms.DateTimeInput(
                format='%Y-%m-%dT%H:%M',
                attrs={'class': 'form-control', 'type': 'datetime-local'},
            ),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['starts_at'].input_formats = ('%Y-%m-%dT%H:%M',)
        self.fields['ends_at'].input_formats = ('%Y-%m-%dT%H:%M',)

    def clean(self):
        cleaned_data = super().clean()
        starts_at = cleaned_data.get('starts_at')
        ends_at = cleaned_data.get('ends_at')
        if starts_at and ends_at and ends_at < starts_at:
            self.add_error('ends_at', 'La fecha de fin debe ser posterior al inicio.')
        return cleaned_data
