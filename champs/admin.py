from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import *


'''
	Inlines
'''
class ChampCostInline(admin.TabularInline):
	model = ChampCost
	extra = 1

class ChampCategoryInline(admin.TabularInline):
	model = ChampCategory
	extra = 1

class ChampFileInline(admin.TabularInline):
	model = ChampFile
	extra = 1

'''
	Admin
'''
class ChampionshipAdmin(admin.ModelAdmin):
	list_display = ('name', 'date',)
	inlines = [ChampCostInline, ChampCategoryInline, ChampFileInline]

class ChampCategoryAdmin(admin.ModelAdmin):
	list_display = ('category', 'amount',)

class ChampCostAdmin(admin.ModelAdmin):
	list_display = ('cost', 'amount',)

class ChampFileAdmin(admin.ModelAdmin):
	list_display = ('name', 'file',)

class CostAdmin(admin.ModelAdmin):
	list_display = ('name',)

class RegistrationAdmin(admin.ModelAdmin):
	list_display = ('champ', 'student', 'get_categories')
	list_filter = ('champ',)
	search_fields = ['student',]
	
	def get_categories(self, obj):
		html = ""
		for item in obj.categories.all():
			html += "%s <br/>" % item
		return mark_safe(html)
	get_categories.short_description = 'Categorías' 

class RegistrationFileAdmin(admin.ModelAdmin):
	list_display = ('file', )

admin.site.register(Category)
admin.site.register(Championship, ChampionshipAdmin)
admin.site.register(ChampCategory, ChampCategoryAdmin)
admin.site.register(ChampCost, ChampCostAdmin)
admin.site.register(ChampFile, ChampFileAdmin)
admin.site.register(Cost, CostAdmin)
admin.site.register(Registration, RegistrationAdmin)
admin.site.register(RegistrationFile, RegistrationFileAdmin)

