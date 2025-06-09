from django.urls import path
from . import views

app_name = 'game'

urlpatterns = [
    path('new/', views.new_game, name='new_game'),
    path('<int:game_id>/', views.play, name='play'),
    path('<int:game_id>/action/', views.action, name='action'),
]