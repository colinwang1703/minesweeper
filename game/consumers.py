import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.game_group_name = f'game_{self.game_id}'
        self.user = self.scope.get("user")
        
        # 加入游戏组
        await self.channel_layer.group_add(
            self.game_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # 检查游戏是否存在
        game = await self.get_game()
        if not game:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': '游戏不存在'
            }))
            await self.close()
            return
        
        # 发送连接成功消息
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': f'Connected to game {self.game_id}',
            'user': self.user.username if self.user and self.user.is_authenticated else 'Anonymous'
        }))
        
        # 发送当前游戏状态
        game_data = await self.get_game_data()
        if game_data:
            await self.send(text_data=json.dumps({
                'type': 'game_state',
                'data': game_data
            }))
        
        # 通知其他用户有人加入
        await self.channel_layer.group_send(
            self.game_group_name,
            {
                'type': 'user_joined',
                'user': self.user.username if self.user and self.user.is_authenticated else 'Anonymous',
                'channel_name': self.channel_name
            }
        )

    async def disconnect(self, close_code):
        # 通知其他用户有人离开
        await self.channel_layer.group_send(
            self.game_group_name,
            {
                'type': 'user_left',
                'user': self.user.username if self.user and self.user.is_authenticated else 'Anonymous',
            }
        )
        
        # 离开游戏组
        await self.channel_layer.group_discard(
            self.game_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            action_type = data.get('type')
            
            if action_type == 'game_action':
                await self.handle_game_action(data)
            elif action_type == 'spectator_action':
                await self.handle_spectator_action(data)
            else:
                # 简单回显消息用于测试
                await self.send(text_data=json.dumps({
                    'type': 'echo',
                    'message': f'Received: {data}'
                }))
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))

    async def handle_game_action(self, data):
        """处理游戏动作"""
        if not self.user or not self.user.is_authenticated:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': '需要登录才能操作'
            }))
            return
            
        # 获取游戏并检查权限
        game = await self.get_game()
        if not game:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': '游戏不存在'
            }))
            return
            
        # 检查是否是游戏所有者
        if game.user_id != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': '无权限操作此游戏'
            }))
            return
            
        if game.is_completed:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': '游戏已结束'
            }))
            return
        
        # 处理具体动作
        action_data = data.get('data', {})
        if 'batch_actions' in action_data:
            # 批量操作
            for action in action_data['batch_actions']:
                await self.process_single_action(game, action)
        else:
            # 单个操作
            await self.process_single_action(game, action_data)
        
        # 保存游戏状态
        await self.save_game(game)
        
        # 广播游戏状态更新
        game_data = await self.get_game_data()
        await self.channel_layer.group_send(
            self.game_group_name,
            {
                'type': 'game_update',
                'data': game_data,
                'action': action_data,
                'user': self.user.username
            }
        )

    async def handle_spectator_action(self, data):
        """处理观众动作"""
        # 添加用户认证检查
        if not self.user or not self.user.is_authenticated:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': '需要登录才能发送消息'
            }))
            return
            
        message_data = data.get('data', {})
        message_type = message_data.get('type')
        
        if message_type == 'chat':
            # 聊天消息
            await self.channel_layer.group_send(
                self.game_group_name,
                {
                    'type': 'chat_message',
                    'user': self.user.username,
                    'message': message_data.get('message', ''),
                    'timestamp': message_data.get('timestamp')
                }
            )

    # WebSocket事件处理器
    async def game_update(self, event):
        """发送游戏状态更新"""
        await self.send(text_data=json.dumps({
            'type': 'game_update',
            'data': event['data'],
            'action': event['action'],
            'user': event['user']
        }))

    async def user_joined(self, event):
        """用户加入通知"""
        if event['channel_name'] != self.channel_name:  # 不通知自己
            await self.send(text_data=json.dumps({
                'type': 'user_joined',
                'user': event['user']
            }))
    
    async def user_left(self, event):
        """用户离开通知"""
        await self.send(text_data=json.dumps({
            'type': 'user_left',
            'user': event['user']
        }))

    async def chat_message(self, event):
        """聊天消息"""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'user': event['user'],
            'message': event['message'],
            'timestamp': event['timestamp']
        }))

    # 数据库操作方法
    @database_sync_to_async
    def get_game(self):
        """获取游戏对象"""
        try:
            from .models import Game
            return Game.objects.get(id=self.game_id)
        except Game.DoesNotExist:
            return None

    @database_sync_to_async
    def get_game_data(self):
        """获取游戏数据"""
        try:
            from .models import Game
            game = Game.objects.get(id=self.game_id)
            return {
                'id': game.id,
                'rows': game.rows,
                'cols': game.cols,
                'mines': game.mines,
                'state': game.get_state_matrix(),  # 改为 'state' 而不是 'state_matrix'
                'mines_matrix': game.get_mines_matrix(),
                'is_completed': game.is_completed,
                'is_success': game.is_success,
                'used_time': game.get_used_time(),
                'start_time': game.start_time.isoformat() if game.start_time else None,
                'end_time': game.end_time.isoformat() if game.end_time else None,
                'user': game.user.username if game.user else None
            }
        except:
            return None

    @database_sync_to_async
    def process_single_action(self, game, action_data):
        """处理单个游戏动作"""
        try:
            from .views import _process_action, _check_game_end
            
            x = int(action_data.get('x', 0))
            y = int(action_data.get('y', 0))
            action = action_data.get('act', 'open')
            
            _process_action(game, x, y, action)
            _check_game_end(game)
        except Exception as e:
            print(f"处理游戏动作时出错: {e}")

    @database_sync_to_async
    def save_game(self, game):
        """保存游戏"""
        try:
            game.save()
        except Exception as e:
            print(f"保存游戏时出错: {e}")