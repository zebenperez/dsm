"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from decimal import Decimal
from datetime import date

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from studio.models import (
    Article, ArticlePayment, Assistance, Concept, Enrolment, Group as StudioGroup,
    InsufficientWalletBalance, Payment, Student, Teacher, WalletMovement,
)
from studio.views import calculate_amount, calculate_cash_summary, calculate_wallet_payments


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
