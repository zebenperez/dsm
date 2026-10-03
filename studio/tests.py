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

from studio.models import Article, ArticlePayment, Concept, InsufficientWalletBalance, Student, WalletMovement
from studio.views import calculate_amount, calculate_wallet_payments


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
