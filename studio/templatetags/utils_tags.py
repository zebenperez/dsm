from django import template
from django.conf import settings

from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _,  to_locale, get_language, ugettext as ugt
from django.db.models import Count

register= template.Library();

# Render with context processors shortcut
def render_template(request, template_path, extra_context = {}):
	c = RequestContext(request)
	c.update(extra_context)
	return render_to_string(template_path, context_instance=c)


@register.filter
def get_range(limit):
	return range(1 ,int(limit) +1)


@register.filter
def element_exists(list,elem_str):
	return elem_str in list

@register.filter
def contains(value, arg):
	return value in arg

@register.filter(name='addcss')
def addcss(field, css):
   return field.as_widget(attrs={"class":css})

@register.filter(name='get')
def get(o, index):
    try:
        return o[index]
    except:
        return settings.TEMPLATE_STRING_IF_INVALID

@register.filter
def mysplit(value, sep = "."):
    parts = value.split(sep)
    return (parts[0], sep.join(parts[1:]))
