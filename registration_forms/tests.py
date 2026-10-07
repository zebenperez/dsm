from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, TestCase
from django.urls import reverse

from registration_forms.admin import FormAdmin
from registration_forms.models import Form, FormAnswer, FormQuestion, FormSubmission
from studio.models import Enrolment, Group, Student, Teacher


class FormAdminCloneTests(TestCase):
    def setUp(self):
        self.form = Form.objects.create(
            title='Pedido de camiseta', description='Elige talla', is_published=True,
            allow_response_changes=True,
        )
        self.question = FormQuestion.objects.create(
            form=self.form,
            text='Talla',
            answer_type=FormQuestion.ANSWER_TYPE_SELECT,
            options='S\nM\nL',
            required=True,
            position=2,
        )
        student = Student.objects.create(code=99, pin='A099', name='Alumna', phone='')
        submission = FormSubmission.objects.create(form=self.form, student=student)
        FormAnswer.objects.create(submission=submission, question=self.question, short_text='M')

    def test_admin_action_clones_configuration_and_questions_without_responses(self):
        request = RequestFactory().post('/admin/registration_forms/form/')
        request.user = User.objects.create_superuser('admin', 'admin@example.com', 'secret')
        request.session = {}
        request._messages = FallbackStorage(request)
        admin_view = FormAdmin(Form, AdminSite())

        admin_view.clone_selected_forms(request, Form.objects.filter(pk=self.form.pk))

        clone = Form.objects.exclude(pk=self.form.pk).get()
        self.assertEqual(clone.title, 'Copia de Pedido de camiseta')
        self.assertEqual(clone.description, self.form.description)
        self.assertFalse(clone.is_published)
        self.assertTrue(clone.allow_response_changes)
        self.assertFalse(FormSubmission.objects.filter(form=clone).exists())
        clone_question = clone.questions.get()
        self.assertEqual(clone_question.text, self.question.text)
        self.assertEqual(clone_question.answer_type, FormQuestion.ANSWER_TYPE_SELECT)
        self.assertEqual(clone_question.options, 'S\nM\nL')
        self.assertEqual(clone_question.position, 2)


class FormResponsePendingStudentsTests(TestCase):
    def setUp(self):
        teacher = Teacher.objects.create(code=1, name='Profesora', phone='')
        self.target_group = Group.objects.create(
            name='Grupo destinatario', teacher=teacher, ini_time='17:00', end_time='18:00',
        )
        other_group = Group.objects.create(
            name='Otro grupo', teacher=teacher, ini_time='18:00', end_time='19:00',
        )
        self.responded_student = Student.objects.create(code=1, pin='A001', name='Respondida', phone='')
        self.pending_student = Student.objects.create(code=2, pin='A002', name='Pendiente', phone='')
        other_student = Student.objects.create(code=3, pin='A003', name='Otro grupo', phone='')
        inactive_student = Student.objects.create(code=4, pin='A004', name='Matrícula inactiva', phone='')
        Enrolment.objects.create(student=self.responded_student, group=self.target_group, active=True)
        Enrolment.objects.create(student=self.pending_student, group=self.target_group, active=True)
        Enrolment.objects.create(student=other_student, group=other_group, active=True)
        Enrolment.objects.create(student=inactive_student, group=self.target_group, active=False)

        self.targeted_form = Form.objects.create(title='Formulario dirigido')
        self.targeted_form.target_groups.add(self.target_group)
        FormSubmission.objects.create(form=self.targeted_form, student=self.responded_student)
        self.general_form = Form.objects.create(title='Formulario general')

        user = User.objects.create_user('reception', password='secret')
        user.groups.add(AuthGroup.objects.create(name='reception'))
        self.client.force_login(user)

    def test_shows_only_active_target_group_students_who_have_not_responded(self):
        response = self.client.get(reverse('registration_form_responses', args=[self.targeted_form.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pendientes de responder')
        self.assertContains(response, self.pending_student.name)
        self.assertNotContains(response, 'Matrícula inactiva')
        self.assertNotContains(response, 'Otro grupo')

    def test_does_not_show_pending_section_for_a_general_form(self):
        response = self.client.get(reverse('registration_form_responses', args=[self.general_form.id]))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Pendientes de responder')

    def test_numbers_responses_and_shows_target_groups_for_multi_group_form(self):
        second_group = Group.objects.create(
            name='Segundo grupo', teacher=self.target_group.teacher,
            ini_time='19:00', end_time='20:00',
        )
        self.targeted_form.target_groups.add(second_group)
        Enrolment.objects.create(
            student=self.responded_student, group=second_group, active=True,
        )

        response = self.client.get(
            reverse('registration_form_responses', args=[self.targeted_form.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<th>Grupo</th>', html=True)
        self.assertContains(response, '<td>1</td>', html=True)
        self.assertContains(response, 'Grupo destinatario, Segundo grupo')

    def test_does_not_show_group_column_for_single_group_form(self):
        response = self.client.get(
            reverse('registration_form_responses', args=[self.targeted_form.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<th>Grupo</th>', html=True)

    def test_shows_group_column_for_general_form(self):
        FormSubmission.objects.create(
            form=self.general_form, student=self.responded_student,
        )

        response = self.client.get(
            reverse('registration_form_responses', args=[self.general_form.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<th>Grupo</th>', html=True)
        self.assertContains(response, self.target_group.name)
