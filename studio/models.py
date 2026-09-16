# -*- encoding: utf-8 -*-

from django.db import models, transaction
from django.db.models import Sum
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import datetime
from django.contrib.auth.models import User
from django.forms import ModelForm
from django import forms

import datetime
import random
import string

# Create your models here.
class Teacher(models.Model):
	active = models.BooleanField(verbose_name="Activo", default=True)
	creation_date = models.DateTimeField(verbose_name="Fecha de creación", auto_now_add=True)
	code = models.BigIntegerField(verbose_name="Código")
	name = models.CharField(max_length=200, verbose_name="Nombre completo")
	phone = models.CharField(max_length=15, verbose_name="Teléfono")
	email = models.EmailField(verbose_name="Correo electrónico", blank=True, null=True)
	user = models.OneToOneField(User, unique=True, on_delete=models.CASCADE, verbose_name="Usuario", blank=True, null=True)

	def __str__(self):
		return u"%s" % (self.name)

	class Meta:
		verbose_name = "Profesor"
		verbose_name_plural = "Profesores"

def my_random_pin():
	chars = string.ascii_uppercase + string.digits
	return ''.join(random.choice(chars) for i in range(4))

def content_file_name(instance, filename):
	instance.filename = filename
	return '/'.join(['students/pictures', datetime.datetime.now().strftime("%Y%m%d%H%M%S") + filename])

def get_year(student):
	try:
		res = datetime.date.today() - student.born_date
		return res.days / 365
	except:
		return ""

class Student(models.Model):
	creation_date = models.DateTimeField(verbose_name="Fecha de creación", auto_now_add=True)
	born_date = models.DateField(verbose_name="Fecha de nacimiento", blank=True, null=True)
	code = models.BigIntegerField(verbose_name="Código",unique=True)
	pin = models.CharField(verbose_name="Pin", max_length=4, default=my_random_pin, unique=True)
	name = models.CharField(max_length=200, verbose_name="Nombre completo")
	phone = models.CharField(max_length=15, verbose_name="Teléfono")
	licence = models.CharField(max_length=15, verbose_name="Licencia", default="", blank=True)
	email = models.EmailField(verbose_name="Correo electrónico", blank=True, null=True)
	user = models.OneToOneField(User, unique=True, on_delete=models.CASCADE, verbose_name="Usuario", blank=True, null=True)
	picture = models.ImageField(upload_to=content_file_name, blank = True, null = True, verbose_name='Foto', help_text="Seleccione una foto para subir")
	band = models.CharField(max_length=15, verbose_name="Pulsera", blank=True, default="")

	def __str__(self):
		#return "%s (%s)"%(self.name, get_year(self))
		return "%s"%(self.name)

	def get_name(self):
		name = self.name.split(" ")
		return f'{name[0]} {name[1]}' if len(name) > 3 else name[0]

	def get_surname(self):
		name = self.name.split(" ")
		return f'{name[2]} {name[3]}' if len(name) > 3 else f'{name[1]} {name[2]}'

	def last_payment(self):
		return Payment.objects.filter(student=self).order_by('-pay_date').first()

	def bad_debt(self):
		payment = self.last_payment() 
		today = datetime.datetime.today()
		return (payment.expire_date.month < today.month and payment.expire_date < today)

	@property
	def wallet_balance(self):
		return self.wallet_movements.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

	class Meta:
		verbose_name = "Alumno"
		verbose_name_plural = "Alumnos"
		ordering = ['name',]

class Group(models.Model):
	active = models.BooleanField(verbose_name="Activo", default=True)
	monday = models.BooleanField(verbose_name="Lunes", default=False)
	tuesday = models.BooleanField(verbose_name="Martes", default=False)
	wednesday = models.BooleanField(verbose_name="Miércoles", default=False)
	thursday = models.BooleanField(verbose_name="Jueves", default=False)
	friday = models.BooleanField(verbose_name="Viernes", default=False)
	saturday = models.BooleanField(verbose_name="Sábado", default=False)
	sunday = models.BooleanField(verbose_name="Domingo", default=False)
	creation_date = models.DateTimeField(verbose_name="Fecha de creación", auto_now_add=True)
	name = models.CharField(max_length=200, verbose_name="Nombre completo")
	ini_time = models.TimeField(verbose_name="Fecha de inicio")
	end_time = models.TimeField(verbose_name="Fecha de fin")
	teacher = models.ForeignKey(Teacher, unique=False, on_delete=models.CASCADE, verbose_name="Profesor")

	def __str__(self):
		daystr = ""
		if self.monday :
			daystr = daystr +"L -"
		if self.tuesday:
			daystr = daystr +"M -"
		if self.wednesday:
			daystr = daystr +"X -"
		if self.thursday:
			daystr = daystr +"J -"
		if self.friday:
			daystr = daystr +"V -"
		if self.saturday:
			daystr = daystr +"S -"
		if self.sunday:
			daystr = daystr +"D"
		#return '%s - %s [%s (%s)]'  % (self.teacher.name.encode('utf-8'), self.name.encode('utf-8'), daystr, str(self.ini_time)[:5])
		return u'%s %s [%s (%s)]' % (self.teacher.name, self.name, daystr, str(self.ini_time)[:5])
		#return '%s' % (self.teacher)

	def get_name(self):
		daystr = ""
		if self.monday :
			daystr = daystr +"L -"
		if self.tuesday:
			daystr = daystr +"M -"
		if self.wednesday:
			daystr = daystr +"X -"
		if self.thursday:
			daystr = daystr +"J -"
		if self.friday:
			daystr = daystr +"V -"
		if self.saturday:
			daystr = daystr +"S -"
		if self.sunday:
			daystr = daystr +"D"
		return '%s [%s (%s)]' % (self.name, daystr, str(self.ini_time)[:5])

	def get_full_name(self):
		daystr = ""
		if self.monday :
			daystr = daystr +"L -"
		if self.tuesday:
			daystr = daystr +"M -"
		if self.wednesday:
			daystr = daystr +"X -"
		if self.thursday:
			daystr = daystr +"J -"
		if self.friday:
			daystr = daystr +"V -"
		if self.saturday:
			daystr = daystr +"S -"
		if self.sunday:
			daystr = daystr +"D"
		return '%s %s [%s (%s)]' % (self.teacher.name, self.name, daystr, str(self.ini_time)[:5])

	class Meta:
		verbose_name = "Grupo"
		verbose_name_plural = "Grupos"
		ordering = ['teacher__name',]


class Enrolment(models.Model):
    active = models.BooleanField(verbose_name="Activo", default=True)
    creation_date = models.DateTimeField(verbose_name="Fecha de creación", auto_now_add=True)
    percent_studio = models.BigIntegerField(verbose_name="% Escuela", default=50)
    percent_teacher = models.BigIntegerField(verbose_name="% Profesor", default=50)
    price = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Precio", default=30)
    group = models.ForeignKey(Group, unique=False, on_delete=models.CASCADE, verbose_name="Grupo")
    student = models.ForeignKey(Student, unique=False, on_delete=models.CASCADE, verbose_name="Alumno", related_name="enrolment")

    def __str__(self):
    	#return u'%s - %s' % (self.student, self.group)
    	return u'%s' % (self.group)

    class Meta:
        verbose_name = "Matrícula"
        verbose_name_plural = "Matrículas"
	

class Concept(models.Model):
    code = models.CharField(max_length=10, verbose_name="Código")
    name = models.CharField(max_length=200, verbose_name="Nombre")
	
    def __str__(self):
        return str(self.name)

    class Meta:
        verbose_name = "Concepto"
        verbose_name_plural = "Conceptos"

class Payment(models.Model):
	card = models.BooleanField(verbose_name="Tarjeta", default=False)
	#teacher = models.BooleanField(verbose_name="Profesor", default=True)
	amount = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Cantidad")
	note = models.CharField(max_length=200, verbose_name="Nota")
	date = models.DateTimeField(verbose_name="Fecha")
	pay_date = models.DateTimeField(verbose_name="Fecha de pago")
	expire_date = models.DateTimeField(verbose_name="Fecha de caducidad")
	student = models.ForeignKey(Student, unique=False, on_delete=models.CASCADE, verbose_name="Alumno")
	enrolment = models.ForeignKey(Enrolment, unique=False, on_delete=models.CASCADE, verbose_name="Matrícula")
	#concept = models.ForeignKey(Concept, unique=False, verbose_name="Concepto")
	
	def __str__(self):
		return str(self.amount)

	class Meta:
		verbose_name = "Pago"
		verbose_name_plural = "Pagos"
		ordering = ['-pay_date',]
	
class TeacherPayment(models.Model):
	note = models.CharField(max_length=200, blank=True , verbose_name="Nota")
	date = models.DateTimeField(verbose_name="Fecha")
	card = models.BooleanField(verbose_name="Tarjeta", default=False)
	amount = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Cantidad")
	teacher = models.ForeignKey(Teacher, unique=False, on_delete=models.CASCADE, verbose_name="Profesor")
	concept = models.ForeignKey(Concept, unique=False, on_delete=models.CASCADE, verbose_name="Concepto")

	class Meta:
		verbose_name = "Pago a profesores"
		verbose_name_plural = "Pagos a profesores"
	
class Article(models.Model):
	publish = models.BooleanField(verbose_name="Publicado", default=True)
	code = models.CharField(max_length=10, verbose_name="Código")
	name = models.CharField(max_length=200, verbose_name="Nombre")
	cost = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Costo")
	pvp = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Pvp")
	stock = models.BigIntegerField(verbose_name="Stock")
	
	def __str__(self):
		return str(self.name)

	class Meta:
		verbose_name = "Artículo"
		verbose_name_plural = "Artículos"

class ArticlePayment(models.Model):
	note = models.CharField(max_length=200, blank=True , verbose_name="Nota")
	date = models.DateTimeField(verbose_name="Fecha", auto_now_add=True)
	card = models.BooleanField(verbose_name="Tarjeta", default=False)
	amount = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Cantidad")
	article = models.ForeignKey(Article, unique=False, on_delete=models.CASCADE, verbose_name="Artículo")
	concept = models.ForeignKey(Concept, unique=False, on_delete=models.CASCADE, verbose_name="Concepto")

	class Meta:
		verbose_name = "Pago de artículos"
		verbose_name_plural = "Pagos de artículos"


class InsufficientWalletBalance(Exception):
	pass


class WalletMovement(models.Model):
	TYPE_TOP_UP = 'top_up'
	TYPE_PURCHASE = 'purchase'
	TYPE_REFUND = 'refund'
	TYPE_ADJUSTMENT = 'adjustment'
	TYPE_CHOICES = (
		(TYPE_TOP_UP, 'Recarga'),
		(TYPE_PURCHASE, 'Pago'),
		(TYPE_REFUND, 'Devolución'),
		(TYPE_ADJUSTMENT, 'Ajuste'),
	)

	METHOD_CASH = 'cash'
	METHOD_CARD = 'card'
	METHOD_TRANSFER = 'transfer'
	METHOD_CHOICES = (
		(METHOD_CASH, 'Efectivo'),
		(METHOD_CARD, 'Tarjeta'),
		(METHOD_TRANSFER, 'Transferencia'),
	)

	student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='wallet_movements', verbose_name='Alumna/o')
	amount = models.DecimalField(max_digits=8, decimal_places=2, verbose_name='Importe')
	movement_type = models.CharField(max_length=12, choices=TYPE_CHOICES, verbose_name='Tipo')
	payment_method = models.CharField(max_length=12, choices=METHOD_CHOICES, blank=True, verbose_name='Método de recarga')
	description = models.CharField(max_length=200, blank=True, verbose_name='Concepto')
	created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha')
	created_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='wallet_movements', verbose_name='Registrado por')

	class Meta:
		verbose_name = 'movimiento de monedero'
		verbose_name_plural = 'movimientos de monedero'
		ordering = ('-created_at', '-id')
		constraints = [
			models.CheckConstraint(condition=~models.Q(amount=0), name='wallet_movement_amount_not_zero'),
		]

	def __str__(self):
		return '%s · %s €' % (self.student, self.amount)

	def clean(self):
		if self.amount == 0:
			raise ValidationError({'amount': 'El importe debe ser distinto de cero.'})
		if self.movement_type in (self.TYPE_TOP_UP, self.TYPE_REFUND) and self.amount < 0:
			raise ValidationError({'amount': 'Las recargas y devoluciones deben ser positivas.'})
		if self.movement_type == self.TYPE_PURCHASE and self.amount > 0:
			raise ValidationError({'amount': 'Los pagos deben restar saldo.'})

	@classmethod
	def record(cls, student, amount, movement_type, description='', payment_method='', created_by=None):
		"""Create an immutable wallet entry, never allowing a negative balance."""
		amount = Decimal(amount)
		with transaction.atomic():
			locked_student = Student.objects.select_for_update().get(pk=student.pk)
			balance = cls.objects.filter(student=locked_student).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
			if balance + amount < 0:
				raise InsufficientWalletBalance
			movement = cls(
				student=locked_student,
				amount=amount,
				movement_type=movement_type,
				description=description,
				payment_method=payment_method,
				created_by=created_by,
			)
			movement.full_clean()
			movement.save()
			return movement
	
class Cash(models.Model):
	i_card = models.IntegerField(verbose_name="Tarjeta apertura", blank=True, null=True, default=0)
	e_card = models.IntegerField(verbose_name="Tarjeta cierre", blank=True, null=True)
	i_50000 = models.IntegerField(verbose_name="500", blank=True, null=True)
	i_20000 = models.IntegerField(verbose_name="200", blank=True, null=True)
	i_10000 = models.IntegerField(verbose_name="100", blank=True, null=True)
	i_05000 = models.IntegerField(verbose_name="50", blank=True, null=True)
	i_02000 = models.IntegerField(verbose_name="20", blank=True, null=True)
	i_01000 = models.IntegerField(verbose_name="10", blank=True, null=True)
	i_00500 = models.IntegerField(verbose_name="5", blank=True, null=True)
	i_00200 = models.IntegerField(verbose_name="2", blank=True, null=True)
	i_00100 = models.IntegerField(verbose_name="1", blank=True, null=True)
	i_00050 = models.IntegerField(verbose_name="0,5", blank=True, null=True)
	i_00020 = models.IntegerField(verbose_name="0,2", blank=True, null=True)
	i_00010 = models.IntegerField(verbose_name="0,1", blank=True, null=True)
	i_00005 = models.IntegerField(verbose_name="0,05", blank=True, null=True)
	i_00002 = models.IntegerField(verbose_name="0,02", blank=True, null=True)
	i_00001 = models.IntegerField(verbose_name="0,01", blank=True, null=True)
	e_50000 = models.IntegerField(verbose_name="500", blank=True, null=True)
	e_20000 = models.IntegerField(verbose_name="200", blank=True, null=True)
	e_10000 = models.IntegerField(verbose_name="100", blank=True, null=True)
	e_05000 = models.IntegerField(verbose_name="50", blank=True, null=True)
	e_02000 = models.IntegerField(verbose_name="20", blank=True, null=True)
	e_01000 = models.IntegerField(verbose_name="10", blank=True, null=True)
	e_00500 = models.IntegerField(verbose_name="5", blank=True, null=True)
	e_00200 = models.IntegerField(verbose_name="2", blank=True, null=True)
	e_00100 = models.IntegerField(verbose_name="1", blank=True, null=True)
	e_00050 = models.IntegerField(verbose_name="0,5", blank=True, null=True)
	e_00020 = models.IntegerField(verbose_name="0,2", blank=True, null=True)
	e_00010 = models.IntegerField(verbose_name="0,1", blank=True, null=True)
	e_00005 = models.IntegerField(verbose_name="0,05", blank=True, null=True)
	e_00002 = models.IntegerField(verbose_name="0,02", blank=True, null=True)
	e_00001 = models.IntegerField(verbose_name="0,01", blank=True, null=True)
	i_total = models.DecimalField(max_digits=7, decimal_places=2, verbose_name="Total apertura", blank=True, null=True)
	e_total = models.DecimalField(max_digits=7, decimal_places=2, verbose_name="Total cierre", blank=True, null=True)
	i_note = models.CharField(max_length=1000, blank=True , verbose_name="Nota apertura")
	e_note = models.CharField(max_length=1000, blank=True , verbose_name="Nota cierre")
	date = models.DateTimeField(verbose_name="Fecha", auto_now_add=True)

	class Meta:
		verbose_name = "Caja"
		verbose_name_plural = "Cajas"

class Assistance(models.Model):
	date = models.DateField(verbose_name="Fecha")
	group = models.ForeignKey(Group, unique=False, on_delete=models.CASCADE, verbose_name="Group")
	enrolments = models.ManyToManyField('Enrolment', related_name='enrolemnts')

	def __str__(self):
		return "%s - %s" % (self.date, self.group)

	class Meta:
		verbose_name = "Asistencia"
		verbose_name_plural = "Asistenciass"


class Notification(models.Model):
	date = models.DateField(verbose_name="Fecha", auto_now_add=True)
	msg = models.TextField(verbose_name="Mensaje", default="")
	students = models.ManyToManyField('Student', verbose_name="Alumnos", blank=True)

	class Meta:
		verbose_name='Notificacion'
		verbose_name_plural='Notificaciones'

	def __str__(self):
		return "%s" % (self.msg)
