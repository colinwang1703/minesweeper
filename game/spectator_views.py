from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.contrib import messages
from datetime import timedelta
from .models import Game, SpectatorSession

@login_required(login_url='/user/login/')
def live_games(request):
    """显示可观看的直播游戏列表"""
    # 计算300秒前的时间
    cutoff_time = timezone.now() - timedelta(seconds=300)
    
    live_games = Game.objects.filter(
        is_completed=False,
        allow_spectators=True,
        start_time__isnull=False,
        start_time__gte=cutoff_time  # 只显示300秒内的游戏
    ).exclude(user=request.user).select_related('user').order_by('-start_time')  # 按开始时间倒序，最新的在前
    
    context = {
        'live_games': live_games,
    }
    return render(request, 'game/live_games.html', context)

@login_required(login_url='/user/login/')
def spectate(request, game_id):
    """观众观看游戏"""
    game = get_object_or_404(Game, id=game_id)
    
    # 检查游戏是否超过300秒
    if game.start_time and timezone.now() - game.start_time > timedelta(seconds=300):
        messages.error(request, '该游戏已进行超过5分钟，不再支持观看')
        return redirect('game:live_games')
    
    # 检查是否可以观看
    if not game.can_be_spectated():
        messages.error(request, '该游戏不允许观看或已结束')
        return redirect('game:live_games')
    
    if game.user == request.user:
        # 如果是游戏创建者，重定向到游戏页面
        return redirect('game:play', game_id=game_id)
    
    # 创建或更新观众会话
    spectator_session, created = SpectatorSession.objects.get_or_create(
        game=game,
        spectator=request.user,
        defaults={'join_time': timezone.now()}
    )
    
    if not created:
        spectator_session.last_seen = timezone.now()
        spectator_session.save()
    
    # 更新观众数量
    active_spectators = SpectatorSession.objects.filter(
        game=game,
        last_seen__gte=timezone.now() - timezone.timedelta(minutes=5)
    ).count()
    
    game.spectator_count = active_spectators
    game.save(update_fields=['spectator_count'])
    
    context = {
        'game': game,
        'is_spectator': True,
        'spectator_count': active_spectators,
    }
    
    return render(request, 'game/spectate.html', context)

@login_required(login_url='/user/login/')
def spectate_data(request, game_id):
    """获取观众观看数据（AJAX）"""
    game = get_object_or_404(Game, id=game_id)
    
    # 检查游戏是否超过300秒
    if game.start_time and timezone.now() - game.start_time > timedelta(seconds=300):
        return JsonResponse({'error': '游戏已进行超过5分钟，观看已结束'}, status=403)
    
    if game.is_completed:
        if game.is_success:
            return JsonResponse({'error': '🎉 游戏胜利！'}, status=403)
        else:
            return JsonResponse({'error': '💥 游戏失败！'}, status=403)

    if not game.can_be_spectated():
        return JsonResponse({'error': '游戏不可观看'}, status=403)
    
    # 更新观众最后活跃时间
    try:
        spectator_session = SpectatorSession.objects.get(
            game=game,
            spectator=request.user
        )
        spectator_session.last_seen = timezone.now()
        spectator_session.save()
    except SpectatorSession.DoesNotExist:
        pass
    
    # 计算数字矩阵（只显示已揭开的部分）
    numbers = []
    mines_matrix = game.get_mines_matrix()
    state_matrix = game.get_state_matrix()
    
    for i in range(game.rows):
        row = []
        for j in range(game.cols):
            if state_matrix[i][j] == 1:  # 已揭开
                if mines_matrix[i][j]:
                    row.append(-1)  # 雷
                else:
                    # 计算周围雷数
                    count = 0
                    for di in [-1, 0, 1]:
                        for dj in [-1, 0, 1]:
                            ni, nj = i + di, j + dj
                            if 0 <= ni < game.rows and 0 <= nj < game.cols:
                                if mines_matrix[ni][nj]:
                                    count += 1
                    row.append(count)
            else:
                row.append(None)  # 未揭开
        numbers.append(row)
    
    # 计算游戏剩余观看时间
    elapsed_time = int(game.get_used_time())
    time_left = max(0, 300 - elapsed_time)
    
    data = {
        'state': state_matrix,
        'numbers': numbers,
        'is_completed': game.is_completed,
        'is_success': game.is_success,
        'used_time': elapsed_time,
        'spectator_count': game.spectator_count,
        'mines_left': game.mines - sum(sum(row) for row in game.game_state.get('flagged', [])),
        'time_left': time_left,  # 添加剩余观看时间
    }
    
    return JsonResponse(data)
