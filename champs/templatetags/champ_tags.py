# -*- encoding: utf-8 -*-

from django import template
from django.db.models import Q
from django.utils.safestring import mark_safe
from champs.models import *

register = template.Library()

@register.simple_tag
def get_doc(champ_file, reg):
	for item in reg.registrationfile_set.all():
		if item.champ_file == champ_file:
			return mark_safe('<a href="%s" target="_blank">Documento</a>' % (item.file.url))
	return mark_safe('<input type="file" name="file_%s" />' % (champ_file.id))

@register.simple_tag
def get_reg_costs(reg):
	category_ids = list(reg.categories.values_list('id', flat=True))
	return reg.champ.costs.filter(Q(category__isnull=True) | Q(category__category_id__in=category_ids)).select_related('cost', 'category__category').order_by('category__category__name', 'cost__name')
