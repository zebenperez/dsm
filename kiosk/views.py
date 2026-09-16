from functools import wraps

from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from .models import KioskPayment, KioskProduct, KioskTicket


def kiosk_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if request.user.is_authenticated and (request.user.is_superuser or request.user.groups.filter(name='kiosk').exists()):
            return view(request, *args, **kwargs)
        return redirect('kiosk-login')
    return wrapped


def login(request):
    if request.user.is_authenticated and (request.user.is_superuser or request.user.groups.filter(name='kiosk').exists()):
        return redirect('kiosk-terminal')
    error = None
    if request.method == 'POST':
        user = authenticate(username=request.POST.get('username', ''), password=request.POST.get('password', ''))
        if user and (user.is_superuser or user.groups.filter(name='kiosk').exists()):
            auth_login(request, user)
            return redirect('kiosk-terminal')
        error = 'Usuario, contraseña o permisos de quiosco no válidos.'
    return render(request, 'kiosk/login.html', {'error': error})


@kiosk_required
def logout(request):
    auth_logout(request)
    return redirect('kiosk-login')


def _cart(request):
    return request.session.setdefault('kiosk_cart', {})


@kiosk_required
def terminal(request):
    cart = _cart(request)
    if request.method == 'POST':
        action = request.POST.get('action')
        product_id = request.POST.get('product_id')
        if action == 'add' and KioskProduct.objects.filter(pk=product_id, active=True).exists():
            cart[str(product_id)] = int(cart.get(str(product_id), 0)) + 1
        elif action == 'set_quantity' and product_id in cart:
            try:
                quantity = int(request.POST.get('quantity', 0))
            except (TypeError, ValueError):
                quantity = 0
            if quantity > 0:
                cart[str(product_id)] = quantity
            else:
                cart.pop(str(product_id), None)
        elif action == 'remove':
            cart.pop(str(product_id), None)
        elif action == 'clear':
            cart.clear()
        request.session.modified = True
        return redirect('kiosk-terminal')

    search = request.GET.get('q', '').strip()
    product_list = KioskProduct.objects.filter(active=True)
    if search:
        product_list = product_list.filter(name__icontains=search)
    products = list(product_list)
    cart_products = {product.id: product for product in KioskProduct.objects.filter(id__in=cart.keys())}
    cart_lines = []
    total = 0
    for product_id, quantity in cart.items():
        product = cart_products.get(int(product_id))
        if product:
            line_total = product.price * quantity
            cart_lines.append({'product': product, 'quantity': quantity, 'total': line_total})
            total += line_total
    return render(request, 'kiosk/terminal.html', {
        'product_list': products,
        'cart_lines': cart_lines,
        'cart_total': total,
        'search': search,
        'payment_methods': KioskPayment.METHOD_CHOICES,
    })


@kiosk_required
def checkout(request):
    if request.method != 'POST':
        return redirect('kiosk-terminal')
    try:
        ticket = KioskTicket.create_from_cart(
            request.user,
            _cart(request),
            request.POST.get('payment_method', ''),
            request.POST.get('band', ''),
        )
    except (ValidationError, ValueError, TypeError) as error:
        messages.error(request, error.messages[0] if hasattr(error, 'messages') else str(error))
        return redirect('kiosk-terminal')
    request.session['kiosk_cart'] = {}
    request.session.modified = True
    return redirect('kiosk-receipt', ticket_id=ticket.id)


@kiosk_required
def receipt(request, ticket_id):
    ticket = get_object_or_404(KioskTicket.objects.prefetch_related('lines', 'payments'), pk=ticket_id)
    return render(request, 'kiosk/receipt.html', {'ticket': ticket})
