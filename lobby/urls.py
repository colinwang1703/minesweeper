from django.urls import path
from . import views

app_name = "lobby"

urlpatterns = [
    path('', views.index, name='index'),
    # 其他 URL 路径可以在这里添加
]