"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from decimal import Decimal

from django.test import TestCase

from studio.models import InsufficientWalletBalance, Student, WalletMovement


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
