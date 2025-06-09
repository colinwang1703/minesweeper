from django.contrib import admin
from .models import Game

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'rows', 'cols', 'mines', 'is_completed', 'is_success', 'date')
    search_fields = ('user__username',)
    list_filter = ('is_completed', 'date')