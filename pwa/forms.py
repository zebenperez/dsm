from django import forms
from django.core.exceptions import ValidationError

from studio.models import Student


class ComplementaryDataForm(forms.ModelForm):
    """The personal details a student can safely update from the PWA."""

    class Meta:
        model = Student
        fields = (
            'email', 'phone', 'dni', 'dni_expiry_date', 'sex', 'nationality',
            'address', 'postal_code', 'municipality', 'province', 'autonomous_community',
            'dni_front', 'dni_back',
        )
        widgets = {
            'email': forms.EmailInput(attrs={'autocomplete': 'email'}),
            'phone': forms.TextInput(attrs={'inputmode': 'tel', 'autocomplete': 'tel'}),
            'dni': forms.TextInput(attrs={'autocapitalize': 'characters'}),
            'dni_expiry_date': forms.DateInput(attrs={'type': 'date'}),
            'sex': forms.Select(choices=(
                ('', 'Selecciona una opción'),
                ('Masculino', 'Masculino'),
                ('Femenino', 'Femenino'),
                ('Otros', 'Otros'),
            )),
            'nationality': forms.TextInput(attrs={'autocomplete': 'country-name'}),
            'address': forms.TextInput(attrs={'autocomplete': 'street-address'}),
            'postal_code': forms.TextInput(attrs={
                'inputmode': 'numeric', 'autocomplete': 'postal-code', 'maxlength': '5',
            }),
            'municipality': forms.TextInput(attrs={'autocomplete': 'address-level2'}),
            'province': forms.TextInput(attrs={'autocomplete': 'address-level1'}),
            'autonomous_community': forms.TextInput(attrs={'autocomplete': 'address-level1'}),
            'dni_front': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
            'dni_back': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in self.fields:
            self.fields[field_name].required = True
        if not self.is_bound:
            for field_name, default_value in (
                ('province', 'Santa Cruz de Tenerife'),
                ('autonomous_community', 'Canarias'),
            ):
                if not getattr(self.instance, field_name):
                    self.initial[field_name] = default_value

    def clean_postal_code(self):
        postal_code = self.cleaned_data['postal_code'].strip()
        if len(postal_code) != 5 or not postal_code.isdigit():
            raise ValidationError('Introduce un código postal de cinco cifras.')
        return postal_code

    def clean_municipality(self):
        municipality = self.cleaned_data['municipality'].strip()
        if not municipality:
            raise ValidationError('Indica tu municipio de residencia.')
        return municipality

    def clean_dni(self):
        dni = self.cleaned_data['dni'].strip().upper()
        if len(dni) < 7:
            raise ValidationError('Introduce un DNI válido.')
        return dni

    def clean(self):
        cleaned_data = super().clean()
        for field_name, label in (('dni_front', 'anverso del DNI'), ('dni_back', 'reverso del DNI')):
            image = cleaned_data.get(field_name)
            if image is False:
                self.add_error(field_name, 'La foto del %s es obligatoria.' % label)
            elif not image and not getattr(self.instance, field_name):
                self.add_error(field_name, 'Añade una foto del %s.' % label)
            elif image and image.size > 10 * 1024 * 1024:
                self.add_error(field_name, 'La imagen no puede superar los 10 MB.')
        return cleaned_data
