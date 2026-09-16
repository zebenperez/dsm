from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models, transaction

from studio.models import InsufficientWalletBalance, Student, WalletMovement


class KioskProduct(models.Model):
    name = models.CharField(max_length=200, verbose_name='Nombre')
    category = models.CharField(max_length=100, blank=True, verbose_name='Categoría')
    price = models.DecimalField(max_digits=8, decimal_places=2, verbose_name='Precio')
    image = models.ImageField(upload_to='kiosk/products/', blank=True, verbose_name='Imagen')
    active = models.BooleanField(default=True, verbose_name='Disponible')
    position = models.PositiveIntegerField(default=0, verbose_name='Orden')

    class Meta:
        ordering = ('position', 'category', 'name')
        verbose_name = 'producto de quiosco'
        verbose_name_plural = 'productos de quiosco'

    def __str__(self):
        return self.name

    def clean(self):
        if self.price is None or self.price <= 0:
            raise ValidationError({'price': 'El precio debe ser mayor que cero.'})


class KioskTicket(models.Model):
    STATUS_COMPLETED = 'completed'
    STATUS_REFUNDED = 'refunded'
    STATUS_CHOICES = (
        (STATUS_COMPLETED, 'Completado'),
        (STATUS_REFUNDED, 'Devuelto'),
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha')
    worker = models.ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL, related_name='kiosk_tickets', verbose_name='Vendedor/a')
    total = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name='Total')
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_COMPLETED, verbose_name='Estado')

    class Meta:
        ordering = ('-created_at', '-id')
        verbose_name = 'ticket de quiosco'
        verbose_name_plural = 'tickets de quiosco'

    def __str__(self):
        return 'Ticket #%s' % self.pk

    @classmethod
    def create_from_cart(cls, worker, cart, payment_method, band=''):
        """Persist a ticket and payment atomically from a server-side cart."""
        if payment_method not in KioskPayment.METHOD_VALUES:
            raise ValidationError('Método de pago no válido.')
        if not cart:
            raise ValidationError('El carrito está vacío.')

        with transaction.atomic():
            product_ids = [int(product_id) for product_id in cart]
            product_map = {
                product.id: product
                for product in KioskProduct.objects.filter(id__in=product_ids, active=True)
            }
            lines = []
            total = Decimal('0.00')
            for product_id, quantity in cart.items():
                product = product_map.get(int(product_id))
                quantity = int(quantity)
                if not product or quantity < 1:
                    raise ValidationError('Hay un producto no disponible en el carrito.')
                line_total = product.price * quantity
                lines.append((product, quantity, line_total))
                total += line_total

            ticket = cls.objects.create(worker=worker, total=total)
            for product, quantity, line_total in lines:
                KioskTicketLine.objects.create(
                    ticket=ticket,
                    product=product,
                    product_name=product.name,
                    unit_price=product.price,
                    quantity=quantity,
                    line_total=line_total,
                )

            wallet_movement = None
            if payment_method == KioskPayment.METHOD_WALLET:
                student = Student.objects.filter(band=band.strip()).first()
                if not student:
                    raise ValidationError('No hay ninguna alumna/o asociada a esta pulsera.')
                try:
                    wallet_movement = WalletMovement.record(
                        student, -total, WalletMovement.TYPE_PURCHASE,
                        'Quiosco · Ticket #%s' % ticket.pk, '', worker,
                    )
                except InsufficientWalletBalance:
                    raise ValidationError('Saldo insuficiente para realizar este pago.')

            KioskPayment.objects.create(
                ticket=ticket,
                method=payment_method,
                amount=total,
                wallet_movement=wallet_movement,
            )
            return ticket


class KioskTicketLine(models.Model):
    ticket = models.ForeignKey(KioskTicket, on_delete=models.CASCADE, related_name='lines', verbose_name='Ticket')
    product = models.ForeignKey(KioskProduct, blank=True, null=True, on_delete=models.SET_NULL, verbose_name='Producto')
    product_name = models.CharField(max_length=200, verbose_name='Producto vendido')
    unit_price = models.DecimalField(max_digits=8, decimal_places=2, verbose_name='Precio unitario')
    quantity = models.PositiveIntegerField(verbose_name='Cantidad')
    line_total = models.DecimalField(max_digits=8, decimal_places=2, verbose_name='Total')

    class Meta:
        verbose_name = 'línea de ticket de quiosco'
        verbose_name_plural = 'líneas de tickets de quiosco'


class KioskPayment(models.Model):
    METHOD_CASH = 'cash'
    METHOD_CARD = 'card'
    METHOD_WALLET = 'wallet'
    METHOD_CHOICES = (
        (METHOD_CASH, 'Efectivo'),
        (METHOD_CARD, 'Tarjeta'),
        (METHOD_WALLET, 'Pulsera/llavero'),
    )
    METHOD_VALUES = {choice[0] for choice in METHOD_CHOICES}

    ticket = models.ForeignKey(KioskTicket, on_delete=models.CASCADE, related_name='payments', verbose_name='Ticket')
    method = models.CharField(max_length=10, choices=METHOD_CHOICES, verbose_name='Método')
    amount = models.DecimalField(max_digits=8, decimal_places=2, verbose_name='Importe')
    wallet_movement = models.OneToOneField(WalletMovement, blank=True, null=True, on_delete=models.SET_NULL, related_name='kiosk_payment', verbose_name='Movimiento de monedero')

    class Meta:
        verbose_name = 'pago de quiosco'
        verbose_name_plural = 'pagos de quiosco'
