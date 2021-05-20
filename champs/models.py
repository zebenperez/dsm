from django.db import models

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

class ChampCost(models.Model):
    amount = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="Importe", default=0)
    cost = models.ForeignKey(Cost, verbose_name="Costo", on_delete=models.SET_NULL, blank=True, null=True)
    champ = models.ForeignKey(Championship, verbose_name="Campeonato", on_delete=models.CASCADE, blank=True, null=True)

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
    champ = models.ForeignKey(Championship, verbose_name="Campeonato", on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        verbose_name = 'Categoría Campeonato'
        verbose_name_plural = 'Categorías Campeonatos'


