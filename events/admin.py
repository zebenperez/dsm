from django.contrib import admin

from .models import Event, PublicDisplaySettings


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'starts_at', 'ends_at')
    list_filter = ('starts_at',)
    search_fields = ('title', 'description')


@admin.register(PublicDisplaySettings)
class PublicDisplaySettingsAdmin(admin.ModelAdmin):
    fields = ('rotation_enabled', 'rotation_interval_seconds')

    def has_add_permission(self, request):
        return not PublicDisplaySettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
