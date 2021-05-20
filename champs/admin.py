from django.contrib import admin
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


admin.site.register(Category)
admin.site.register(Championship, ChampionshipAdmin)
admin.site.register(ChampCategory)
admin.site.register(ChampCost)
admin.site.register(ChampFile)
admin.site.register(Cost)

