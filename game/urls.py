from django.urls import path
from . import views
from . import spectator_views

app_name = 'game'

urlpatterns = [
    path('new/', views.new_game, name='new_game'),
    path('<int:game_id>/', views.play, name='play'),
    path('<int:game_id>/spectate/', spectator_views.spectate, name='spectate'),
    path('<int:game_id>/spectate/data/', spectator_views.spectate_data, name='spectate_data'),
    path('live/', spectator_views.live_games, name='live_games'),
    # 保留HTTP接口作为备用
    path('<int:game_id>/action/', views.action, name='action'),
]