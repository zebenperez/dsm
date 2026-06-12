from django.contrib.auth.models import User, Group
from django.shortcuts import render, redirect
from django.utils.translation import ugettext as _
from django.utils import timezone

from studio.models import Student, Payment, Assistance, Enrolment


def check_pin(request):
	return ("pin" in request.session and request.session["pin"] != "")

def login(request):
	return render (request,'pwa/login.html',{})

def logout(request):
	request.session["pin"] = ""
	return redirect(login)

def set_pin(request):
	try:
		pin = request.POST["pin"]
		student = Student.objects.filter(pin=pin).first()
		if student == None:
			return render (request,'pwa/login.html',{'err': 'Pin no encontrado!'})
		request.session["pin"] = pin
		return redirect(payments)
	except Exception as e:
		return render (request,'pwa/login.html',{"err": e})

def index(request):
	if not check_pin(request):
		return redirect(login)
	student = Student.objects.filter(pin=request.session["pin"]).first()
	if student.licence == "":
		return redirect(payments)
	return render (request,'pwa/index.html',{"student": student})

def payments(request):
	if not check_pin(request):
		return redirect(login)
	student = Student.objects.filter(pin=request.session["pin"]).first()
	payment_list = Payment.objects.filter(student=student, date__year=timezone.now().year)
	return render (request,'pwa/payments.html',{'student': student, 'payment_list': payment_list})

def assistances(request):
	if not check_pin(request):
		return redirect(login)
	student = Student.objects.filter(pin=request.session["pin"]).first()
	enrolment_list = Enrolment.objects.filter(student=student, active=True)
	assistance_list = Assistance.objects.filter(enrolments__in=enrolment_list, date__year=timezone.now().year).order_by('-date')
	return render (request,'pwa/assistances.html',{'student': student, 'assistance_list': assistance_list})

def change_photo(request):
	if not check_pin(request):
		return redirect(login)
	if request.POST:
		student = Student.objects.get(pk=request.POST["student"])
		#print(request.FILES["photo"])
		student.picture = request.FILES["photo"]
		student.save()
	return redirect(index)


