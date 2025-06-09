from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.models import User
from django.contrib import messages

def login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            return redirect('lobby:index')  # 登录成功后跳转，可根据实际修改
        else:
            messages.error(request, '用户名或密码错误')
    return render(request, 'user/login.html')

def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        if password != password2:
            messages.error(request, '两次输入的密码不一致')
        elif User.objects.filter(username=username).exists():
            messages.error(request, '用户名已存在')
        else:
            user = User.objects.create_user(username=username, password=password)
            # UserProfile 会通过信号自动创建
            auth_login(request, user)
            return redirect('lobby:index')  # 注册成功后跳转
    return render(request, 'user/register.html')