from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.utils import timezone

from studio.models import Group, Student


class FormQuerySet(models.QuerySet):
    def for_student(self, student):
        """Return forms that are available to a student's active groups.

        A form without recipient groups is available to every student, which
        preserves the behaviour of forms created before group targeting.
        """
        return self.filter(
            Q(target_groups__isnull=True) |
            Q(target_groups__enrolment__student=student,
              target_groups__enrolment__active=True)
        ).distinct()


class Form(models.Model):
    title = models.CharField('Título', max_length=200)
    description = models.TextField('Descripción', blank=True)
    image = models.ImageField('Imagen', upload_to='forms/', blank=True)
    is_published = models.BooleanField('Publicado', default=False)
    deadline = models.DateTimeField('Fecha límite', blank=True, null=True)
    allow_response_changes = models.BooleanField('Permitir cambiar la respuesta', default=False)
    target_groups = models.ManyToManyField(
        Group,
        verbose_name='Grupos destinatarios',
        related_name='registration_forms',
        blank=True,
        help_text='Déjalo vacío para que puedan verlo todas las alumnas.',
    )
    created_at = models.DateTimeField('Creado el', auto_now_add=True)

    objects = FormQuerySet.as_manager()

    class Meta:
        ordering = ('-created_at', 'title')
        verbose_name = 'formulario'
        verbose_name_plural = 'formularios'

    def __str__(self):
        return self.title

    @property
    def is_open(self):
        return self.is_published and (self.deadline is None or self.deadline >= timezone.now())


class FormQuestion(models.Model):
    ANSWER_TYPE_YES_NO = 'yes_no'
    ANSWER_TYPE_SHORT_TEXT = 'short_text'
    ANSWER_TYPE_CHOICES = (
        (ANSWER_TYPE_YES_NO, 'Sí o no'),
        (ANSWER_TYPE_SHORT_TEXT, 'Texto corto'),
    )

    form = models.ForeignKey(Form, verbose_name='Formulario', related_name='questions', on_delete=models.CASCADE)
    text = models.CharField('Pregunta', max_length=500)
    answer_type = models.CharField('Tipo de respuesta', max_length=20, choices=ANSWER_TYPE_CHOICES)
    required = models.BooleanField('Obligatoria', default=False)
    position = models.PositiveIntegerField('Orden', default=0)

    class Meta:
        ordering = ('position', 'id')
        verbose_name = 'pregunta de formulario'
        verbose_name_plural = 'preguntas de formulario'

    def __str__(self):
        return self.text


class FormSubmission(models.Model):
    form = models.ForeignKey(Form, verbose_name='Formulario', related_name='submissions', on_delete=models.CASCADE)
    student = models.ForeignKey(Student, verbose_name='Alumna', related_name='form_submissions', on_delete=models.CASCADE)
    submitted_at = models.DateTimeField('Enviado el', auto_now_add=True)

    class Meta:
        unique_together = ('form', 'student')
        ordering = ('-submitted_at',)
        verbose_name = 'respuesta de formulario'
        verbose_name_plural = 'respuestas de formulario'

    def __str__(self):
        return '%s — %s' % (self.form, self.student)


class FormAnswer(models.Model):
    submission = models.ForeignKey(FormSubmission, verbose_name='Respuesta', related_name='answers', on_delete=models.CASCADE)
    question = models.ForeignKey(FormQuestion, verbose_name='Pregunta', related_name='answers', on_delete=models.CASCADE)
    short_text = models.CharField('Texto', max_length=500, blank=True)
    yes_no = models.BooleanField('Sí o no', null=True, blank=True)

    class Meta:
        unique_together = ('submission', 'question')
        verbose_name = 'respuesta a pregunta'
        verbose_name_plural = 'respuestas a preguntas'

    def __str__(self):
        return '%s: %s' % (self.question, self.value)

    def clean(self):
        if self.submission_id and self.question_id:
            if self.submission.form_id != self.question.form_id:
                raise ValidationError('La pregunta debe pertenecer al formulario respondido.')

    @property
    def value(self):
        if self.question.answer_type == FormQuestion.ANSWER_TYPE_YES_NO:
            if self.yes_no is None:
                return ''
            return 'Sí' if self.yes_no else 'No'
        return self.short_text
