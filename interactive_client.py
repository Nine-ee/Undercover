"""
交互式游戏方客户端
可以看到其他人的描述、倒计时，手动输入描述和投票
"""
import requests
import time
import os
import sys

# 配置服务器地址
BASE_URL = "http://127.0.0.1:5000"

class InteractiveClient:
    def __init__(self, group_name: str):
        self.group_name = group_name
        self.word = None
        self.last_descriptions = []
    
    def clear_screen(self):
        """清屏"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self, title: str):
        """打印标题"""
        print("\n" + "="*50)
        print(f"  {title}")
        print("="*50)
    
    def get_status(self):
        """获取游戏状态"""
        try:
            r = requests.get(f"{BASE_URL}/api/status", timeout=3)
            if r.status_code == 200:
                return r.json().get('data', {})
        except:
            pass
        return {}
    
    def get_descriptions(self):
        """获取当前回合的描述（通过状态API无法获取，需要单独接口）"""
        # 注意：公开API不暴露描述内容，这里模拟从主持方广播获取
        # 实际游戏中，主持方会念出来或显示在大屏幕上
        try:
            # 尝试获取（如果有公开接口的话）
            r = requests.get(f"{BASE_URL}/api/descriptions", timeout=3)
            if r.status_code == 200:
                return r.json().get('data', {})
        except:
            pass
        return {}
    
    def register(self) -> bool:
        """注册"""
        try:
            r = requests.post(f"{BASE_URL}/api/register", 
                            json={"group_name": self.group_name}, timeout=3)
            result = r.json()
            if result.get('code') == 200:
                print(f"✓ 注册成功！")
                return True
            else:
                print(f"✗ 注册失败: {result.get('message')}")
                return False
        except Exception as e:
            print(f"✗ 连接失败: {e}")
            return False
    
    def get_word(self):
        """获取词语"""
        try:
            r = requests.get(f"{BASE_URL}/api/word", 
                           params={"group_name": self.group_name}, timeout=3)
            result = r.json()
            if result.get('code') == 200:
                self.word = result['data'].get('word')
                return self.word
        except:
            pass
        return None
    
    def submit_description(self, desc: str) -> tuple:
        """提交描述"""
        try:
            r = requests.post(f"{BASE_URL}/api/describe",
                            json={"group_name": self.group_name, "description": desc}, timeout=3)
            result = r.json()
            return result.get('code') == 200 and '成功' in result.get('message', ''), result.get('message', '')
        except Exception as e:
            return False, str(e)
    
    def submit_vote(self, target: str) -> tuple:
        """提交投票"""
        try:
            r = requests.post(f"{BASE_URL}/api/vote",
                            json={"voter_group": self.group_name, "target_group": target}, timeout=3)
            result = r.json()
            return result.get('code') == 200, result.get('message', '')
        except Exception as e:
            return False, str(e)
    
    def display_status(self, status: dict):
        """显示当前状态"""
        self.clear_screen()
        
        print(f"╔{'═'*48}╗")
        print(f"║  🎮 谁是卧底 - 游戏方终端  [{self.group_name}]".ljust(49) + "║")
        print(f"╠{'═'*48}╣")
        
        # 我的词语
        if self.word:
            print(f"║  📝 我的词语: {self.word}".ljust(49) + "║")
        
        # 游戏状态
        status_map = {
            'waiting': '⏳ 等待注册',
            'registered': '✅ 已注册，等待开始',
            'word_assigned': '📋 词语已分配，等待开始回合',
            'describing': '🎤 描述阶段',
            'voting': '🗳️ 投票阶段',
            'round_end': '🔄 回合结束',
            'game_end': '🏁 游戏结束'
        }
        game_status = status.get('status', 'waiting')
        print(f"║  状态: {status_map.get(game_status, game_status)}".ljust(49) + "║")
        print(f"║  回合: 第 {status.get('round', 0)} 轮".ljust(49) + "║")
        
        # 倒计时
        if game_status == 'describing':
            speaker_time = status.get('speaker_remaining_seconds')
            if speaker_time is not None:
                print(f"║  ⏱️ 当前发言者剩余: {speaker_time} 秒".ljust(49) + "║")
        
        remaining = status.get('remaining_seconds')
        if remaining is not None:
            print(f"║  ⏱️ 阶段剩余时间: {remaining} 秒".ljust(49) + "║")
        
        print(f"╠{'═'*48}╣")
        
        # 发言顺序
        if game_status in ['describing', 'voting']:
            order = status.get('describe_order', [])
            current = status.get('current_speaker', '')
            current_idx = status.get('current_speaker_index', 0)
            
            print(f"║  📋 发言顺序:".ljust(50) + "║")
            for i, name in enumerate(order):
                if name in status.get('eliminated_groups', []):
                    marker = "❌"
                elif game_status == 'describing' and i < current_idx:
                    marker = "✅"
                elif name == current and game_status == 'describing':
                    marker = "👉"
                else:
                    marker = "⬜"
                
                me_marker = " (我)" if name == self.group_name else ""
                print(f"║     {marker} {name}{me_marker}".ljust(50) + "║")
        
        # 显示当前回合的描述
        descriptions = status.get('descriptions', [])
        if descriptions:
            print(f"╠{'═'*48}╣")
            print(f"║  💬 本回合描述:".ljust(50) + "║")
            for desc in descriptions:
                group = desc.get('group', '???')
                text = desc.get('description', '')
                # 截断过长的描述
                if len(text) > 30:
                    text = text[:27] + "..."
                me_marker = " ←我" if group == self.group_name else ""
                print(f"║    [{group}]{me_marker}: {text}".ljust(50) + "║")
        
        # 淘汰的组
        eliminated = status.get('eliminated_groups', [])
        if eliminated:
            print(f"╠{'═'*48}╣")
            print(f"║  💀 已淘汰: {', '.join(eliminated)}".ljust(49) + "║")
        
        print(f"╚{'═'*48}╝")
    
    def wait_for_game_start(self):
        """等待游戏开始"""
        print("\n等待主持方开始游戏...")
        while True:
            status = self.get_status()
            if status.get('status') in ['word_assigned', 'describing']:
                return True
            if status.get('status') == 'game_end':
                return False
            time.sleep(1)
    
    def wait_for_my_turn(self):
        """等待轮到自己发言，同时显示状态"""
        while True:
            status = self.get_status()
            self.display_status(status)
            
            if status.get('status') != 'describing':
                return status.get('status')
            
            if status.get('current_speaker') == self.group_name:
                return 'my_turn'
            
            print(f"\n等待 {status.get('current_speaker')} 发言中...")
            time.sleep(2)
    
    def run(self):
        """运行客户端"""
        self.print_header(f"谁是卧底 - 游戏方客户端")
        print(f"服务器: {BASE_URL}")
        print(f"组名: {self.group_name}")
        
        # 注册
        if not self.register():
            return
        
        # 等待游戏开始
        if not self.wait_for_game_start():
            print("游戏已结束")
            return
        
        # 获取词语
        self.word = self.get_word()
        if self.word:
            print(f"\n🎯 你的词语是: 【{self.word}】")
            print("请记住你的词语！")
            input("按Enter继续...")
        
        # 游戏主循环
        while True:
            status = self.get_status()
            game_status = status.get('status')
            
            if game_status == 'game_end':
                self.display_status(status)
                print("\n🏁 游戏结束！")
                if self.group_name in status.get('eliminated_groups', []):
                    print("😢 你被淘汰了")
                else:
                    print("🎉 你存活到了最后！")
                break
            
            elif game_status == 'describing':
                # 等待轮到自己
                result = self.wait_for_my_turn()
                
                if result == 'my_turn':
                    status = self.get_status()
                    self.display_status(status)
                    
                    speaker_time = status.get('speaker_remaining_seconds', 30)
                    print(f"\n👉 轮到你发言了！剩余 {speaker_time} 秒")
                    print(f"你的词语是: 【{self.word}】")
                    
                    desc = input("请输入你的描述: ").strip()
                    if not desc:
                        desc = "我选择沉默"
                    
                    success, msg = self.submit_description(desc)
                    if success:
                        print(f"✓ 描述提交成功!")
                    else:
                        print(f"✗ 提交失败: {msg}")
                    
                    time.sleep(1)
                
                elif result == 'voting':
                    continue
                else:
                    time.sleep(1)
            
            elif game_status == 'voting':
                self.display_status(status)
                
                # 获取可投票的组
                active = status.get('active_groups', [])
                others = [g for g in active if g != self.group_name]
                
                if others:
                    print(f"\n🗳️ 投票阶段！剩余 {status.get('remaining_seconds', 120)} 秒")
                    print("可投票的组:")
                    for i, g in enumerate(others, 1):
                        print(f"  {i}. {g}")
                    
                    choice = input(f"请输入要投票的组名或序号: ").strip()
                    
                    # 支持输入序号
                    if choice.isdigit():
                        idx = int(choice) - 1
                        if 0 <= idx < len(others):
                            choice = others[idx]
                    
                    if choice in others:
                        success, msg = self.submit_vote(choice)
                        if success:
                            print(f"✓ 投票成功: {self.group_name} → {choice}")
                        else:
                            print(f"✗ 投票失败: {msg}")
                    else:
                        print("无效的选择")
                
                # 等待投票阶段结束
                print("\n等待其他人投票...")
                while True:
                    s = self.get_status()
                    if s.get('status') != 'voting':
                        break
                    time.sleep(2)
            
            elif game_status == 'round_end':
                self.display_status(status)
                print("\n回合结束，等待主持方开始下一轮...")
                while True:
                    s = self.get_status()
                    if s.get('status') in ['describing', 'game_end']:
                        break
                    time.sleep(2)
            
            elif game_status == 'word_assigned':
                self.display_status(status)
                print("\n等待主持方开始第一回合...")
                time.sleep(2)
            
            else:
                time.sleep(1)
        
        print("\n游戏结束，感谢参与！")
        input("按Enter退出...")


def main():
    print("="*50)
    print("  谁是卧底 - 交互式游戏方客户端")
    print("="*50)
    
    # 测试连接
    try:
        r = requests.get(f"{BASE_URL}/api/status", timeout=3)
        if r.status_code != 200:
            print("✗ 服务器连接失败")
            return
        print("✓ 服务器连接成功")
    except:
        print(f"✗ 无法连接服务器 {BASE_URL}")
        print("请确保 backend.py 已启动")
        return
    
    # 输入组名
    group_name = input("\n请输入你的组名: ").strip()
    if not group_name:
        print("组名不能为空")
        return
    
    client = InteractiveClient(group_name)
    client.run()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n已退出")
