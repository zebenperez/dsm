from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from kiosk.models import KioskPayment, KioskProduct, KioskTicket
from studio.models import Student, WalletMovement


class KioskTicketTests(TestCase):
    def setUp(self):
        self.worker = User.objects.create_user(username='kiosk-worker', password='secret')
        self.product = KioskProduct.objects.create(name='Agua', price=Decimal('1.50'))

    def test_cash_ticket_uses_the_product_price_snapshot(self):
        ticket = KioskTicket.create_from_cart(
            self.worker, {str(self.product.id): 2}, KioskPayment.METHOD_CASH,
        )

        self.assertEqual(ticket.total, Decimal('3.00'))
        self.assertEqual(ticket.lines.get().product_name, 'Agua')
        self.assertEqual(ticket.payments.get().method, KioskPayment.METHOD_CASH)

    def test_wallet_ticket_creates_a_matching_wallet_charge(self):
        student = Student.objects.create(code=100, pin='K100', name='Alumna', phone='', band='KIOSK-NFC')
        WalletMovement.record(student, Decimal('5.00'), WalletMovement.TYPE_TOP_UP, 'Recarga')

        ticket = KioskTicket.create_from_cart(
            self.worker, {str(self.product.id): 1}, KioskPayment.METHOD_WALLET, 'KIOSK-NFC',
        )

        self.assertEqual(ticket.payments.get().wallet_movement.amount, Decimal('-1.50'))
        student.refresh_from_db()
        self.assertEqual(student.wallet_balance, Decimal('3.50'))
