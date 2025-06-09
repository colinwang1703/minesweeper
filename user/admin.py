from django.contrib import admin
from .models import UserProfile

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'rating')  # 在列表页显示用户和分数

admin.site.register(UserProfile, UserProfileAdmin)