from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Game
import random
import json
from django.utils import timezone

@login_required
def new_game(request):
    rows, cols, mines = 9, 9, 10  # 默认值
    game = Game.objects.create(user=request.user, rows=rows, cols=cols, mines=mines)
    
    # 生成雷位置
    total = rows * cols
    mine_positions = set(random.sample(range(total), mines))
    game.initialize_game_state(mine_positions)
    
    # 自动安全点击
    _auto_safe_clicks(game, target_revealed=9)
    game.save()
    
    return redirect('game:play', game_id=game.id)

def _auto_safe_clicks(game, target_revealed=9):
    """优化的自动安全点击"""
    mines = game.game_state['mines']
    revealed = game.game_state['revealed']
    
    # 记录开始时间
    if not game.start_time:
        game.start_time = timezone.now()
    
    # 获取所有安全的空白位置（周围没有雷的位置）
    safe_empty_positions = []
    for i in range(game.rows):
        for j in range(game.cols):
            if not mines[i][j] and _count_neighbor_mines_fast(mines, i, j, game.rows, game.cols) == 0:
                safe_empty_positions.append((i, j))
    
    # 随机选择一个空白位置点击
    if safe_empty_positions:
        random.shuffle(safe_empty_positions)
        row, col = safe_empty_positions[0]
        _reveal_area_fast(game.game_state, row, col, game.rows, game.cols)

def _reveal_area_fast(game_state, x, y, rows, cols):
    """优化的递归展开"""
    mines = game_state['mines']
    revealed = game_state['revealed']
    
    stack = [(x, y)]
    while stack:
        i, j = stack.pop()
        if i < 0 or i >= rows or j < 0 or j >= cols or revealed[i][j] or mines[i][j]:
            continue
            
        revealed[i][j] = 1
        
        # 如果周围没有雷，继续展开
        if _count_neighbor_mines_fast(mines, i, j, rows, cols) == 0:
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    stack.append((i + dx, j + dy))

def _count_neighbor_mines_fast(mines, x, y, rows, cols):
    """优化的邻居雷数计算"""
    count = 0
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            if dx == 0 and dy == 0:
                continue
            ni, nj = x + dx, y + dy
            if 0 <= ni < rows and 0 <= nj < cols and mines[ni][nj]:
                count += 1
    return count

@login_required
def play(request, game_id):
    game = get_object_or_404(Game, id=game_id, user=request.user)
    
    context = {
        'game': game,
        'state_matrix': game.get_state_matrix(),
        'mines_matrix': game.get_mines_matrix(),
        'rows': game.rows,
        'cols': game.cols,
        'used_time': f"{game.get_used_time():.2f}",
        'start_time_str': game.start_time.strftime('%H:%M:%S') if game.start_time else '',
    }
    return render(request, 'game/play.html', context)

@login_required
def action(request, game_id):
    if request.method != 'POST':
        return redirect('game:play', game_id=game_id)
    
    game = get_object_or_404(Game, id=game_id, user=request.user)
    
    # 游戏已结束
    if game.is_completed:
        return redirect('game:play', game_id=game_id)
    
    # 批量操作
    if request.POST.get('batch_actions'):
        actions = json.loads(request.POST['batch_actions'])
        for act in actions:
            x, y, action_type = int(act['x']), int(act['y']), act['act']
            _process_action(game, x, y, action_type)
    else:
        # 单步操作
        x = int(request.POST.get('x'))
        y = int(request.POST.get('y'))
        act = request.POST.get('act')
        _process_action(game, x, y, act)
    
    # 检查游戏结束
    _check_game_end(game)
    game.save()
    
    return redirect('game:play', game_id=game_id)

def _process_action(game, x, y, action):
    """处理单个动作"""
    revealed = game.game_state['revealed']
    flagged = game.game_state['flagged']
    mines = game.game_state['mines']
    
    if action == 'open' and not revealed[x][y] and not flagged[x][y]:
        # 检查是否点击到雷
        if mines[x][y]:
            # 直接揭示这个雷
            revealed[x][y] = 1
        else:
            # 安全位置，正常展开
            _reveal_area_fast(game.game_state, x, y, game.rows, game.cols)
    elif action == 'flag' and not revealed[x][y]:
        flagged[x][y] = 1 - flagged[x][y]  # 切换标记状态

def _check_game_end(game):
    """检查游戏是否结束并标记完成状态"""
    if game.is_completed:
        return
        
    mines = game.game_state['mines']
    revealed = game.game_state['revealed']
    
    # 检查是否踩雷
    for i in range(game.rows):
        for j in range(game.cols):
            if revealed[i][j] and mines[i][j]:
                # 游戏失败
                game.mark_completed(is_win=False)
                return
    
    # 检查是否胜利
    total_safe = game.rows * game.cols - game.mines
    revealed_safe = sum(sum(row) for row in revealed)
    if revealed_safe == total_safe:
        # 游戏胜利
        game.mark_completed(is_win=True)

