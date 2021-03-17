 #Create your views here.

from django.contrib import admin
from django.contrib.auth.models import User, Group
#from django.contrib.sites.models import Site
from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.core.paginator import Paginator, InvalidPage
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render, render_to_response, redirect
from django.utils.translation import ugettext as _
from django.views.decorators.http import require_POST


def index(request):
	return render (request,'web/index.html',{})
