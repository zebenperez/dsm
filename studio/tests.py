"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from decimal import Decimal
from datetime import date, timedelta

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from studio.models import (
    Article, ArticlePayment, Assistance, Concept, Enrolment, Group as StudioGroup,
    InsufficientWalletBalance, Payment, Student, Teacher, WalletMovement,
)
from studio.views import calculate_amount, calculate_cash_summary, calculate_wallet_payments


class AdminOperationalAccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin', password='secret')
        admins, _ = Group.objects.get_or_create(name='admins')
        self.user.groups.add(admins)
        self.client.force_login(self.user)

    def test_admin_group_sees_and_can_open_operational_section(self):
        response = self.client.get(reverse('tpv'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TPV')
        self.assertContains(response, 'Pulseras')
        self.assertContains(response, 'Monedero')
        self.assertContains(response, 'Caja')

        response = self.client.get(reverse('wallet'))

        self.assertEqual(response.status_code, 200)

    def test_admin_group_can_access_registration_forms(self):
        response = self.client.get(reverse('registration_forms'))

        self.assertEqual(response.status_code, 200)

    def test_admin_group_can_access_wallet_payment_endpoints(self):
        response = self.client.post(reverse('pay_with_wallet'))

        self.assertIn('/studio/tpv/', response['Location'])

        response = self.client.post(reverse('article_pay_with_wallet'))

        self.assertIn('/studio/tpv/', response['Location'])

    def test_logout_ends_the_session(self):
        response = self.client.post(reverse('logout'))

        self.assertRedirects(response, '/studio/')
        self.assertNotIn('_auth_user_id', self.client.session)


class StudentManagementTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin', password='secret')
        admins, _ = Group.objects.get_or_create(name='admins')
        self.user.groups.add(admins)
        self.teacher = Teacher.objects.create(code=1, name='Profesora', phone='')
        self.group = StudioGroup.objects.create(
            name='Bachata', teacher=self.teacher, ini_time='18:00', end_time='19:00', monday=True,
        )
        self.client.force_login(self.user)

    def test_admin_can_create_student_and_manage_an_enrolment(self):
        response = self.client.post(reverse('student-create'), {
            'code': 100, 'name': 'Alumno de prueba', 'pin': 'A100', 'phone': '600000000',
            'born_date': '', 'licence': '', 'email': '', 'band': '',
        })

        student = Student.objects.get(code=100)
        self.assertRedirects(response, reverse('student-update', args=[student.id]))

        response = self.client.post(reverse('enrolment-create', args=[student.id]), {
            'group': self.group.id, 'price': '30.00', 'percent_studio': 50,
            'percent_teacher': 50, 'active': 'on',
        })

        self.assertRedirects(response, reverse('student-update', args=[student.id]))
        enrolment = Enrolment.objects.get(student=student, group=self.group)
        self.assertTrue(enrolment.active)

        response = self.client.post(reverse('enrolment-update', args=[student.id, enrolment.id]), {
            'group': self.group.id, 'price': '30.00', 'percent_studio': 50,
            'percent_teacher': 50,
        })

        self.assertRedirects(response, reverse('student-update', args=[student.id]))
        enrolment.refresh_from_db()
        self.assertFalse(enrolment.active)

    def test_students_can_be_filtered_by_active_group(self):
        other_group = StudioGroup.objects.create(
            name='Salsa', teacher=self.teacher, ini_time='19:00', end_time='20:00', tuesday=True,
        )
        bachata_student = Student.objects.create(code=101, pin='A101', name='Alumna Bachata', phone='')
        salsa_student = Student.objects.create(code=102, pin='A102', name='Alumno Salsa', phone='')
        inactive_student = Student.objects.create(code=103, pin='A103', name='Matrícula inactiva', phone='')
        Enrolment.objects.create(student=bachata_student, group=self.group, active=True)
        Enrolment.objects.create(student=salsa_student, group=other_group, active=True)
        Enrolment.objects.create(student=inactive_student, group=self.group, active=False)

        response = self.client.get(reverse('students'), {'group': self.group.id})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alumna Bachata')
        self.assertNotContains(response, 'Alumno Salsa')
        self.assertNotContains(response, 'Matrícula inactiva')
        self.assertEqual(response.context['student_count'], 1)

    def test_students_can_be_filtered_by_licence_status(self):
        licensed_student = Student.objects.create(
            code=104, pin='A104', name='Alumna con licencia', phone='', licence='LIC-104',
        )
        unlicensed_student = Student.objects.create(
            code=105, pin='A105', name='Alumna sin licencia', phone='', licence='',
        )
        Enrolment.objects.create(student=licensed_student, group=self.group, active=True)
        Enrolment.objects.create(student=unlicensed_student, group=self.group, active=True)

        response = self.client.get(reverse('students'), {'licence': 'with_licence'})

        self.assertContains(response, 'Alumna con licencia')
        self.assertNotContains(response, 'Alumna sin licencia')
        self.assertEqual(response.context['student_count'], 1)

        response = self.client.get(reverse('students'), {'licence': 'without_licence'})

        self.assertNotContains(response, 'Alumna con licencia')
        self.assertContains(response, 'Alumna sin licencia')
        self.assertEqual(response.context['student_count'], 1)

    def test_students_list_shows_birth_date_and_current_age(self):
        student = Student.objects.create(
            code=109, pin='A109', name='Alumna con fecha', phone='', born_date=date(2000, 1, 1),
        )
        Enrolment.objects.create(student=student, group=self.group, active=True)

        response = self.client.get(reverse('students'))

        self.assertContains(response, 'Fecha de nacimiento')
        self.assertContains(response, '01/01/2000 (%s años)' % (date.today().year - 2000))

    def test_admin_can_review_and_edit_federation_data(self):
        student = Student.objects.create(
            code=108, pin='A108', name='Alumna federada', phone='600000108',
        )
        image = (
            b'GIF87a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04'
            b'\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        )

        response = self.client.post(reverse('student-update', args=[student.id]), {
            'code': student.code,
            'name': student.name,
            'pin': student.pin,
            'born_date': '18-05-2000',
            'phone': student.phone,
            'licence': 'LIC-108',
            'email': 'alumna@example.com',
            'band': '',
            'dni': '12345678Z',
            'dni_expiry_date': '18-05-2030',
            'sex': 'Femenino',
            'nationality': 'Española',
            'address': 'Calle Ejemplo, 1',
            'postal_code': '38001',
            'municipality': 'Santa Cruz de Tenerife',
            'province': 'Santa Cruz de Tenerife',
            'autonomous_community': 'Canarias',
            'dni_front': SimpleUploadedFile('anverso.gif', image, content_type='image/gif'),
            'dni_back': SimpleUploadedFile('reverso.gif', image, content_type='image/gif'),
        })

        self.assertRedirects(response, reverse('student-update', args=[student.id]))
        student.refresh_from_db()
        self.assertEqual(student.dni, '12345678Z')
        self.assertEqual(student.dni_expiry_date, date(2030, 5, 18))
        self.assertEqual(student.sex, 'Femenino')
        self.assertEqual(student.province, 'Santa Cruz de Tenerife')
        self.assertTrue(student.dni_front.name)
        self.assertTrue(student.dni_back.name)

    def test_attendance_follow_up_excludes_students_with_attendance_and_marks_overdue_payments(self):
        inactive_student = Student.objects.create(code=106, pin='A106', name='Sin asistencia', phone='600000106')
        attended_student = Student.objects.create(code=107, pin='A107', name='Con asistencia', phone='600000107')
        inactive_enrolment = Enrolment.objects.create(student=inactive_student, group=self.group, active=True)
        attended_enrolment = Enrolment.objects.create(student=attended_student, group=self.group, active=True)
        Assistance.objects.create(date=date.today(), group=self.group).enrolments.add(attended_enrolment)
        Payment.objects.create(
            student=inactive_student, enrolment=inactive_enrolment, amount=Decimal('30.00'), note='',
            date=date.today(), pay_date=date.today(), expire_date=date.today() - timedelta(days=1),
        )

        response = self.client.get(reverse('attendance-follow-up'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sin asistencia')
        self.assertNotContains(response, 'Con asistencia')
        self.assertContains(response, 'Pago vencido')
        self.assertEqual(response.context['overdue_count'], 1)


class WalletMovementTests(TestCase):
    def setUp(self):
        self.student = Student.objects.create(
            code=1, pin='W001', name='Alumna de prueba', phone='', band='NFC-001',
        )

    def test_a_charge_cannot_make_the_wallet_balance_negative(self):
        WalletMovement.record(
            self.student, Decimal('20.00'), WalletMovement.TYPE_TOP_UP,
            'Recarga inicial', WalletMovement.METHOD_CASH,
        )
        WalletMovement.record(
            self.student, Decimal('-7.50'), WalletMovement.TYPE_PURCHASE,
            'Camiseta',
        )

        self.student.refresh_from_db()
        self.assertEqual(self.student.wallet_balance, Decimal('12.50'))

        with self.assertRaises(InsufficientWalletBalance):
            WalletMovement.record(
                self.student, Decimal('-13.00'), WalletMovement.TYPE_PURCHASE,
                'Pago no permitido',
            )

        self.assertEqual(WalletMovement.objects.filter(student=self.student).count(), 2)

    def test_daily_close_does_not_count_wallet_spending_as_a_second_card_charge(self):
        """A €100 card top-up followed by a €40 wallet payment leaves €60 in wallet."""
        WalletMovement.record(
            self.student, Decimal('100.00'), WalletMovement.TYPE_TOP_UP,
            'Recarga con tarjeta', WalletMovement.METHOD_CARD,
        )
        WalletMovement.record(
            self.student, Decimal('-40.00'), WalletMovement.TYPE_PURCHASE,
            'Matrícula',
        )

        summary = calculate_cash_summary(date.today())

        self.assertEqual(summary['card_collected'], Decimal('100.00'))
        self.assertEqual(summary['cash_collected'], Decimal('0.00'))
        self.assertEqual(summary['wallet_spent'], Decimal('40.00'))
        self.assertEqual(summary['wallet_net_change'], Decimal('60.00'))


class DashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='manager', password='secret')
        managers, _ = Group.objects.get_or_create(name='managers')
        self.user.groups.add(managers)
        self.teacher = Teacher.objects.create(code=10, name='Profesora', phone='')
        self.dance_group = StudioGroup.objects.create(
            name='Bachata iniciación', teacher=self.teacher,
            ini_time='18:00', end_time='19:00', monday=True,
        )
        self.student = Student.objects.create(code=10, pin='D010', name='Alumna activa', phone='')
        self.enrolment = Enrolment.objects.create(student=self.student, group=self.dance_group)

    def test_dashboard_shows_existing_operational_data(self):
        Payment.objects.create(
            student=self.student, enrolment=self.enrolment,
            amount=Decimal('30.00'), note='', date=date.today(),
            pay_date=date.today(), expire_date=date.today(),
        )
        assistance = Assistance.objects.create(date=date.today(), group=self.dance_group)
        assistance.enrolments.add(self.enrolment)
        self.client.force_login(self.user)

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Estado de la escuela')
        self.assertEqual(response.context['active_students_count'], 1)
        self.assertEqual(response.context['total_income'], Decimal('30.00'))
        self.assertEqual(response.context['attendance_rate'], 100)

    def test_dashboard_payment_trend_counts_each_paying_student_once_per_month(self):
        Payment.objects.create(
            student=self.student, enrolment=self.enrolment,
            amount=Decimal('30.00'), note='', date=date.today(),
            pay_date=date.today(), expire_date=date.today(),
        )
        Payment.objects.create(
            student=self.student, enrolment=self.enrolment,
            amount=Decimal('15.00'), note='', date=date.today(),
            pay_date=date.today() + timedelta(days=1), expire_date=date.today(),
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse('dashboard'))

        trend = response.context['payment_trend']
        current_year = next(series for series in trend['years'] if series['year'] == date.today().year)
        month_index = date.today().month - 1
        self.assertEqual(current_year['students'][month_index], 1)
        self.assertEqual(current_year['income'][month_index], 45.0)

    def test_dashboard_requires_manager_access(self):
        outsider = User.objects.create_user(username='outsider', password='secret')
        self.client.force_login(outsider)

        response = self.client.get(reverse('dashboard'))

        self.assertRedirects(response, reverse('auth_login'))


class ArticleWalletPaymentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='reception', password='secret')
        reception, _ = Group.objects.get_or_create(name='reception')
        self.user.groups.add(reception)
        self.student = Student.objects.create(code=2, pin='W002', name='Alumno de prueba', phone='', band='LLAVERO-002')
        WalletMovement.record(self.student, Decimal('20.00'), WalletMovement.TYPE_TOP_UP, 'Recarga')
        self.article = Article.objects.create(
            code='CAM-1', name='Camiseta', cost=Decimal('5.00'),
            pvp=Decimal('12.00'), stock=3,
        )
        self.concept = Concept.objects.create(code='art', name='Artículos')

    def test_article_can_be_paid_from_wallet(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('article_pay_with_wallet'), {
            'article_id': self.article.id,
            'band': self.student.band,
            'amount': '12,00',
            'concept': self.concept.code,
            'note': 'Talla M',
        })

        self.assertEqual(response.status_code, 302)
        self.assertIn('t=article', response['Location'])
        self.assertIn('wallet_message_level=success', response['Location'])
        sale = ArticlePayment.objects.get()
        self.assertEqual(sale.student, self.student)
        self.assertEqual(sale.wallet_movement.amount, Decimal('-12.00'))
        self.article.refresh_from_db()
        self.student.refresh_from_db()
        self.assertEqual(self.article.stock, 2)
        self.assertEqual(self.student.wallet_balance, Decimal('8.00'))
        self.assertEqual(calculate_amount(date.today(), True), Decimal('0.00'))
        self.assertEqual(calculate_wallet_payments(date.today()), Decimal('12.00'))

    def test_deleting_a_wallet_paid_tuition_returns_the_balance(self):
        teacher = Teacher.objects.create(code=20, name='Profesora de prueba', phone='')
        dance_group = StudioGroup.objects.create(
            name='Salsa', teacher=teacher, ini_time='18:00', end_time='19:00', monday=True,
        )
        enrolment = Enrolment.objects.create(student=self.student, group=dance_group, price=Decimal('15.00'))
        wallet_charge = WalletMovement.record(
            self.student, Decimal('-15.00'), WalletMovement.TYPE_PURCHASE, 'Cuota: Salsa',
        )
        payment = Payment.objects.create(
            student=self.student, enrolment=enrolment, amount=Decimal('15.00'), note='',
            date=date.today(), pay_date=date.today(), expire_date=date.today(),
            wallet_movement=wallet_charge,
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse('delete_payment', args=[payment.id]))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Payment.objects.filter(pk=payment.id).exists())
        self.student.refresh_from_db()
        self.assertEqual(self.student.wallet_balance, Decimal('20.00'))
        refund = WalletMovement.objects.latest('id')
        self.assertEqual(refund.movement_type, WalletMovement.TYPE_REFUND)
        self.assertEqual(refund.amount, Decimal('15.00'))

    def test_article_wallet_payment_does_not_sell_with_insufficient_balance(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('article_pay_with_wallet'), {
            'article_id': self.article.id,
            'band': self.student.band,
            'amount': '25.00',
            'concept': self.concept.code,
        })

        self.assertEqual(response.status_code, 302)
        self.assertFalse(ArticlePayment.objects.exists())
        self.article.refresh_from_db()
        self.assertEqual(self.article.stock, 3)

    def test_article_wallet_payment_creates_the_default_concept_when_missing(self):
        self.client.force_login(self.user)
        self.concept.delete()

        response = self.client.post(reverse('article_pay_with_wallet'), {
            'article_id': self.article.id,
            'band': self.student.band,
            'amount': '12.00',
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(ArticlePayment.objects.get().concept.code, 'art')

    def test_article_uses_the_promotional_price_when_its_promotion_is_active(self):
        self.article.is_promo = True
        self.article.promo_price = Decimal('9.50')
        self.article.save()

        self.assertEqual(self.article.sale_price, Decimal('9.50'))
