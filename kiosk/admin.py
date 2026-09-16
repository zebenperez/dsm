from django.contrib import admin

from .models import KioskPayment, KioskProduct, KioskTicket, KioskTicketLine


@admin.register(KioskProduct)
class KioskProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'active', 'position')
    list_filter = ('active', 'category')
    search_fields = ('name', 'category')
    list_editable = ('price', 'active', 'position')


class KioskTicketLineInline(admin.TabularInline):
    model = KioskTicketLine
    extra = 0
    readonly_fields = ('product', 'product_name', 'unit_price', 'quantity', 'line_total')
    can_delete = False


class KioskPaymentInline(admin.TabularInline):
    model = KioskPayment
    extra = 0
    readonly_fields = ('method', 'amount', 'wallet_movement')
    can_delete = False


@admin.register(KioskTicket)
class KioskTicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'worker', 'total', 'status')
    list_filter = ('status', 'created_at')
    search_fields = ('id', 'worker__username')
    readonly_fields = ('created_at', 'worker', 'total', 'status')
    inlines = (KioskTicketLineInline, KioskPaymentInline)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
