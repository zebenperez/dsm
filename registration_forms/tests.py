from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, TestCase

from registration_forms.admin import FormAdmin
from registration_forms.models import Form, FormAnswer, FormQuestion, FormSubmission
from studio.models import Student


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
