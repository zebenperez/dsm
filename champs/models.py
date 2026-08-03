from django.db import models
from studio.models import Student

import datetime


class Cost(models.Model):
    name = models.CharField(max_length=200, verbose_name="Nombre", default="")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Coste'
        verbose_name_plural = 'Costes'

class Category(models.Model):
    name = models.CharField(max_length=200, verbose_name="Nombre", default="")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'

class Championship(models.Model):
    publish = models.BooleanField(verbose_name='Publicado', default=False)
    date = models.DateField('Fecha', default=datetime.datetime.today)
    name = models.CharField(max_length=200, verbose_name="Nombre", default="")
    location = models.CharField(max_length=900, verbose_name="Localización", default="")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Campeonato'
        verbose_name_plural = 'Campeonatos'


class ChampioshipInfo(models.Model):
    champ = models.OneToOneField(
        Championship,
        verbose_name="Campeonato",
        on_delete=models.CASCADE,
        related_name="info",
    )
    outbound_date = models.DateField("Fecha de ida", blank=True, null=True)
    return_date = models.DateField("Fecha de vuelta", blank=True, null=True)
    carrier_name = models.CharField(max_length=200, verbose_name="Nombre del transportista", blank=True, default="")
    details = models.TextField(verbose_name="Detalles", blank=True, default="")
    accommodation_name = models.CharField(max_length=200, verbose_name="Nombre de la estancia", blank=True, default="")

    class Meta:
        verbose_name = 'Información del campeonato'
        verbose_name_plural = 'Información de los campeonatos'

class ChampCost(models.Model):
    AMOUNT_TYPE_PER_COMPETITOR = 'per_competitor'
    AMOUNT_TYPE_GLOBAL = 'global'
    AMOUNT_TYPE_CHOICES = (
        (AMOUNT_TYPE_PER_COMPETITOR, 'Por competidora'),
        (AMOUNT_TYPE_GLOBAL, 'Global'),
    )
    SCOPE_ALL_TRAVELERS = 'all_travelers'
    SCOPE_CATEGORY = 'category'
    SCOPE_COMPANIONS = 'companions'
    SCOPE_CHOICES = (
        (SCOPE_ALL_TRAVELERS, 'Todos los viajeros'),
        (SCOPE_CATEGORY, 'Solo una categoría'),
        (SCOPE_COMPANIONS, 'Solo acompañantes'),
    )

    amount = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="Importe", default=0)
    amount_type = models.CharField(max_length=20, choices=AMOUNT_TYPE_CHOICES, default=AMOUNT_TYPE_PER_COMPETITOR, verbose_name="Tipo de importe")
    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES, default=SCOPE_ALL_TRAVELERS, verbose_name="Aplica a")
    cost = models.ForeignKey(Cost, verbose_name="Costo", on_delete=models.SET_NULL, blank=True, null=True)
    champ = models.ForeignKey(Championship, verbose_name="Campeonato", on_delete=models.CASCADE, blank=True, null=True, related_name="costs")
    category = models.ForeignKey('ChampCategory', verbose_name="Categoría", on_delete=models.CASCADE, blank=True, null=True, related_name="costs")

    class Meta:
        verbose_name = 'Costo Campeonato'
        verbose_name_plural = 'Costos Campeonatos'

def upload_champ_file(instance, filename):
    ascii_filename = str(filename.encode('ascii', 'ignore'))
    instance.filename = ascii_filename
    folder = "champs/files/%s" % (instance.champ.id)
    return '/'.join(['%s' % (folder), datetime.datetime.now().strftime("%Y%m%d%H%M%S") + ascii_filename])

class ChampFile(models.Model):
    file = models.FileField(upload_to=upload_champ_file, blank=True, verbose_name="Fichero", help_text="Select file to upload")
    name = models.CharField(max_length=200, verbose_name="Nombre", default="")
    champ = models.ForeignKey(Championship, verbose_name="Campeonato", on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        verbose_name = 'Documento Campeonato'
        verbose_name_plural = 'Documentos Campeonatos'

class ChampCategory(models.Model):
    amount = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="Importe", default=0)
    category = models.ForeignKey(Category, verbose_name="Categoría", on_delete=models.SET_NULL, blank=True, null=True)
    champ = models.ForeignKey(Championship, verbose_name="Campeonato", on_delete=models.CASCADE, blank=True, null=True, related_name="categories")

    class Meta:
        verbose_name = 'Categoría Campeonato'
        verbose_name_plural = 'Categorías Campeonatos'

class Registration(models.Model):
    student = models.ForeignKey(Student, verbose_name="Alumno", on_delete=models.SET_NULL, blank=True, null=True)
    champ = models.ForeignKey(Championship, verbose_name="Campeonato", on_delete=models.CASCADE, blank=True, null=True)
    categories = models.ManyToManyField(Category, related_name='registrations', blank=True)
    paid_amount = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Importe pagado", default=0)
    position = models.CharField(max_length=100, verbose_name="Posición", blank=True, default="")
    payment_proof = models.FileField(upload_to='regs/payment-proofs/', blank=True, verbose_name="Justificante de pago")

    class Meta:
        verbose_name = 'Inscripción'
        verbose_name_plural = 'Inscripciones'


class TravelCompanion(models.Model):
    registration = models.ForeignKey(Registration, verbose_name="Inscripción", on_delete=models.CASCADE, related_name="travel_companions")
    full_name = models.CharField(max_length=200, verbose_name="Nombre completo")
    is_canary_resident = models.BooleanField(default=False, verbose_name="Residente en Canarias")
    municipality = models.CharField(max_length=200, blank=True, default="", verbose_name="Municipio de residencia")
    birth_date = models.DateField(verbose_name="Fecha de nacimiento")
    dni = models.CharField(max_length=20, verbose_name="DNI")
    paid_amount = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Importe pagado", default=0)

    class Meta:
        verbose_name = 'Acompañante de viaje'
        verbose_name_plural = 'Acompañantes de viaje'

def upload_reg_file(instance, filename):
    ascii_filename = str(filename.encode('ascii', 'ignore'))
    instance.filename = ascii_filename
    folder = "regs/files/%s" % (instance.reg.id)
    return '/'.join(['%s' % (folder), datetime.datetime.now().strftime("%Y%m%d%H%M%S") + ascii_filename])

class RegistrationFile(models.Model):
    file = models.FileField(upload_to=upload_reg_file, blank=True, verbose_name="Fichero", help_text="Select file to upload")
    champ_file = models.ForeignKey(ChampFile, verbose_name="Tipo de fichero", on_delete=models.SET_NULL, blank=True, null=True)
    reg = models.ForeignKey(Registration, verbose_name="Inscripcion", on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        verbose_name = 'Inscripción fichero'
        verbose_name_plural = 'Inscripciones ficheros'
