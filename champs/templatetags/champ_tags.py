# -*- encoding: utf-8 -*-

from django import template
from django.utils.safestring import mark_safe
from champs.models import *

register = template.Library()

@register.simple_tag
def get_doc(champ_file, reg):
	for item in reg.registrationfile_set.all():
		if item.champ_file == champ_file:
			return mark_safe('<a href="%s" target="_blank">Documento</a>' % (item.file.url))
	return mark_safe('<input type="file" name="file_%s" />' % (champ_file.id))
