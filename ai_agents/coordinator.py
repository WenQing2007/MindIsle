"""
ai_agents/coordinator.py
MindIsle（心屿）多智能体协商与路由协调器

结合后端 backend/risk.py 的四级风险等级（green/yellow/orange/red）：
  - 安全评估智能体优先独立运行，高危（red）触发「一票否决」（veto），
    立即中断一切正常流程，切换为应急响应（24 小时心理援助热线）；
  - 按风险等级将输入路由给 共情陪伴 / CBT 等专业智能体，组织一次
    ACPs/AIP 内部协商（并行讨论 → 交叉校验 → 整合输出）；
  - 自动记录 AIP 报文协作日志（get_collaboration_log），
    支撑后台协作日志与心理报告生成。

对外主入口：MultiAgentCoordinator.process_dialogue(user_text)
与 src/agent_core.py 返回结构兼容（可作 drop-in 替换）：
  { risk_level, risk_score, risk_matched, is_vetoed,
    response_text, action, reason, routed_agents, hotline }
"""
from __future__ import annotations

import os
import sys
from typing import Any, Callable, Dict, List, Optional

# 兼容两种运行方式：
#   包导入   python -c "from ai_agents.coordinator import ..."
#   直接运行 python ai_agents/coordinator.py
try:
    from ai_agents.protocols import AIPMessage, MsgType, new_message
    from ai_agents.prompts import (
        CBT_AGENT_PROMPT,
        COMPANION_AGENT_PROMPT,
        SAFETY_AGENT_PROMPT,
    )
except ImportError:  # 兜底：直接运行脚本时，脚本所在目录已在 sys.path
    from protocols import AIPMessage, MsgType, new_message
    from prompts import (
        CBT_AGENT_PROMPT,
        COMPANION_AGENT_PROMPT,
        SAFETY_AGENT_PROMPT,
    )

# ---------------------------------------------------------------------------
# 常量与路由表
# ---------------------------------------------------------------------------
EMERGENCY_HOTLINE: str = "400-161-9995"   # 24 小时全国心理援助热线
COORDINATOR: str = "coordinator"           # 协调智能体
VETO_AGENT: str = "safety_assessor"        # 安全评估智能体（一票否决）

# 风险等级 → 参与协商的智能体路由表
RISK_ROUTING: Dict[str, List[str]] = {
    "green": ["empathy_companion"],                                # 低：共情陪伴
    "yellow": ["empathy_companion", "cognitive_behavior"],         # 中：共情 + CBT
    "orange": ["empathy_companion", "cognitive_behavior"],         # 较高：共情 + CBT（并通知教师）
    "red": [VETO_AGENT],                                           # 高：仅安全评估，一票否决
}

# 风险等级 → 系统动作（与 backend/requirements.py RISK_INTERVENTION 对齐）
ACTION_MAP: Dict[str, str] = {
    "green": "NORMAL_TALK",
    "yellow": "WARN_TEACHER_ANONYMOUS",
    "orange": "NOTIFY_TEACHER",
    "red": "TRIGGER_EMERGENCY_POPUP",
}

# 正常流程的分等级兜底话术（接入 LLM 后由智能体生成，此处保证系统兜底可用）
RESPONSE_TEMPLATES: Dict[str, str] = {
    "green": (
        "收到你的分享！听上去你今天的心情还挺不错的，"
        "愿意的话多和我说说吗？"
    ),
    "yellow": (
        "谢谢你愿意告诉我这些。遇到这种情况确实会让人心里沉甸甸的，"
        "别给自己太大压力。试着先做几次深呼吸放松一下，我们慢慢聊，好吗？"
    ),
    "orange": (
        "谢谢你信任我。被这样对待一定很难受，这不是你的错。"
        "请一定要把这件事告诉信任的老师、家长或心理老师，你不需要一个人扛着。"
        "愿意的话，能和我说说发生了什么吗？"
    ),
}

# ---------------------------------------------------------------------------
# 本地兜底风险评估（仅当 backend/risk.py 无法导入时启用）
# 关键词表与 backend/risk.py 的 KEYWORD_MAP 保持一致。
# ---------------------------------------------------------------------------
_LOCAL_KEYWORDS: Dict[str, List[str]] = {
    "green": ["开心", "高兴", "很好", "不错", "喜欢", "满意", "快乐", "幸福",
              "棒", "还行", "挺好", "没事", "哈哈", "嘻嘻", "谢谢", "感激"],
    "yellow": ["压力", "难过", "焦虑", "烦恼", "担心", "害怕考试", "累",
               "心累", "郁闷", "烦躁", "不开心", "不太好", "紧张", "迷茫",
               "孤独", "失落", "沮丧", "忧愁"],
    "orange": ["欺凌", "欺负", "被欺负", "被打", "挨打", "讨厌", "恨", "恐惧",
               "害怕", "怕", "威胁", "勒索", "孤立", "排挤", "家庭暴力",
               "被骂", "人身攻击"],
    "red": ["自杀", "不想活", "想死", "跳楼", "割腕", "结束生命", "活不下去",
            "了断", "去死", "自伤", "自残"],
}
_LOCAL_ORDER: List[str] = ["green", "yellow", "orange", "red"]
_LOCAL_SCORES: Dict[str, float] = {"green": 0.1, "yellow": 0.35, "orange": 0.7, "red": 1.0}


def _local_assess(text: str) -> Dict[str, Any]:
    """与 backend/risk.py::assess 等价的本地兜底实现。"""
    text = text or ""
    best_level, best_index = "green", 0
    all_matched: List[str] = []
    for level in _LOCAL_ORDER:
        hits = [kw for kw in _LOCAL_KEYWORDS[level] if kw in text]
        if hits:
            all_matched.extend(hits)
            idx = _LOCAL_ORDER.index(level)
            if idx > best_index:
                best_index, best_level = idx, level
    return {
        "level": best_level,
        "level_db": {"green": "low", "yellow": "medium", "orange": "high", "red": "critical"}[best_level],
        "score": _LOCAL_SCORES[best_level],
        "matched": all_matched,
        "matched_level": best_level,
    }


def _local_is_critical(level: str) -> bool:
    return level == "red"


def _load_risk_api() -> tuple[Callable[[str], Dict[str, Any]], Callable[[str], bool]]:
    """优先加载后端 backend/risk.py 的风险评估接口，失败则退回本地兜底实现。

    加载顺序：
      1. from backend.risk import assess, is_critical  （项目根下的包导入）
      2. import risk                                   （backend/ 已被加入 sys.path）
      3. 模块内 _local_assess / _local_is_critical     （最后兜底）
    """
    try:
        from backend.risk import assess, is_critical
        return assess, is_critical
    except ImportError:
        pass

    # 直接运行脚本（python ai_agents/coordinator.py）时补全 sys.path
    _cur = os.path.dirname(os.path.abspath(__file__))
    _project_root, _backend_dir = os.path.dirname(_cur), os.path.join(os.path.dirname(_cur), "backend")
    for p in (_project_root, _backend_dir):
        if p not in sys.path:
            sys.path.insert(0, p)

    try:
        import risk as _risk
        return _risk.assess, _risk.is_critical
    except ImportError:
        return _local_assess, _local_is_critical


_ASSESS, _IS_CRITICAL = _load_risk_api()

class MultiAgentCoordinator:
    """遵循北邮 ACPs 的多智能体协商与路由协调器。

    流水线：
      1) 安全评估智能体优先独立运行（结合 backend/risk.py）；
      2) 高危（red）→ 一票否决：中断一切流程，输出应急响应 + 援助热线；
      3) 其余等级 → 按 RISK_ROUTING 路由给各专业智能体，
         组织 ACPs/AIP 协商（并行讨论 → 交叉校验 → 整合）；
      4) 记录全量 AIP 报文协作日志，供后台协作日志 / 报告生成使用。
    """

    # 触发一票否决后的应急话术模板（{hotline} 会被替换为实例配置的热线）
    EMERGENCY_RESPONSE_TEMPLATE: str = (
        "听到你现在经历的痛苦，我非常关切你。你并不孤单，"
        "请立刻寻求老师、家长或拨打 24 小时全国心理援助热线：{hotline}。"
    )

    def __init__(
        self,
        emergency_hotline: str = EMERGENCY_HOTLINE,
        age: int = 12,
        risk_assessor: Optional[Callable[[str], Dict[str, Any]]] = None,
        risk_is_critical: Optional[Callable[[str], bool]] = None,
        max_negotiation_rounds: int = 2,
    ) -> None:
        """
        :param emergency_hotline:       24 小时心理援助热线
        :param age:                     学生年龄段（6-18，用于 Prompt 渲染）
        :param risk_assessor:           自定义风险评估函数 f(text)->dict（默认 backend.risk.assess）
        :param risk_is_critical:        自定义高危判定函数 f(level)->bool（默认 backend.risk.is_critical）
        :param max_negotiation_rounds:  协商最大轮数（AIP 循环上限）
        """
        self.emergency_hotline: str = emergency_hotline
        self.age: int = age
        self.assess_risk_fn: Callable[[str], Dict[str, Any]] = risk_assessor or _ASSESS
        self.is_critical_fn: Callable[[str], bool] = risk_is_critical or _IS_CRITICAL
        self.max_negotiation_rounds: int = max_negotiation_rounds

        self.last_result: Optional[Dict[str, Any]] = None       # 最近一次对话结果
        self.collaboration_log: List[AIPMessage] = []           # AIP 报文协作日志

    # ------------------------------------------------------------------
    # 1. 风险评估（结合 backend/risk.py 的四级风险）
    # ------------------------------------------------------------------
    def assess_risk(self, text: str) -> Dict[str, Any]:
        """调用风险评估接口，返回 {level, level_db, score, matched, ...}。"""
        return dict(self.assess_risk_fn(text or ""))

    # ------------------------------------------------------------------
    # 2. 分发路由
    # ------------------------------------------------------------------
    def dispatch(self, risk_level: str) -> List[str]:
        """按风险等级返回参与协商的智能体列表（路由表见 RISK_ROUTING）。"""
        return list(RISK_ROUTING.get(risk_level, RISK_ROUTING["green"]))

    # 别名：与 ACPs「消息路由」语义对齐
    route = dispatch

    def decide_action(self, risk_level: str) -> str:
        """根据风险等级决策系统动作（与 requirements.py RISK_INTERVENTION 对齐）。"""
        return ACTION_MAP.get(risk_level, "NORMAL_TALK")

    # ------------------------------------------------------------------
    # 3. ACPs/AIP 协商（生成内部协作报文）
    # ------------------------------------------------------------------
    def _agent_reply(self, agent: str, risk_level: str, user_text: str) -> Dict[str, Any]:
        """各专业智能体的规则版建议载荷。

        接入 LLM 后，可在此处调用大模型并返回其结构化 JSON；
        当前不依赖网络，保证系统在无模型环境下仍可完整跑通协商流程。
        """
        if agent == "empathy_companion":
            return {
                "role": "empathy_companion",
                "emotion_reflection": "你现在的情绪被看见了，你愿意说出来已经很有勇气。",
                "companion_response": RESPONSE_TEMPLATES.get(risk_level, RESPONSE_TEMPLATES["green"]),
                "gentle_guidance": "做几次深呼吸，然后告诉我更多细节，我会一直陪着你。",
                "risk_alert": risk_level,
                "confidence": 0.9,
            }
        if agent == "cognitive_behavior":
            return {
                "role": "cognitive_behavior",
                "core_belief": "可能存在的自动化思维：\"这件事我应付不了\"。",
                "cognitive_distortions": ["灾难化", "以偏概全"],
                "reframed_thought": "“我暂时还没学会，不代表我永远做不到。”",
                "action_plan": ["把担心的事写下来并划掉可控的部分",
                                "把大目标拆成今天能完成的 1 小步"],
                "risk_alert": risk_level,
                "confidence": 0.85,
            }
        return {"role": agent, "note": "规则版占位输出", "risk_alert": risk_level}



    def negotiate(
        self,
        user_text: str,
        risk: Dict[str, Any],
        session_id: str = "",
    ) -> List[AIPMessage]:
        """组织一次 ACPs/AIP 内部协商，返回完整报文列表。

        流程：协调→安全评估(优先) → [高危:VETO_INTERRUPT 广播中断]
              → 协调→各专业智能体并行讨论 → 交叉校验 → 整合输出。
        """
        msgs: List[AIPMessage] = []
        risk_level: str = risk.get("level", "green")
        routed: List[str] = self.dispatch(risk_level)
        risk_hint = f"level={risk_level}, score={risk.get('score', 0.0)}"

        # ---- Step 1：安全评估智能体优先独立运行 ----
        msgs.append(new_message(
            COORDINATOR, VETO_AGENT, MsgType.DISCUSS_REQUEST,
            payload={
                "user_text": user_text,
                "risk_hint": risk_hint,
                "hotline": self.emergency_hotline,
                "prompt": SAFETY_AGENT_PROMPT.format(
                    age=self.age, user_text=user_text,
                    risk_hint=risk_hint, hotline=self.emergency_hotline,
                ),
            },
            session_id=session_id,
        ))

        # ---- Step 2：高危 → 一票否决，立即中断，无需进入专业智能体讨论 ----
        if risk_level == "red":
            reason = (", ".join(risk.get("matched", [])) or "命中高危风险信号")
            emergency_text = self.EMERGENCY_RESPONSE_TEMPLATE.format(
                hotline=self.emergency_hotline
            )
            veto_msg = new_message(
                VETO_AGENT, "all", MsgType.VETO_INTERRUPT,
                payload={
                    "reason": f"命中高危信号: {reason}",
                    "matched_signals": risk.get("matched", []),
                    "emergency_text": emergency_text,
                    "hotline": self.emergency_hotline,
                },
                session_id=session_id,
            )
            msgs.append(veto_msg)
            msgs.append(new_message(
                COORDINATOR, "all", MsgType.ROUTE_NOTIFY,
                payload={"instruction": "VETO_CRISIS", "reason": reason},
                session_id=session_id,
                reply_to=veto_msg.message_id,
            ))
            return msgs

        # ---- Step 3：协调智能体向各专业智能体发起并行讨论 ----
        agent_prompts = {
            "empathy_companion": COMPANION_AGENT_PROMPT,
            "cognitive_behavior": CBT_AGENT_PROMPT,
        }
        for agent in routed:
            prompt = agent_prompts.get(agent, "")
            if prompt:
                prompt = prompt.format(
                    age=self.age, user_text=user_text, risk_level=risk_level,
                )
            req = new_message(
                COORDINATOR, agent, MsgType.DISCUSS_REQUEST,
                payload={
                    "user_text": user_text,
                    "risk_level": risk_level,
                    "prompt": prompt,
                },
                session_id=session_id,
            )
            msgs.append(req)
            msgs.append(new_message(
                agent, COORDINATOR, MsgType.DISCUSS_RESPONSE,
                payload=self._agent_reply(agent, risk_level, user_text),
                session_id=session_id,
                reply_to=req.message_id,
            ))

        # ---- Step 4：交叉校验（yellow 及以上、且路由不少于两个智能体时执行） ----
        if risk_level in ("yellow", "orange") and len(routed) >= 2:
            for agent in routed:
                others = [a for a in routed if a != agent]
                check = new_message(
                    COORDINATOR, agent, MsgType.CROSS_CHECK_REQUEST,
                    payload={
                        "cross_check_targets": others,
                        "risk_level": risk_level,
                    },
                    session_id=session_id,
                )
                msgs.append(check)
                msgs.append(new_message(
                    agent, COORDINATOR, MsgType.CROSS_CHECK_RESPONSE,
                    payload={
                        "status": "agreed",
                        "note": f"{agent} 已复核其他智能体建议，无安全冲突",
                    },
                    session_id=session_id,
                    reply_to=check.message_id,
                ))

        # ---- Step 5：协调智能体整合统一回复 ----
        msgs.append(new_message(
            COORDINATOR, "all", MsgType.INTEGRATE_RESPONSE,
            payload={
                "final_response": self.build_response(user_text, risk_level),
                "action": self.decide_action(risk_level),
                "risk_level": risk_level,
                "routed_agents": routed,
            },
            session_id=session_id,
        ))
        return msgs

    # ------------------------------------------------------------------
    # 4. 统一回复生成
    # ------------------------------------------------------------------
    def build_response(self, user_text: str, risk_level: str) -> str:
        """按风险等级生成最终回复（高危输出应急话术，其余输出分级兜底话术）。"""
        if risk_level == "red":
            return self.EMERGENCY_RESPONSE_TEMPLATE.format(
                hotline=self.emergency_hotline
            )
        return RESPONSE_TEMPLATES.get(risk_level, RESPONSE_TEMPLATES["green"])

    # ------------------------------------------------------------------
    # 5. 对外主入口
    # ------------------------------------------------------------------
    def process_dialogue(
        self, user_text: str, session_id: str = ""
    ) -> Dict[str, Any]:
        """处理一段用户输入，返回统一对话结果（对外主入口）。

        返回结构（与 src/agent_core.py 兼容，可 drop-in 替换）：
            {
                "risk_level":    str,   # green | yellow | orange | red
                "risk_score":    float, # 0.0 ~ 1.0
                "risk_matched":  list,  # 命中的风险信号词
                "is_vetoed":     bool,  # True=安全评估一票否决
                "response_text": str,   # 系统回复（应急话术或分级兜底话术）
                "action":        str,   # NORMAL_TALK | WARN_TEACHER_ANONYMOUS
                                       #  | NOTIFY_TEACHER | TRIGGER_EMERGENCY_POPUP
                "reason":        str,   # 否决原因（未否决时为空串）
                "routed_agents": list,  # 参与本轮协商的智能体列表
                "hotline":       str|None,  # 高危时返回 24 小时援助热线
            }
        """
        text = (user_text or "").strip()
        if not text:
            return {
                "risk_level": "green",
                "risk_score": 0.0,
                "risk_matched": [],
                "is_vetoed": False,
                "response_text": "看起来你还没有说内容，我在听，慢慢说就好。",
                "action": "NORMAL_TALK",
                "reason": "",
                "routed_agents": self.dispatch("green"),
                "hotline": None,
            }

        # 1) 风险评估（结合 backend/risk.py：green/yellow/orange/red）
        risk = self.assess_risk(text)
        risk_level: str = risk.get("level", "green")

        # 2) 一票否决判定（风险等级为 red，或风险模块判定为 critical）
        is_vetoed: bool = (risk_level == "red") or self.is_critical_fn(risk_level)

        # 3) 组织 ACPs/AIP 协商，记录协作日志
        messages = self.negotiate(text, risk, session_id=session_id)
        self.collaboration_log = messages

        # 4) 整合输出
        reason = ""
        if is_vetoed:
            reason = "命中高危信号: " + (", ".join(risk.get("matched", [])) or "高危风险判定")

        result: Dict[str, Any] = {
            "risk_level": risk_level,
            "risk_score": risk.get("score", 0.0),
            "risk_matched": risk.get("matched", []),
            "is_vetoed": is_vetoed,
            "response_text": self.build_response(text, risk_level),
            "action": self.decide_action(risk_level),
            "reason": reason,
            "routed_agents": self.dispatch(risk_level),
            "hotline": self.emergency_hotline if is_vetoed else None,
        }
        self.last_result = result
        return result

    # ------------------------------------------------------------------
    # 6. AIP 协作日志（供后台协作日志 / 报告生成使用）
    # ------------------------------------------------------------------
    def get_collaboration_log(self) -> List[Dict[str, Any]]:
        """返回最近一次协商产生的全部 AIP 报文（dict 形式，JSON 友好）。"""
        return [msg.to_dict() for msg in self.collaboration_log]


# ---------------------------------------------------------------------------
# 演示入口
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    coordinator = MultiAgentCoordinator()
    samples = [
        "今天考试考了 100 分，好开心！",
        "最近压力好大，晚上经常睡不着，有点难过。",
        "我被同学欺负了，很害怕去学校。",
        "我真的不想活了，感觉活着没意思。",
    ]
    print("=" * 72)
    for text in samples:
        result = coordinator.process_dialogue(text, session_id="demo")
        print(f"[{result['risk_level']:>6s}] veto={result['is_vetoed']}  "
              f"action={result['action']}")
        print(f"  输入 : {text}")
        print(f"  回复 : {result['response_text']}")
        print(f"  路由 : {result['routed_agents']}  命中: {result['risk_matched']}")
        print(f"  协作日志 : {len(coordinator.get_collaboration_log())} 条 AIP 报文")
        print("-" * 72)

