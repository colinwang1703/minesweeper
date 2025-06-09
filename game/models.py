from django.db import models
from django.utils import timezone
import json

class Game(models.Model):
    """
    扫雷游戏模型，包含游戏的基本信息。
    """
    id = models.AutoField(primary_key=True, verbose_name='游戏ID')
    rows = models.PositiveIntegerField(verbose_name='行数', default=9)
    cols = models.PositiveIntegerField(verbose_name='列数', default=9)
    mines = models.PositiveIntegerField(verbose_name='雷数', default=10)
    is_completed = models.BooleanField(default=False, verbose_name='完成情况')
    is_success = models.BooleanField(default=False, verbose_name='是否成功')
    user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='用户')
    date = models.DateField(auto_now_add=True, verbose_name='日期', null=True, blank=True)
    start_time = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='结束时间')
    
    # 新增观众相关字段
    allow_spectators = models.BooleanField(default=True, verbose_name='允许观众')
    spectator_count = models.PositiveIntegerField(default=0, verbose_name='观众数量')
    
    # 直接存储为JSON字符串，避免字符串操作
    game_state = models.JSONField(default=dict, verbose_name='游戏状态')
    # 格式: {
    #   "mines": [[0,1,0], [1,0,1], ...],  # 雷位置矩阵
    #   "revealed": [[0,1,0], [1,0,1], ...],  # 已揭开状态
    #   "flagged": [[0,0,1], [0,1,0], ...]   # 标记状态
    # }

    def get_state_matrix(self):
        """获取状态矩阵 (0=未揭开, 1=已揭开, 2=已标记)"""
        state = []
        revealed = self.game_state.get('revealed', [])
        flagged = self.game_state.get('flagged', [])
        
        for i in range(self.rows):
            row = []
            for j in range(self.cols):
                if flagged[i][j]:
                    row.append(2)
                elif revealed[i][j]:
                    row.append(1)
                else:
                    row.append(0)
            state.append(row)
        return state

    def get_mines_matrix(self):
        """获取雷矩阵"""
        return self.game_state.get('mines', [])

    def initialize_game_state(self, mine_positions):
        """初始化游戏状态"""
        mines = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        revealed = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        flagged = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        
        # 设置雷位置
        for pos in mine_positions:
            row, col = pos // self.cols, pos % self.cols
            mines[row][col] = 1
        
        self.game_state = {
            'mines': mines,
            'revealed': revealed,
            'flagged': flagged
        }

    def mark_completed(self, is_win):
        """标记游戏完成"""
        if not self.is_completed:
            self.is_completed = True
            self.is_success = is_win
            if not self.end_time:
                self.end_time = timezone.now()

    def get_used_time(self):
        """获取游戏用时（秒）"""
        if not self.start_time:
            return 0
        end = self.end_time or timezone.now()
        return (end - self.start_time).total_seconds()

    def can_be_spectated(self):
        """判断是否可以被观看"""
        return self.allow_spectators and not self.is_completed

    class Meta:
        verbose_name = '游戏'
        verbose_name_plural = '游戏列表'
        ordering = ['-date']

class SpectatorSession(models.Model):
    """观众会话模型"""
    game = models.ForeignKey(Game, on_delete=models.CASCADE, verbose_name='游戏')
    spectator = models.ForeignKey('auth.User', on_delete=models.CASCADE, verbose_name='观众')
    join_time = models.DateTimeField(auto_now_add=True, verbose_name='加入时间')
    last_seen = models.DateTimeField(auto_now=True, verbose_name='最后活跃时间')
    
    class Meta:
        unique_together = ['game', 'spectator']
        verbose_name = '观众会话'
        verbose_name_plural = '观众会话列表'