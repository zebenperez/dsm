"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from datetime import time

from django.test import TestCase
from django.urls import reverse

from registration_forms.models import Form
from studio.models import Enrolment, Group, Student, Teacher


class RegistrationFormVisibilityTests(TestCase):
    def setUp(self):
        teacher = Teacher.objects.create(code=1, name='Profesora', phone='')
        self.target_group = Group.objects.create(
            name='Grupo objetivo', teacher=teacher, ini_time=time(17), end_time=time(18),
        )
        other_group = Group.objects.create(
            name='Otro grupo', teacher=teacher, ini_time=time(18), end_time=time(19),
        )
        self.target_student = Student.objects.create(code=1, pin='A001', name='Alumna objetivo', phone='')
        self.other_student = Student.objects.create(code=2, pin='A002', name='Otra alumna', phone='')
        Enrolment.objects.create(student=self.target_student, group=self.target_group)
        Enrolment.objects.create(student=self.other_student, group=other_group)

        self.general_form = Form.objects.create(title='Para todas', is_published=True)
        self.targeted_form = Form.objects.create(title='Solo grupo objetivo', is_published=True)
        self.targeted_form.target_groups.add(self.target_group)

    def test_targeted_forms_are_only_visible_to_students_in_a_recipient_group(self):
        self.assertQuerySetEqual(
            Form.objects.for_student(self.target_student).order_by('id'),
            [self.general_form, self.targeted_form],
        )
        self.assertQuerySetEqual(
            Form.objects.for_student(self.other_student).order_by('id'),
            [self.general_form],
        )

    def test_targeted_form_cannot_be_opened_by_an_unrelated_student(self):
        session = self.client.session
        session['pin'] = self.other_student.pin
        session.save()

        response = self.client.get(reverse('pwa-form-detail', args=[self.targeted_form.id]))

        self.assertEqual(response.status_code, 404)
