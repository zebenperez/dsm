from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import get_template, render_to_string
from django.utils.html import strip_tags


def web_send_mail(template_path, context, subject, from_email ,to):
	html_content = render_to_string(template_path,context)
	text_content = strip_tags(html_content)
	msg = EmailMultiAlternatives(subject, text_content, from_email,to)
	msg.attach_alternative(html_content, "text/html")
	print(msg.send())

def get_element (model,pk):

	response = {}
	try :
		response = model.objects.get(pk=int(pk))
	except ObjectDoesNotExist:
		response = False;

	return response 
