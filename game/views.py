from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Game, MineMatrix
import random
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from django.utils import timezone

@login_required
def new_game(request):
    rows, cols, mines = 9, 9, 10  # 可根据需求调整或从表单获取
    game = Game.objects.create(user=request.user, rows=rows, cols=cols, mines=mines)
    # 生成雷矩阵
    total = rows * cols
    mine_positions = set(random.sample(range(total), mines))
    mines_str = ''.join(['1' if i in mine_positions else '0' for i in range(total)])
    state_str = '0' * total  # 全部未揭开
    
    # 创建矩阵
    matrix = MineMatrix.objects.create(game=game, state=state_str, mines=mines_str)
    
    # 自动进行安全点击，直到翻开格子数 >= 9
    _auto_safe_clicks(game, matrix, rows, cols, target_revealed=9)
    
    return redirect('game:play', game_id=game.id)

def _auto_safe_clicks(game, matrix, rows, cols, target_revealed=9):
    """自动进行安全点击，直到翻开的格子数达到目标"""
    state = list(matrix.state)
    mines = list(matrix.mines)
    
    # 记录开始时间
    if not game.start_time:
        game.start_time = timezone.now()
    
    # 获取所有安全位置（非雷位置）
    safe_positions = []
    for i in range(rows * cols):
        if mines[i] == '0':  # 不是雷
            row, col = i // cols, i % cols
            safe_positions.append((row, col))
    
    # 随机打乱安全位置
    random.shuffle(safe_positions)
    
    revealed_count = 0
    attempts = 0
    max_attempts = min(len(safe_positions), 20)  # 最多尝试20次
    
    while revealed_count < target_revealed and attempts < max_attempts:
        if attempts >= len(safe_positions):
            break
            
        row, col = safe_positions[attempts]
        attempts += 1
        
        # 检查该位置是否已经被揭开
        idx = row * cols + col
        if state[idx] != '0':
            continue
            
        # 进行安全点击
        old_revealed = sum(1 for s in state if s == '1')
        _reveal_area(state, mines, row, col, rows, cols)
        new_revealed = sum(1 for s in state if s == '1')
        revealed_count = new_revealed
        
        # 如果这次点击揭开了大片区域，可能已经达到目标
        if revealed_count >= target_revealed:
            break
    
    # 保存状态
    matrix.state = ''.join(state)
    matrix.save()
    game.save()

@login_required
def play(request, game_id):
    game = get_object_or_404(Game, id=game_id, user=request.user)
    matrix = game.matrix
    rows, cols = game.rows, game.cols
    state_matrix = matrix.get_state_matrix()
    mines_matrix = matrix.get_mines_matrix()
    # 计算用时
    if game.start_time:
        if game.end_time:
            used_time = (game.end_time - game.start_time).total_seconds()
        else:
            used_time = (timezone.now() - game.start_time).total_seconds()
    else:
        used_time = 0
    context = {
        'game': game,
        'state_matrix': state_matrix,
        'mines_matrix': mines_matrix,
        'rows': rows,
        'cols': cols,
        'used_time': "%.2f" % used_time,
        'start_time_str': game.start_time.strftime('%H:%M:%S') if game.start_time else '',
    }
    return render(request, 'game/play.html', context)

@login_required
def action(request, game_id):
    game = get_object_or_404(Game, id=game_id, user=request.user)
    
    # 如果游戏已结束，不允许操作
    if game.end_time:
        return redirect('game:play', game_id=game.id)
    
    matrix = game.matrix
    rows, cols = game.rows, game.cols
    state = list(matrix.state)
    mines = list(matrix.mines)

    # 批量操作支持
    if request.method == 'POST' and request.POST.get('batch_actions'):
        actions = json.loads(request.POST['batch_actions'])
        for act in actions:
            x, y, action_type = int(act['x']), int(act['y']), act['act']
            idx = x * cols + y
            if action_type == 'open' and state[idx] == '0':
                _reveal_area(state, mines, x, y, rows, cols)
            elif action_type == 'flag' and state[idx] == '0':
                state[idx] = '2'
            elif action_type == 'flag' and state[idx] == '2':
                state[idx] = '0'  # 取消标记
        # 检查是否结束
        _check_and_set_end_time(game, state, mines, rows, cols)
        matrix.state = ''.join(state)
        matrix.save()
        game.save()
        return redirect('game:play', game_id=game.id)

    # 单步操作
    if request.method == 'POST':
        x = int(request.POST.get('x'))
        y = int(request.POST.get('y'))
        act = request.POST.get('act')  # 'open' or 'flag'
        idx = x * cols + y
        if act == 'open' and state[idx] == '0':
            _reveal_area(state, mines, x, y, rows, cols)
        elif act == 'flag' and state[idx] == '0':
            state[idx] = '2'
        elif act == 'flag' and state[idx] == '2':
            state[idx] = '0'  # 取消标记
        # 检查是否结束
        _check_and_set_end_time(game, state, mines, rows, cols)
        matrix.state = ''.join(state)
        matrix.save()
        game.save()
    return redirect('game:play', game_id=game.id)

def _reveal_area(state, mines, x, y, rows, cols):
    """递归展开无雷区域"""
    stack = [(x, y)]
    while stack:
        i, j = stack.pop()
        idx = i * cols + j
        if state[idx] != '0':
            continue
        state[idx] = '1'
        # 如果当前不是雷且周围没有雷，递归展开
        if mines[idx] == '0' and _count_neighbor_mines(mines, i, j, rows, cols) == 0:
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    ni, nj = i + dx, j + dy
                    if 0 <= ni < rows and 0 <= nj < cols and state[ni * cols + nj] == '0':
                        stack.append((ni, nj))

def _count_neighbor_mines(mines, x, y, rows, cols):
    count = 0
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            if dx == 0 and dy == 0:
                continue
            ni, nj = x + dx, y + dy
            if 0 <= ni < rows and 0 <= nj < cols:
                idx = ni * cols + nj
                if mines[idx] == '1':
                    count += 1
    return count

def _check_and_set_end_time(game, state, mines, rows, cols):
    """判断游戏是否结束，并记录结束时间"""
    total = rows * cols
    revealed = [i for i, s in enumerate(state) if s == '1']
    # 输：有雷被翻开
    for idx in revealed:
        if mines[idx] == '1':
            if not game.end_time:
                game.end_time = timezone.now()
            return
    # 胜：所有非雷格都被翻开
    if all((state[i] == '1' or mines[i] == '1') for i in range(total)):
        if not game.end_time:
            game.end_time = timezone.now()

