import csv
from datetime import date
from decimal import Decimal
from io import StringIO

from django.contrib.auth.models import Group, User
from django.db.models import Sum
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from champs.models import BankTransaction, Category, Championship, FederationLicencePayment, PaymentAllocation, Registration, TravelCompanion
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


class ChampionshipTravelersExportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='travel-admin', password='secret')
        admins, _ = Group.objects.get_or_create(name='admins')
        self.user.groups.add(admins)
        self.client.force_login(self.user)
        self.championship = Championship.objects.create(name='Viaje nacional')
        self.category = Category.objects.create(name='Dúo juvenil')
        self.student = Student.objects.create(
            code=903, pin='V903', name='María Pérez García', phone='', municipality='La Laguna',
            dni='12345678A', born_date=date(2010, 4, 3),
        )
        self.registration = Registration.objects.create(student=self.student, champ=self.championship)
        self.registration.categories.add(self.category)
        TravelCompanion.objects.create(
            registration=self.registration, full_name='Ana Pérez García', municipality='La Laguna',
            dni='87654321B', birth_date=date(1980, 2, 1),
        )

    def test_export_contains_competitors_and_companions(self):
        response = self.client.get(reverse('champs-export-travelers', args=[self.championship.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        rows = list(csv.reader(StringIO(response.content.decode('utf-8-sig'))))
        self.assertEqual(rows[0], [
            'Tipo', 'Nombre y apellidos', 'Municipio', 'Número de DNI',
            'Fecha de nacimiento', 'Categoría', 'Competidora a la que acompaña',
        ])
        self.assertIn(
            ['Competidora', 'María Pérez García', 'La Laguna', '12345678A', '03/04/2010', 'Dúo juvenil', ''],
            rows,
        )
        self.assertIn(
            ['Acompañante', 'Ana Pérez García', 'La Laguna', '87654321B', '01/02/1980', 'Dúo juvenil', 'María Pérez García'],
            rows,
        )


class ChampionshipPaymentEditingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='payment-admin', password='secret')
        admins, _ = Group.objects.get_or_create(name='admins')
        self.user.groups.add(admins)
        self.client.force_login(self.user)
        self.championship = Championship.objects.create(name='Campeonato de pagos')
        self.student = Student.objects.create(code=904, pin='P904', name='Pago editable', phone='')
        self.registration = Registration.objects.create(
            student=self.student, champ=self.championship, paid_amount='15.00',
        )
        self.companion = TravelCompanion.objects.create(
            registration=self.registration, full_name='Acompañante editable',
            birth_date=date(1980, 1, 1), dni='12345678Z', paid_amount='10.00',
        )

    def test_admin_can_edit_registration_and_companion_paid_totals(self):
        response = self.client.get(reverse('edit-champ-registration-payment'), {
            'champ_id': self.championship.id, 'registration_id': self.registration.id, 'amount': '30.00',
        })

        self.assertEqual(response.status_code, 200)
        self.registration.refresh_from_db()
        self.assertEqual(self.registration.paid_amount, Decimal('30.00'))

        response = self.client.get(reverse('edit-champ-companion-payment'), {
            'champ_id': self.championship.id, 'companion_id': self.companion.id, 'amount': '25.00',
        })

        self.assertEqual(response.status_code, 200)
        self.companion.refresh_from_db()
        self.assertEqual(self.companion.paid_amount, Decimal('25.00'))

    def test_standard_post_payment_forms_update_totals_and_redirect(self):
        response = self.client.post(reverse('edit-champ-registration-payment'), {
            'champ_id': self.championship.id, 'registration_id': self.registration.id, 'amount': '22.00',
        })

        self.assertRedirects(response, reverse('champs-details', args=[self.championship.id]))
        self.registration.refresh_from_db()
        self.assertEqual(self.registration.paid_amount, Decimal('22.00'))

        response = self.client.post(reverse('edit-champ-companion-payment'), {
            'champ_id': self.championship.id, 'companion_id': self.companion.id, 'amount': '18.00',
        })

        self.assertRedirects(response, reverse('champs-details', args=[self.championship.id]))
        self.companion.refresh_from_db()
        self.assertEqual(self.companion.paid_amount, Decimal('18.00'))

    def test_paid_total_cannot_be_reduced_below_a_reconciled_amount(self):
        transaction = BankTransaction.objects.create(
            external_id='EDIT-PAYMENT-1', booking_date=date.today(), amount='25.00', payer='Cliente', reference='Pago',
        )
        PaymentAllocation.objects.create(
            transaction=transaction, registration=self.registration, amount='25.00', confirmed_by=self.user,
        )

        self.client.get(reverse('edit-champ-registration-payment'), {
            'champ_id': self.championship.id, 'registration_id': self.registration.id, 'amount': '20.00',
        })

        self.registration.refresh_from_db()
        self.assertEqual(self.registration.paid_amount, Decimal('15.00'))

    def test_admin_can_assign_a_registration_payment_to_its_companion(self):
        transaction = BankTransaction.objects.create(
            external_id='ASSIGN-PAYMENT-1', booking_date=date.today(), amount='15.00', payer='Cliente', reference='Viaje',
        )
        PaymentAllocation.objects.create(
            transaction=transaction, registration=self.registration, amount='15.00', confirmed_by=self.user,
        )

        response = self.client.get(reverse('assign-champ-registration-payment-to-companion'), {
            'champ_id': self.championship.id,
            'registration_id': self.registration.id,
            'companion_id': self.companion.id,
            'amount': '10.00',
        })

        self.assertEqual(response.status_code, 200)
        self.registration.refresh_from_db()
        self.companion.refresh_from_db()
        self.assertEqual(self.registration.paid_amount, Decimal('5.00'))
        self.assertEqual(self.companion.paid_amount, Decimal('20.00'))
        self.assertEqual(self.registration.bank_allocations.aggregate(total=Sum('amount'))['total'], Decimal('5.00'))
        self.assertEqual(self.companion.bank_allocations.aggregate(total=Sum('amount'))['total'], Decimal('10.00'))

    def test_standard_post_can_assign_a_payment_to_a_companion(self):
        response = self.client.post(reverse('assign-champ-registration-payment-to-companion'), {
            'champ_id': self.championship.id,
            'registration_id': self.registration.id,
            'companion_id': self.companion.id,
            'amount': '5.00',
        })

        self.assertRedirects(response, reverse('champs-details', args=[self.championship.id]))
        self.registration.refresh_from_db()
        self.companion.refresh_from_db()
        self.assertEqual(self.registration.paid_amount, Decimal('10.00'))
        self.assertEqual(self.companion.paid_amount, Decimal('15.00'))


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
