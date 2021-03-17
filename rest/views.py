# -*- coding: utf-8 -*-
from django.http import Http404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.decorators import action
#from rest_framework.decorators import detail_route
from rest_framework import permissions
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated

from rest.serializers import *
from rest.permissions import IsAdminOrIsEstablishment

from studio.models import *

from django.contrib.auth.models import Group, User
from django.contrib.gis.measure import D
from django.contrib.gis.geos import fromstr, Point
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
#from django.form.fields import email_re

from django.utils.translation import ugettext as _

#from push_notifications.models import APNSDevice, GCMDevice
from fcm_django.models import FCMDevice

from datetime import date, datetime
from dateutil.relativedelta import relativedelta

import json
import string
import random

from django.http import HttpResponse

class PaymentsViewSet(viewsets.ViewSet):
	queryset = Payment.objects.all()
	serializer_class = PaymentSerializer
	model = Payment

	def list(self, request):
		payments = Payment.objects.all()
		serializer = PaymentSerializer(payments, many=True)
		return Response(serializer.data)

	#@action(permission_classes=[])
	#@detail_route(methods=['post'])
	@action(detail=False, methods=['get'])
	def check_pin(self, request, pk=None):
		device_id = request.POST["device_id"]
		register_id = request.POST["register_id"]
		students = Student.objects.filter(pin=request.POST["pin"])
		if len(students) > 0:
			devices = FCMDevice.objects.filter(name=students[0].pin)
			if len(devices) == 0 and register_id != "":
				try:
					new_device = FCMDevice(name=students[0].pin, user=None, device_id=int(device_id, 16), registration_id=register_id)
				except:
					new_device = FCMDevice(name=students[0].pin, user=None, device_id="", registration_id=register_id)
				new_device.save()
			return Response({"registered": True})
		else:
			return Response({"registered": False})

	#@action(permission_classes=[])
	#@detail_route(methods=['post'])
	@action(detail=False, methods=['get'])
	def get_payments(self, request, pk=None):
		pin = request.POST["pin"]
		if "|" in pin:
			pin_list = pin.split("|")
			payment_list = Payment.objects.filter(student__pin__in=pin_list).order_by('-pay_date')
		else:
			payment_list = Payment.objects.filter(student__pin=pin).order_by('-pay_date')
		serializer = PaymentSerializer(payment_list, many=True)
		return Response({"payments" : serializer.data})

class AssistancesViewSet(viewsets.ViewSet):
	queryset = Assistance.objects.all()
	serializer_class = AssistanceSerializer
	model = Assistance

	def list(self, request):
		assistances = Assistance.objects.all()
		serializer = AssistanceSerializer(assistances, many=True)
		return Response(serializer.data)

	#@detail_route(methods=['post'])
	@action(detail=False, methods=['get'])
	def get_assistances(self, request, pk=None):
		pin = request.POST["pin"]
		if "|" in pin:
			pin_list = pin.split("|")
			enrolment_list = Enrolment.objects.filter(student__pin__in=pin_list, active = True)
		else:
			enrolment_list = Enrolment.objects.filter(student__pin=pin, active = True)
		ini_date = date.today() - relativedelta(months=3)
		end_date = date.today()

		result = []
		for enrolment in enrolment_list:
			assistance_list = Assistance.objects.filter(enrolments__in = [enrolment], date__range = (ini_date, end_date)).order_by('-date')
			for assistance in assistance_list:
				group = assistance.group.get_full_name()
				result.append({'date': assistance.date, 'group': group, 'student': enrolment.student.name})
		return Response({"assistances": result})

class NotificationsViewSet(viewsets.ViewSet):
	queryset = Notification.objects.all()
	serializer_class = NotificationSerializer
	model = Notification

	def list(self, request):
		notifications = Notification.objects.all()
		serializer = NotificationSerializer(notifications, many=True)
		return Response(serializer.data)

	#@detail_route(methods=['post'])
	@action(detail=False, methods=['get'])
	def get_notifications(self, request, pk=None):
		pin = request.POST["pin"]
		if "|" in pin:
			pin_list = pin.split("|")
			student_list = Student.objects.filter(pin__in=pin_list)
		else:
			student_list = Student.objects.filter(pin=pin)
		ini_date = date.today() - relativedelta(months=3)
		end_date = date.today()

		result = []
		for student in student_list:
			notification_list = Notification.objects.filter(students__in = [student], date__range = (ini_date, end_date)).order_by('-date')
			for notification in notification_list:
				result.append({'date': notification.date, 'msg': notification.msg, 'student': student.name})
		return Response({"notifications": result})


