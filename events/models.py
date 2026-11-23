from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator


class Event(models.Model):
    title = models.CharField('Título', max_length=200)
    starts_at = models.DateTimeField('Inicio')
    starts_at_has_time = models.BooleanField(default=True)
    ends_at = models.DateTimeField('Fin', blank=True, null=True)
    description = models.TextField('Descripción', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('starts_at', 'title')
        verbose_name = 'evento'
        verbose_name_plural = 'eventos'

    def __str__(self):
        return self.title


class PublicDisplaySettings(models.Model):
    """Singleton configuration for the public birthday/events display."""
    rotation_enabled = models.BooleanField('Activar rotación automática', default=True)
    rotation_interval_seconds = models.PositiveIntegerField(
        'Duración de cada pantalla (segundos)',
        default=60,
        validators=[MinValueValidator(10), MaxValueValidator(3600)],
        help_text='Entre 10 segundos y 1 hora.',
    )

    class Meta:
        verbose_name = 'pantalla pública'
        verbose_name_plural = 'pantalla pública'

    def save(self, *args, **kwargs):
        self.pk = 1
        super(PublicDisplaySettings, self).save(*args, **kwargs)

    @classmethod
    def current(cls):
        return cls.objects.filter(pk=1).first() or cls()
