from django.contrib import admin
from .models import Game, SpectatorSession

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'rows', 'cols', 'mines', 'is_completed', 'is_success', 'date')
    search_fields = ('user__username',)
    list_filter = ('is_completed', 'date')

@admin.register(SpectatorSession)
class SpectatorSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'game', 'spectator', 'last_seen')
    search_fields = ('game__id', 'spectator__username')
    list_filter = ('last_seen',)
    raw_id_fields = ('game', 'spectator')