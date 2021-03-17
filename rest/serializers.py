from django.contrib.auth.models import User
from rest_framework import serializers
from studio.models import *

class AssistanceSerializer(serializers.ModelSerializer):
	group = serializers.CharField()

	class Meta:
		model = Assistance
		fields = ('date', 'group')

class EnrolmentSerializer(serializers.ModelSerializer):
	class Meta:
		model = Enrolment

class NotificationSerializer(serializers.ModelSerializer):
	class Meta:
		model = Notification
		fields = ('date', 'msg')

class StudentSerializer(serializers.ModelSerializer):
	class Meta:
		model = Student
		fields = ('name',)

class PaymentSerializer(serializers.ModelSerializer):
	#pk = serializers.Field()
	date=serializers.DateTimeField(format="%d-%m-%Y")
	pay_date=serializers.DateTimeField(format="%d-%m-%Y")
	expire_date=serializers.DateTimeField(format="%d-%m-%Y")
	#enrolment = serializers.RelatedField(read_only = True)
	#enrolment = EnrolmentSerializer()
	enrolment = serializers.CharField()
	#student = serializers.RelatedField(source='student')
	#student = StudentSerializer()
	student = serializers.CharField()

	class Meta:
		model = Payment
		fields = ('amount', 'date', 'pay_date', 'expire_date', 'student', 'enrolment')
