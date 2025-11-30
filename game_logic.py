"""
游戏逻辑模块
负责游戏状态管理、投票判定、得分计算等核心逻辑
"""
import random
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum


# 配置常量
MAX_GROUPS = 5  # 最大组数
DESCRIBE_TIMEOUT = 180  # 描述阶段总超时时间（秒）
VOTE_TIMEOUT = 120  # 投票阶段超时时间（秒）
SPEAKER_TIMEOUT = 30  # 每个人发言超时时间（秒）


class GameStatus(Enum):
    """游戏状态枚举"""
    WAITING = "waiting"  # 等待注册
    REGISTERED = "registered"  # 已注册，等待开始
    WORD_ASSIGNED = "word_assigned"  # 词语已分配
    DESCRIBING = "describing"  # 描述阶段
    VOTING = "voting"  # 投票阶段
    ROUND_END = "round_end"  # 回合结束
    GAME_END = "game_end"  # 游戏结束


class GameLogic:
    """游戏逻辑核心类"""
    
    def __init__(self):
        self.groups: Dict[str, Dict] = {}  # 组名 -> 组信息
        self.game_status = GameStatus.WAITING
        self.undercover_group: Optional[str] = None  # 卧底组名
        self.undercover_word: str = ""  # 卧底词
        self.civilian_word: str = ""  # 平民词
        self.current_round = 0  # 当前回合数
        self.describe_order: List[str] = []  # 描述顺序
        self.current_speaker_index: int = 0  # 当前发言者索引
        self.descriptions: Dict[int, List[Dict]] = {}  # 每回合的描述 {round: [{group, desc, time}]}
        self.votes: Dict[int, Dict[str, str]] = {}  # 每回合的投票 {round: {voter: target}}
        self.eliminated_groups: List[str] = []  # 已淘汰的组
        self.scores: Dict[str, int] = {}  # 得分 {group: score}
        self.reports: List[Dict] = []  # 异常上报记录
        self.last_vote_result: Optional[Dict] = None  # 最近一次投票结果
        self.phase_deadline: Optional[datetime] = None  # 当前阶段截止时间
        self.speaker_deadline: Optional[datetime] = None  # 当前发言者截止时间
        
    def register_group(self, group_name: str) -> bool:
        """
        注册游戏组
        :param group_name: 组名
        :return: 是否注册成功
        """
        if group_name in self.groups:
            return False
        if len(self.groups) >= MAX_GROUPS:
            return False
        
        self.groups[group_name] = {
            "name": group_name,
            "role": None,  # "undercover" 或 "civilian"
            "word": "",
            "registered_time": datetime.now().isoformat()
        }
        
        if len(self.groups) > 0:
            self.game_status = GameStatus.REGISTERED
        
        return True
    
    def start_game(self, undercover_word: str, civilian_word: str) -> bool:
        """
        开始游戏，分配身份和词语
        :param undercover_word: 卧底词
        :param civilian_word: 平民词
        :return: 是否成功开始
        """
        if len(self.groups) < 3:  # 至少3组才能开始
            return False
        if self.game_status != GameStatus.REGISTERED:
            return False
        
        self.undercover_word = undercover_word
        self.civilian_word = civilian_word
        
        # 随机选择卧底
        group_names = list(self.groups.keys())
        self.undercover_group = random.choice(group_names)
        
        # 分配身份和词语
        for group_name in group_names:
            if group_name == self.undercover_group:
                self.groups[group_name]["role"] = "undercover"
                self.groups[group_name]["word"] = undercover_word
            else:
                self.groups[group_name]["role"] = "civilian"
                self.groups[group_name]["word"] = civilian_word
        
        self.current_round = 1
        self.scores = {group_name: 0 for group_name in group_names}
        self.game_status = GameStatus.WORD_ASSIGNED
        return True
    
    def start_round(self) -> List[str]:
        """
        开始新回合，随机排序
        :return: 描述顺序列表
        """
        if self.game_status not in [GameStatus.WORD_ASSIGNED, GameStatus.ROUND_END]:
            return []
        
        # 获取未淘汰的组
        active_groups = [g for g in self.groups.keys() if g not in self.eliminated_groups]
        if len(active_groups) < 2:
            return []
        
        # 随机排序
        self.describe_order = active_groups.copy()
        random.shuffle(self.describe_order)
        
        # 初始化本回合的描述和投票
        self.descriptions[self.current_round] = []
        self.votes[self.current_round] = {}
        
        # 重置发言者索引
        self.current_speaker_index = 0
        
        # 设置描述阶段截止时间
        self.phase_deadline = datetime.now() + timedelta(seconds=DESCRIBE_TIMEOUT)
        
        # 设置第一个发言者的截止时间
        self.speaker_deadline = datetime.now() + timedelta(seconds=SPEAKER_TIMEOUT)
        
        self.game_status = GameStatus.DESCRIBING
        return self.describe_order
    
    def submit_description(self, group_name: str, description: str) -> Tuple[bool, str]:
        """
        提交描述
        :param group_name: 组名
        :param description: 描述内容
        :return: (是否成功, 消息)
        """
        if self.game_status != GameStatus.DESCRIBING:
            return False, "当前不是描述阶段"
        if group_name not in self.describe_order:
            return False, "该组不在发言列表中"
        if group_name in self.eliminated_groups:
            return False, "该组已被淘汰"
        
        # 检查是否已经提交过
        for desc in self.descriptions.get(self.current_round, []):
            if desc["group"] == group_name:
                return False, "该组已提交过描述"
        
        # 检查是否轮到该组发言
        current_speaker = self.get_current_speaker()
        if current_speaker != group_name:
            return False, f"请等待，当前应由 {current_speaker} 发言"
        
        # 检查是否超时
        is_timeout = False
        if self.speaker_deadline and datetime.now() > self.speaker_deadline:
            is_timeout = True
        
        self.descriptions[self.current_round].append({
            "group": group_name,
            "description": description,
            "time": datetime.now().isoformat(),
            "timeout": is_timeout  # 标记是否超时提交
        })
        
        # 移动到下一个发言者
        self.current_speaker_index += 1
        
        # 设置下一个发言者的截止时间
        self.speaker_deadline = datetime.now() + timedelta(seconds=SPEAKER_TIMEOUT)
        
        # 检查是否所有人都提交了
        active_groups = [g for g in self.describe_order if g not in self.eliminated_groups]
        if len(self.descriptions[self.current_round]) >= len(active_groups):
            # 设置投票阶段截止时间
            self.phase_deadline = datetime.now() + timedelta(seconds=VOTE_TIMEOUT)
            self.speaker_deadline = None
            self.game_status = GameStatus.VOTING
        
        msg = "描述提交成功"
        if is_timeout:
            msg += "（超时提交）"
        return True, msg
    
    def submit_vote(self, voter_group: str, target_group: str) -> bool:
        """
        提交投票
        :param voter_group: 投票者组名
        :param target_group: 被投票者组名
        :return: 是否成功
        """
        if self.game_status != GameStatus.VOTING:
            return False
        if voter_group in self.eliminated_groups:
            return False
        if target_group in self.eliminated_groups:
            return False
        if voter_group not in self.groups:
            return False
        if target_group not in self.groups:
            return False
        if voter_group == target_group:  # 不能投自己
            return False
        
        self.votes[self.current_round][voter_group] = target_group
        return True
    
    def process_voting_result(self) -> Dict:
        """
        处理投票结果，判定淘汰和游戏状态
        :return: 投票结果信息
        """
        if self.game_status != GameStatus.VOTING:
            return {"error": "当前不在投票阶段"}
        
        round_votes = self.votes[self.current_round]
        active_groups = [g for g in self.describe_order if g not in self.eliminated_groups]
        
        # 检查是否所有人都投票了
        if len(round_votes) < len(active_groups):
            return {"error": "还有组未投票"}
        
        # 统计票数
        vote_count: Dict[str, int] = {}
        for target in round_votes.values():
            vote_count[target] = vote_count.get(target, 0) + 1
        
        # 找出得票最多的组
        max_votes = max(vote_count.values()) if vote_count else 0
        max_voted_groups = [g for g, v in vote_count.items() if v == max_votes]
        
        result = {
            "round": self.current_round,
            "vote_count": vote_count,
            "max_voted_groups": max_voted_groups,
            "max_votes": max_votes,
            "eliminated": [],
            "game_ended": False,
            "winner": None,
            "message": "",  # 提示信息
            "undercover_group": None,  # 游戏结束时揭示卧底
            "undercover_word": "",  # 卧底词
            "civilian_word": "",  # 平民词
            "final_scores": {}  # 最终得分
        }
        
        # 判定结果
        if len(max_voted_groups) == 1:
            # 情况a：票数最多的有1组，该组被淘汰
            eliminated = max_voted_groups[0]
            self.eliminated_groups.append(eliminated)
            result["eliminated"] = [eliminated]
            
            if eliminated == self.undercover_group:
                # 卧底被淘汰，游戏结束，平民胜利
                result["game_ended"] = True
                result["winner"] = "civilian"
                result["message"] = f"🎉 {eliminated} 被投出，TA是卧底！平民胜利！"
                result["undercover_group"] = self.undercover_group
                result["undercover_word"] = self.undercover_word
                result["civilian_word"] = self.civilian_word
                self.game_status = GameStatus.GAME_END
                self._calculate_scores()
                result["final_scores"] = self.scores.copy()
            else:
                # 平民被淘汰，检查剩余人数
                remaining_groups = [g for g in self.groups.keys() if g not in self.eliminated_groups]
                remaining_civilians = [g for g in remaining_groups if g != self.undercover_group]
                
                if len(remaining_civilians) <= 1:
                    # 平民只剩1组或0组，卧底胜利
                    result["game_ended"] = True
                    result["winner"] = "undercover"
                    result["message"] = f"😈 {eliminated} 是平民，被投出后平民只剩{len(remaining_civilians)}组，卧底 {self.undercover_group} 胜利！"
                    result["undercover_group"] = self.undercover_group
                    result["undercover_word"] = self.undercover_word
                    result["civilian_word"] = self.civilian_word
                    self.game_status = GameStatus.GAME_END
                    self._calculate_scores()
                    result["final_scores"] = self.scores.copy()
                else:
                    # 继续下一轮（返回第3步）
                    result["message"] = f"👋 {eliminated} 被投出，TA是平民。游戏继续，进入第 {self.current_round + 1} 轮。"
                    self.current_round += 1
                    self.game_status = GameStatus.ROUND_END
                    
        elif len(max_voted_groups) == 2:
            # 情况c：票数最多的组有2组，进入下一轮（返回第3步）
            result["message"] = f"⚖️ {' 和 '.join(max_voted_groups)} 票数相同（各{max_votes}票），无人淘汰，进入第 {self.current_round + 1} 轮。"
            self.current_round += 1
            self.game_status = GameStatus.ROUND_END
            
        elif len(max_voted_groups) >= 3:
            # 情况b：得票最多有3组或更多
            all_civilians = all(g != self.undercover_group for g in max_voted_groups)
            if all_civilians:
                # 都是平民，全部淘汰，游戏结束，卧底胜利
                self.eliminated_groups.extend(max_voted_groups)
                result["eliminated"] = max_voted_groups
                result["game_ended"] = True
                result["winner"] = "undercover"
                result["message"] = f"😈 {', '.join(max_voted_groups)} 票数相同且都是平民，全部淘汰！卧底 {self.undercover_group} 胜利！"
                result["undercover_group"] = self.undercover_group
                result["undercover_word"] = self.undercover_word
                result["civilian_word"] = self.civilian_word
                self.game_status = GameStatus.GAME_END
                self._calculate_scores()
                result["final_scores"] = self.scores.copy()
            else:
                # 包含卧底，进入下一轮
                self.current_round += 1
                self.game_status = GameStatus.ROUND_END
        
        # 清除倒计时
        self.phase_deadline = None
        self.speaker_deadline = None
        
        self.last_vote_result = result
        return result

    def add_report(self, group_name: str, report_type: str, detail: str) -> Dict:
        """记录异常报告"""
        ticket = f"RPT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{len(self.reports)+1:03d}"
        entry = {
            "ticket": ticket,
            "group": group_name or "unknown",
            "type": report_type,
            "detail": detail,
            "time": datetime.now().isoformat()
        }
        self.reports.append(entry)
        return entry
    
    def _calculate_scores(self):
        """
        计算得分
        规则：
        - 卧底胜利条件：平民只剩1组
        - 胜利分：卧底胜利时得3分
        - 生存分：每生存一轮得1分
        - 卧底得分 = 胜利分 + 生存分
        - 平民得分 = 生存分（生存的轮数）
        """
        if not self.undercover_group:
            return
        
        undercover_eliminated = self.undercover_group in self.eliminated_groups
        
        # 计算每个组的生存轮数
        # 生存轮数 = 被淘汰时的回合数，如果未被淘汰则为当前回合数
        survival_rounds: Dict[str, int] = {}
        
        for group_name in self.groups.keys():
            if group_name in self.eliminated_groups:
                # 找到该组被淘汰的回合
                eliminated_round = self._get_eliminated_round(group_name)
                survival_rounds[group_name] = eliminated_round - 1  # 被淘汰前的轮数
            else:
                # 存活到最后
                survival_rounds[group_name] = self.current_round
        
        if undercover_eliminated:
            # 卧底被淘汰，平民胜利
            # 卧底：只有生存分（被淘汰前的轮数）
            self.scores[self.undercover_group] = max(0, survival_rounds[self.undercover_group])
            
            # 平民：生存分
            for group_name in self.groups.keys():
                if group_name != self.undercover_group:
                    self.scores[group_name] = survival_rounds[group_name]
        else:
            # 卧底存活到最后，卧底胜利
            # 卧底得分 = 胜利分(3) + 生存分
            victory_bonus = 3
            self.scores[self.undercover_group] = victory_bonus + survival_rounds[self.undercover_group]
            
            # 平民：生存分
            for group_name in self.groups.keys():
                if group_name != self.undercover_group:
                    self.scores[group_name] = survival_rounds[group_name]
    
    def _get_eliminated_round(self, group_name: str) -> int:
        """获取某组被淘汰的回合数"""
        # 遍历投票结果找到该组被淘汰的回合
        if self.last_vote_result and group_name in self.last_vote_result.get("eliminated", []):
            return self.last_vote_result.get("round", self.current_round)
        # 默认返回当前回合
        return self.current_round
    
    def get_game_state(self) -> Dict:
        """获取当前游戏状态"""
        # 获取当前回合已发言的组
        described_groups = []
        if self.current_round in self.descriptions:
            described_groups = [d["group"] for d in self.descriptions[self.current_round]]
        
        # 获取当前回合已投票的组
        voted_groups = []
        if self.current_round in self.votes:
            voted_groups = list(self.votes[self.current_round].keys())
        
        return {
            "status": self.game_status.value,
            "groups": {name: {
                "name": info["name"],
                "role": info["role"],
                "eliminated": name in self.eliminated_groups
            } for name, info in self.groups.items()},
            "undercover_group": self.undercover_group if self.game_status != GameStatus.WAITING else None,
            "current_round": self.current_round,
            "describe_order": self.describe_order,
            "current_speaker": self.get_current_speaker(),
            "current_speaker_index": self.current_speaker_index,
            "described_groups": described_groups,  # 已发言的组
            "voted_groups": voted_groups,  # 已投票的组
            "eliminated_groups": self.eliminated_groups,
            "scores": self.scores,
            "descriptions": self.descriptions,
            "votes": self.votes,
            "reports": self.reports
        }

    def get_public_status(self) -> Dict:
        """面向游戏方的公开状态"""
        active_groups = [g for g in self.groups.keys() if g not in self.eliminated_groups]
        
        # 计算阶段剩余时间
        remaining_seconds = None
        if self.phase_deadline:
            delta = self.phase_deadline - datetime.now()
            remaining_seconds = max(0, int(delta.total_seconds()))
        
        # 计算当前发言者剩余时间
        speaker_remaining = None
        if self.speaker_deadline and self.game_status == GameStatus.DESCRIBING:
            delta = self.speaker_deadline - datetime.now()
            speaker_remaining = max(0, int(delta.total_seconds()))
        
        # 获取当前发言人
        current_speaker = self.get_current_speaker() if self.game_status == GameStatus.DESCRIBING else None
        
        # 获取当前回合已提交的描述（供游戏方查看）
        current_descriptions = []
        if self.current_round in self.descriptions:
            for desc in self.descriptions[self.current_round]:
                current_descriptions.append({
                    "group": desc["group"],
                    "description": desc["description"]
                })
        
        # 获取当前回合已投票的组
        voted_groups = []
        if self.current_round in self.votes:
            voted_groups = list(self.votes[self.current_round].keys())
        
        return {
            "status": self.game_status.value,
            "round": self.current_round,
            "active_groups": active_groups,
            "describe_order": self.describe_order if self.game_status in [GameStatus.DESCRIBING, GameStatus.VOTING] else [],
            "current_speaker": current_speaker,
            "current_speaker_index": self.current_speaker_index if self.game_status == GameStatus.DESCRIBING else None,
            "eliminated_groups": self.eliminated_groups,
            "remaining_seconds": remaining_seconds,
            "speaker_remaining_seconds": speaker_remaining,  # 当前发言者剩余时间
            "descriptions": current_descriptions,  # 当前回合的描述列表
            "voted_groups": voted_groups  # 已投票的组
        }
    
    def get_current_speaker(self) -> Optional[str]:
        """获取当前应该发言的组"""
        if self.game_status != GameStatus.DESCRIBING:
            return None
        if self.current_speaker_index >= len(self.describe_order):
            return None
        return self.describe_order[self.current_speaker_index]

    def get_last_result(self) -> Optional[Dict]:
        """最近一轮的公开投票结果"""
        return self.last_vote_result
    
    def get_group_word(self, group_name: str) -> Optional[str]:
        """获取指定组的词语（仅在该组查询时返回）"""
        if group_name not in self.groups:
            return None
        return self.groups[group_name].get("word")
    
    def reset_game(self):
        """重置游戏"""
        self.groups.clear()
        self.game_status = GameStatus.WAITING
        self.undercover_group = None
        self.undercover_word = ""
        self.civilian_word = ""
        self.current_round = 0
        self.describe_order = []
        self.current_speaker_index = 0
        self.descriptions.clear()
        self.votes.clear()
        self.eliminated_groups = []
        self.scores.clear()
        self.reports = []
        self.last_vote_result = None
        self.phase_deadline = None
        self.speaker_deadline = None

