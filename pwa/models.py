import uuid
from datetime import date

from django.db import models

from studio.models import Student


def document_file_name(instance, filename, directory):
    """Keep document paths outside of predictable user filenames."""
    extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'pdf'
    return '%s/%s.%s' % (directory, uuid.uuid4().hex, extension)


def document_template_file_name(instance, filename):
    return document_file_name(instance, filename, 'document-templates')


def student_document_file_name(instance, filename):
    return document_file_name(instance, filename, 'students/signed-documents/%s' % instance.student_id)


class DocumentTemplate(models.Model):
    AUDIENCE_ALL = 'all'
    AUDIENCE_MINORS = 'minors'
    AUDIENCE_ADULTS = 'adults'
    AUDIENCE_CHOICES = (
        (AUDIENCE_ALL, 'Todas las alumnas'),
        (AUDIENCE_MINORS, 'Solo menores de edad'),
        (AUDIENCE_ADULTS, 'Solo mayores de edad'),
    )

    title = models.CharField('Título', max_length=200)
    description = models.TextField('Instrucciones', blank=True)
    template_file = models.FileField('Plantilla PDF', upload_to=document_template_file_name)
    audience = models.CharField('Destinatarias', max_length=10, choices=AUDIENCE_CHOICES, default=AUDIENCE_ALL)
    is_active = models.BooleanField('Disponible en la PWA', default=True)
    created_at = models.DateTimeField('Creado el', auto_now_add=True)

    class Meta:
        ordering = ('title',)
        verbose_name = 'tipo de documento'
        verbose_name_plural = 'tipos de documento'

    def __str__(self):
        return self.title

    @classmethod
    def available_for_student(cls, student):
        templates = cls.objects.filter(is_active=True)
        if not student.born_date:
            return templates.filter(audience=cls.AUDIENCE_ALL)
        today = date.today()
        age = today.year - student.born_date.year - (
            (today.month, today.day) < (student.born_date.month, student.born_date.day)
        )
        audience = (cls.AUDIENCE_ALL, cls.AUDIENCE_MINORS if age < 18 else cls.AUDIENCE_ADULTS)
        return templates.filter(audience__in=audience)


class StudentDocument(models.Model):
    """The current signed copy of each document requested from a student."""

    student = models.ForeignKey(
        Student, related_name='uploaded_documents', on_delete=models.CASCADE,
        verbose_name='Alumna',
    )
    template = models.ForeignKey(
        DocumentTemplate, related_name='student_documents', on_delete=models.CASCADE,
        verbose_name='Tipo de documento',
    )
    file = models.FileField('Documento firmado', upload_to=student_document_file_name)
    original_filename = models.CharField('Nombre original', max_length=255)
    uploaded_at = models.DateTimeField('Subido el', auto_now=True)

    class Meta:
        unique_together = ('student', 'template')
        ordering = ('template__title',)
        verbose_name = 'documento de alumna'
        verbose_name_plural = 'documentos de alumnas'

    def __str__(self):
        return '%s — %s' % (self.student, self.template)

# Create your models here.
