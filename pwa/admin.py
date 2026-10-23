from django.contrib import admin

from .models import DocumentTemplate, StudentDocument


@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    list_display = ('title', 'audience', 'is_active', 'created_at')
    list_filter = ('audience', 'is_active')
    search_fields = ('title', 'description')


@admin.register(StudentDocument)
class StudentDocumentAdmin(admin.ModelAdmin):
    list_display = ('student', 'template', 'uploaded_at')
    list_filter = ('template',)
    search_fields = ('student__name', 'student__code')
    readonly_fields = ('uploaded_at', 'original_filename')
