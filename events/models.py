from django.db import models


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
