"""
src/agent_core.py
MindIsle（心屿）多智能体核心逻辑 —— 北邮 ACPs 协议安全一票否决实现

遵循北邮 ACPs (Agent Collaboration Protocols) 规范：
  1. 安全评估 Agent 优先独立运行，拥有最高优先级；
  2. 任一安全评估 Agent 报告高危风险，即可行使“一票否决”（veto），
     立即终止正常共情 / 疏导流程，切换为应急响应（预警 + 心理援助热线）。
"""

from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# 模块级常量（可在实例初始化时按需覆盖）
# ---------------------------------------------------------------------------

# 24 小时全国心理援助热线
EMERGENCY_HOTLINE: str = "400-161-9995"

# 高危关键词：命中任意一个即触发安全评估 Agent 的一票否决
HIGH_RISK_KEYWORDS: List[str] = [
    "想死",
    "自杀",
    "跳楼",
    "割腕",
    "被打了",
    "霸凌",
]


class ACPSMultiAgentOrchestrator:
    """
    遵循北邮 ACPs (Agent Collaboration Protocols) 规范的多智能体协调器。

    编排顺序：
      [Step 1] 安全评估 Agent 优先独立运行（拥有“一票否决”权）；
      [Step 2] 若 veto=False，再由共情 Agent 与疏导 Agent 协作产出正常陪伴回复。

    主要接口：
      - check_safety(user_text)     : 安全评估 Agent，输出风险判定结构与 veto 标志
      - process_dialogue(user_text) : 对外主入口，返回统一对话结果（含 is_vetoed 标志）
    """

    # 触发否决后的应急话术模板（{hotline} 会被替换为实例配置的热线）
    EMERGENCY_RESPONSE_TEMPLATE: str = (
        "听到你现在经历的痛苦，我非常关切你。你并不孤单，"
        "请立刻寻求老师、家长或拨打 24 小时全国心理援助热线：{hotline}。"
    )

    # 正常流程下的共情陪伴话术
    NORMAL_RESPONSE: str = (
        "收到你的倾诉。我知道遇到这种情况确实会让人心情沮丧，"
        "但我们可以一起面对它，你想聊聊具体是什么事吗？"
    )

    def __init__(
        self,
        high_risk_keywords: Optional[List[str]] = None,
        emergency_hotline: str = EMERGENCY_HOTLINE,
    ) -> None:
        """
        :param high_risk_keywords: 高危关键词表，默认使用模块级 HIGH_RISK_KEYWORDS
        :param emergency_hotline:  24 小时心理援助热线，默认 400-161-9995
        """
        self.high_risk_keywords: List[str] = (
            list(high_risk_keywords) if high_risk_keywords else list(HIGH_RISK_KEYWORDS)
        )
        self.emergency_hotline: str = emergency_hotline

    # ------------------------------------------------------------------
    # [ACPs] 安全评估 Agent（优先级最高 · 一票否决权）
    # ------------------------------------------------------------------
    def check_safety(self, user_text: str) -> Dict[str, Any]:
        """
        [1] 安全评估智能体优先独立运行（符合 ACPs 安全一票否决规则）。

        :param user_text: 用户输入文本
        :return: 安全评估结果，结构如下：
            {
                "is_risk":    bool,          # 是否命中高危风险
                "risk_level": str,           # "red" | "green"
                "reason":     str,           # 命中原因说明（未命中为空串）
                "veto":       bool,          # True=触发安全一票否决
                "keyword":    Optional[str], # 命中的高危关键词（未命中为 None）
            }
        """
        for kw in self.high_risk_keywords:
            if kw in user_text:
                return {
                    "is_risk": True,
                    "risk_level": "red",
                    "reason": f"触发高危词汇: {kw}",
                    "veto": True,            # 触发一票否决
                    "keyword": kw,
                }
        return {
            "is_risk": False,
            "risk_level": "green",
            "reason": "",
            "veto": False,
            "keyword": None,
        }

    # ------------------------------------------------------------------
    # 对外主入口：安全评估 → 一票否决 / 正常共情疏导
    # ------------------------------------------------------------------
    def process_dialogue(self, user_text: str) -> Dict[str, Any]:
        """
        处理一段用户输入，返回统一对话结果（对外主入口）。

        :param user_text: 用户输入文本
        :return: 对话结果，结构如下：
            {
                "risk_level":    str,  # "red" | "green"
                "is_vetoed":     bool, # True 表示被安全评估一票否决
                "response_text": str,  # 系统回复（应急话术或共情陪伴）
                "action":        str,  # "TRIGGER_EMERGENCY_POPUP" | "NORMAL_TALK"
                "reason":        str,  # 否决原因（未否决时为空串）
            }
        """
        # 第一步：安全评估 Agent 优先独立运行（一票否决拥有最高优先级）
        safety_result = self.check_safety(user_text)

        if safety_result["veto"]:
            # 命中高危风险：立即终止正常疏导流程，返回应急响应（预警 + 24 小时热线）
            return {
                "risk_level": "red",
                "is_vetoed": True,
                "response_text": self.EMERGENCY_RESPONSE_TEMPLATE.format(
                    hotline=self.emergency_hotline
                ),
                "action": "TRIGGER_EMERGENCY_POPUP",
                "reason": safety_result["reason"],
            }

        # 第二步：正常的多智能体共情陪伴与疏导回复
        # （规则版实现；接入大模型后可由共情 Agent / 疏导 Agent 并行协作生成）
        return {
            "risk_level": safety_result["risk_level"],
            "is_vetoed": False,
            "response_text": self.NORMAL_RESPONSE,
            "action": "NORMAL_TALK",
            "reason": "",
        }
