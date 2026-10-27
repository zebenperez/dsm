from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from champs.models import BankTransaction, Championship, FederationLicencePayment, Registration
from champs.views import get_champ_list_context, suggested_licence_student, suggested_registration
from studio.models import Student


class ChampionshipPublicationListTests(TestCase):
    def setUp(self):
        self.published = Championship.objects.create(name='Campeonato publicado', publish=True)
        self.unpublished = Championship.objects.create(name='Campeonato sin publicar', publish=False)

    def test_context_can_filter_published_championships(self):
        context = get_champ_list_context('true')

        self.assertEqual(context['publish_filter'], 'true')
        self.assertEqual([champ.id for champ in context['champ_list']], [self.published.id])

    def test_context_can_filter_unpublished_championships(self):
        context = get_champ_list_context('false')

        self.assertEqual(context['publish_filter'], 'false')
        self.assertEqual([champ.id for champ in context['champ_list']], [self.unpublished.id])


class BankReconciliationDiscardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='reception', password='secret')
        reception, _ = Group.objects.get_or_create(name='reception')
        self.user.groups.add(reception)
        self.transaction = BankTransaction.objects.create(
            external_id='OTHER-PAYMENT-1', booking_date=date.today(), amount='25.00',
            payer='Otro cliente', reference='Pago no relacionado',
        )
        self.client.force_login(self.user)

    def test_unrelated_bank_transaction_can_be_discarded(self):
        response = self.client.post(reverse('discard-bank-transaction', args=[self.transaction.id]))

        self.assertRedirects(response, reverse('bank-reconciliation'))
        self.transaction.refresh_from_db()
        self.assertIsNotNone(self.transaction.discarded_at)
        self.assertEqual(self.transaction.discarded_by, self.user)

        response = self.client.get(reverse('bank-reconciliation'))
        self.assertNotContains(response, self.transaction.reference)

    def test_discarded_transaction_cannot_be_allocated(self):
        self.transaction.discarded_at = timezone.now()
        self.transaction.save(update_fields=['discarded_at'])

        response = self.client.post(reverse('confirm-bank-allocation', args=[self.transaction.id]))

        self.assertRedirects(response, reverse('bank-reconciliation'))


class BankReferenceSuggestionTests(TestCase):
    def setUp(self):
        student = Student.objects.create(code=901, pin='R901', name='Referencia', phone='')
        championship = Championship.objects.create(name='Campeonato de referencia')
        self.registration = Registration.objects.create(student=student, champ=championship)

    def test_finds_reference_surrounded_by_other_text_with_spaces(self):
        reference_with_spaces = self.registration.payment_reference.replace('-', ' ')

        suggested = suggested_registration('Pago de Marta %s muchas gracias' % reference_with_spaces)

        self.assertEqual(suggested, self.registration)


class FederationLicenceReconciliationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin-licences', password='secret')
        admins, _ = Group.objects.get_or_create(name='admins')
        self.user.groups.add(admins)
        self.student = Student.objects.create(code=902, pin='L902', name='Licencia anual', phone='')
        self.transaction = BankTransaction.objects.create(
            external_id='LICENCE-2026-902', booking_date=date.today(), amount='50.00',
            payer='Licencia anual', reference='LIC %s %s' % (date.today().year, self.student.code),
        )
        self.client.force_login(self.user)

    def test_annual_licence_can_be_reconciled_for_fifty_euros(self):
        response = self.client.post(reverse('confirm-bank-allocation', args=[self.transaction.id]), {
            'target': 'licence:%s' % self.student.id,
            'amount': '50.00',
        })

        self.assertRedirects(response, reverse('bank-reconciliation'))
        licence_payment = FederationLicencePayment.objects.get(student=self.student, year=date.today().year)
        self.assertEqual(licence_payment.amount, Decimal('50.00'))
        self.assertEqual(licence_payment.bank_transaction, self.transaction)

    def test_suggests_licence_student_from_annual_reference(self):
        suggested = suggested_licence_student(
            'Pago LIC %s %s realizado' % (date.today().year, self.student.code),
            date.today().year,
        )

        self.assertEqual(suggested, self.student)

    def test_suggests_licence_from_federation_concept_ignoring_case_and_accents(self):
        self.student.name = 'Irina Caballero Cabello'
        self.student.save(update_fields=['name'])

        suggested = suggested_licence_student(
            'TRANSFERENCIA: fEdErAcIóN Irina Caballero Cabello',
            date.today().year,
        )

        self.assertEqual(suggested, self.student)
