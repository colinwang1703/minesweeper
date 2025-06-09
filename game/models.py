from django.db import models
from django.utils import timezone

class Game(models.Model):
    """
    扫雷游戏模型，包含游戏的基本信息。
    """
    id = models.AutoField(primary_key=True, verbose_name='游戏ID')
    rows = models.PositiveIntegerField(verbose_name='行数', default=9)
    cols = models.PositiveIntegerField(verbose_name='列数', default=9)
    mines = models.PositiveIntegerField(verbose_name='雷数', default=10)
    is_completed = models.BooleanField(default=False, verbose_name='完成情况')
    user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='用户')
    date = models.DateField(auto_now_add=True, verbose_name='日期', null=True, blank=True)
    start_time = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='结束时间')

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = '游戏'
        verbose_name_plural = '游戏列表'
        ordering = ['date']  # 按发布日期排序

class MineMatrix(models.Model):
    """
    存储某局游戏的雷矩阵，每个格子用两个bit表示：
    - 0: 未揭开
    - 1: 已揭开
    - 2: 标旗
    - 3: 保留
    雷布置用0/1表示
    """
    game = models.OneToOneField('Game', on_delete=models.CASCADE, related_name='matrix')
    # 状态矩阵，长度=rows*cols，每格0/1/2
    state = models.CharField(max_length=999)  # 如 "001201..."，每个字符代表一个格子的状态
    # 雷矩阵，长度=rows*cols，每格0/1
    mines = models.CharField(max_length=999)  # 如 "010000100..."，每个字符代表有无雷

    def get_state_matrix(self):
        # 返回二维数组
        rows, cols = self.game.rows, self.game.cols
        return [list(map(int, self.state[i*cols:(i+1)*cols])) for i in range(rows)]

    def get_mines_matrix(self):
        rows, cols = self.game.rows, self.game.cols
        return [list(map(int, self.mines[i*cols:(i+1)*cols])) for i in range(rows)]