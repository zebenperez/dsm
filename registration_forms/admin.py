from django.contrib import admin
from django.contrib import messages
from django.db import transaction

from .models import Form, FormAnswer, FormQuestion, FormSubmission


class FormQuestionInline(admin.TabularInline):
    model = FormQuestion
    extra = 1
    fields = ('position', 'text', 'answer_type', 'options', 'required')


@admin.register(Form)
class FormAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_published', 'response_start_at', 'deadline', 'allow_response_changes', 'created_at')
    list_filter = ('is_published', 'target_groups')
    search_fields = ('title', 'description')
    filter_horizontal = ('target_groups',)
    inlines = (FormQuestionInline,)
    actions = ('clone_selected_forms',)

    def clone_selected_forms(self, request, queryset):
        with transaction.atomic():
            clones = [form.clone() for form in queryset]
        self.message_user(
            request,
            '%d formulario(s) clonado(s) como borrador.' % len(clones),
            messages.SUCCESS,
        )

    clone_selected_forms.short_description = 'Clonar los formularios seleccionados'


class FormAnswerInline(admin.TabularInline):
    model = FormAnswer
    extra = 0
    readonly_fields = ('question', 'short_text', 'yes_no')
    can_delete = False


@admin.register(FormSubmission)
class FormSubmissionAdmin(admin.ModelAdmin):
    list_display = ('form', 'student', 'submitted_at')
    list_filter = ('form',)
    search_fields = ('student__name', 'student__code', 'form__title')
    readonly_fields = ('form', 'student', 'submitted_at')
    inlines = (FormAnswerInline,)


@admin.register(FormQuestion)
class FormQuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'form', 'answer_type', 'required', 'position')
    list_filter = ('answer_type', 'required')
    search_fields = ('text', 'form__title')


@admin.register(FormAnswer)
class FormAnswerAdmin(admin.ModelAdmin):
    list_display = ('question', 'submission', 'value')
    search_fields = ('question__text', 'submission__student__name')
