from django.contrib import admin
from .models import Game, MineMatrix

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'rows', 'cols', 'mines', 'is_completed', 'date')
    search_fields = ('user__username',)
    list_filter = ('is_completed', 'date')

@admin.register(MineMatrix)
class MineMatrixAdmin(admin.ModelAdmin):
    list_display = ('game', 'state', 'mines')
    search_fields = ('game__id',)