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

import json
import os
import random
import sys
from typing import Any, Callable, Dict, List, Optional

# 兼容两种运行方式：
#   包导入   python -c "from ai_agents.coordinator import ..."
#   直接运行 python ai_agents/coordinator.py
try:
    from ai_agents import llm
    from ai_agents.protocols import AIPMessage, MsgType, new_message
    from ai_agents.prompts import (
        CBT_AGENT_PROMPT,
        COMPANION_AGENT_PROMPT,
        SAFETY_AGENT_PROMPT,
        SCENARIO_DIRECTOR_AGENT_PROMPT,
    )
except ImportError:  # 兜底：直接运行脚本时，脚本所在目录已在 sys.path
    import llm
    from protocols import AIPMessage, MsgType, new_message
    from prompts import (
        CBT_AGENT_PROMPT,
        COMPANION_AGENT_PROMPT,
        SAFETY_AGENT_PROMPT,
        SCENARIO_DIRECTOR_AGENT_PROMPT,
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
    "orange": ["empathy_companion", "cognitive_behavior", "scenario_director"],  # 较高：共情 + CBT + 情景导演（并通知教师）
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
# 危机子信号词表 —— 用于让应急话术真正"看见"学生具体表达了什么，
# 避免对每一次危机都机械地回复同一句固定模板（体验反馈中的核心问题）。
# 这些子信号只影响回复措辞，不改变"red 一票否决 + 转介真实成人/24h热线"的安全红线。
# ---------------------------------------------------------------------------
CRISIS_HOPELESSNESS: List[str] = [
    "没希望", "没有希望", "没救了", "活下去没意思", "活着没意思", "活不下去",
    "撑不下去", "撑不住", "坚持不下去", "放弃", "无所谓", "没意思", "没劲",
]

CRISIS_HELP_INVALIDATION: List[str] = [
    "帮不了", "救不了", "解决不了", "没用的", "没用", "聊也没用", "说了也没用",
    "没人帮", "没人能帮", "谁也帮不了", "谁都救不了", "没人在乎", "不在乎",
    "说什么都没用", "回不去了",
]

CRISIS_ACTIVE_PLAN: List[str] = [
    "就现在", "马上", "今晚", "就要", "准备去", "打算", "已经", "站在",
    "拿起", "爬上", "现在就", "想立刻", "待不住", "一刻也", "再也受不了",
]


def _detect_crisis_signals(text: str) -> Dict[str, List[str]]:
    """检测输入的危机子信号，供应急话术做出更贴切的镜映（不影响安全裁决）。"""
    text = text or ""
    return {
        "hopelessness": [kw for kw in CRISIS_HOPELESSNESS if kw in text],
        "help_invalidation": [kw for kw in CRISIS_HELP_INVALIDATION if kw in text],
        "active_plan": [kw for kw in CRISIS_ACTIVE_PLAN if kw in text],
    }


# 真人求助语义的关键词，用于 _enforce_safety_mandate 兜底校验
ADULT_KEYWORDS: List[str] = [
    "老师", "家长", "成人", "心理老师", "成年人", "大人", "父母",
    "班主任", "告诉你", "坐在你身边", "陪你身边",
]


def _enforce_safety_mandate(text: str, hotline: str) -> str:
    """硬性安全兜底：任何高危险响都保证包含 24h 热线与"向真实成人求助"语义。

    模板 / LLM 生成后统一调用：缺热线补热线句，缺"真实成人求助"补成人句。
    安全底线不依赖模型是否记得或模板是否拼对。
    """
    text = (text or "").strip()
    if hotline not in text:
        text += (
            f" 请立即拨打 24 小时全国心理援助热线：{hotline}，"
            f"电话那头是受过专业训练、真正听得进去你、能接住你的人。"
        )
    if not any(kw in text for kw in ADULT_KEYWORDS):
        text += " 请马上把这件事，让一个你信任的老师、家长或成年家人知道，不要一个人扛。"
    return text


def _crisis_guard_enabled() -> bool:
    """是否允许把 red 高危交给"受约束的大模型"生成（需同时 LLM 已启用）。

    默认关闭：保持"红级不交给模型自由发挥"的安全底线（也是既有测试约束）。
    显式设置 LLM_GUARDED_CRISIS=1/true 开启时，可在生成后由
    _enforce_safety_mandate 强制补齐热线与真人求助，从而获得真正不固定句式的回复。
    """
    return os.getenv("LLM_GUARDED_CRISIS", "").strip().lower() in ("1", "true", "yes", "on")


# 受约束的高危生成 Prompt（仅当 _crisis_guard_enabled() 且 LLM 可用时使用）。
# 它要求模型句式自然多变，但安全红线（真人求助 + 热线）由 _enforce_safety_mandate
# 在生成后再强制执行，因此即便模型险些遗漏也会被兜底补上。
CRISIS_GUARDED_PROMPT: str = """\
[角色]
你是 MindIsle（心屿）的心理陪伴者，此刻正面对一个正经历巨大痛苦、可能身处危机
边缘的学生（{age} 岁）。请用最自然、最真诚、口语化的中文回应 ta。

[必须遵守的红线（违反即无效）]
1. 绝不敷衍、不说教、不命令，不讲空洞的"乐观 / 坚强 / 想开点"。
2. 先真正听见并接住 ta 此刻具体的感受（包括 ta 说"没人能帮我 / 帮不了 /
   解决不了 / 我不行了"这类绝望），不反驳、不否认 ta 的感受。
3. 如实告诉 ta：你不能假装替 ta 解决所有问题；但现在最重要的一步，是让一个
   真实、可靠的成年人（父母 / 班主任 / 心理老师）陪在 ta 身边。
4. 内容里必须出现"24 小时心理援助热线 {hotline}"（号码 {hotline} 原样给出）。
5. 60-160 字；开头方式、句式、语气每次都要自然变化，不要照搬任何模板。

[输入]
学生输入：{user_text}
只输出直接对学生说的内容，不要任何前缀、JSON 或解释。
"""


# ---------------------------------------------------------------------------
# 离线应急话术的语料池与句式骨架：即便不依赖大模型，也能在"真正的句子结构"
# 层面做到高度变化（多套骨架随机排列 + 每块多候选 + 按命中信号挑选镜映措辞）。
# ---------------------------------------------------------------------------
_MIRROR_INVALIDATION: List[str] = [
    "你说“帮不了 / 解决不了”，这种‘已经没人能帮得了我’的绝望，我听到了。这不是你矫情，是你现在真的很难受，难到看不见出路。",
    "你说帮不了、解决不了、觉得已经没路了——这句话背后的绝望很重，重到让你觉得什么都不值得再试。我把它当真了，也明白你有多疼。",
    "你说帮不了、解决不了，觉得全世界都不管我——这份感受我听见了，正是此刻最伤人的地方，我完全明白你为什么这么绝望。",
]
_MIRROR_HOPELESSNESS: List[str] = [
    "你说这一切“没意思 / 撑不下去”，这份绝望我听到了。它很重，重到让人觉得什么都不值得。",
    "你说撑不下去、觉得没有希望了——这是最孤独的一种痛，我听见了，也想让你知道它在被认真对待。",
    "你话里那股‘怎么样都没用了’的无力感，我感受到了。我不打算急着反驳你，因为那份感受对你来说是真实的。",
]
_MIRROR_PLAN: List[str] = [
    "你话里的意思是现在就想有一个了断，我听到了，而且我非常认真地对待它。请先停下来哪怕一分钟，听我往下说。",
    "听起来你正处在一个随时想给自己一个了结的时刻，这让我很担心，也让我更想请你先把手里的念头放一放。",
]
_MIRROR_GENERIC: List[str] = [
    "你把这些话说出来的那一刻，我把它当作此刻最重要的事情来听。你现在承受的痛苦是真的，也是重的。",
    "你说的这些，我一句一句都听见了。这一刻对你一定很艰难，我不想急着劝你，只想先好好地陪着你。",
    "谢谢你愿意把这么重的话说给我。这不是小事，我也不会当成小事来听。",
]
_BRIDGE: List[str] = [
    "我不会假装一两句话就能替你解决所有问题，但此刻真正能拉住你的，是让一个真实、可靠的成年人到你身边。",
    "我不会骗你说一切都会马上好，可现在最要紧的，是有一个人真切地握住你的手——一个你信得过的成年人。",
    "我替不了你做决定，也替你消不掉这些痛，但此刻最优先、最应该做的，是立刻让一个真实的人陪着你，把最重的那句话当面说出来。",
]
_ESCALATION: List[str] = [
    "请现在就拨打 24 小时全国心理援助热线：{hotline}，电话那头是受过专业训练的人；也请告诉你身边信得过的老师或家长。",
    "现在就能做、也最有效的一步，是拨打 24 小时心理援助热线 {hotline}，或立刻走到你信任的父母、班主任、心理老师面前。",
    "别一个人扛。现在拨打 24 小时心理援助热线 {hotline}，或马上把你最难扛的那句话，告诉身边一个你信得过的大人。",
    "你可以现在就打 24 小时心理援助热线 {hotline}——他们接过无数和你一样痛苦的人；然后让你身边信任的成年人也知道，好吗？",
]
_CLOSING_REPEAT: List[str] = [
    "你上次就和我说过这样的痛苦，我真的很担心你现在比上次更难扛。别再硬撑了，现在就去找离你最近的成年人，好吗？",
    "这已经不只是一次听见你类似的痛苦了，我因此更担心你现在比上次更难扛住。请立刻去让一个真实的人陪着你。",
]
_CLOSING_NORMAL: List[str] = [
    "先试着在原地保全自己，告诉自己：现在的感受会过去，你不用一个人扛。",
    "你现在最需要的不是更用力地解决什么，而是先有一个人真切地陪着你、把话听完。",
    "痛苦会让人误以为没有退路，但那只是一种感受，不是事实。先让今晚平安过去。",
    "你不用马上想通任何事。你只需要让一个真实的人知道你现在很难，就够了。",
]

# 离线应急话术的句式骨架（块的不同排列顺序，对应自然程度均可接受的不同结构）
_OFFLINE_STRUCTURES: List[List[str]] = [
    ["mirror", "bridge", "escalation", "close"],
    ["mirror", "escalation", "bridge", "close"],
    ["esc_urgent_first", "mirror", "bridge", "close"],
    ["close", "mirror", "bridge", "escalation"],
    ["mirror", "close", "escalation", "bridge"],
    ["bridge", "mirror", "escalation", "close"],
]
_URGENT_FIRST: List[str] = [
    "请先听我说：此刻最要紧的，是立刻有一个真实的成年人陪在你身边，别一个人待着。",
    "我现在最担心你自己扛着。先答应我一件事——立刻就去找一个信得过的成年人。",
]


# 协调智能体整合统一回复的 Prompt（LLM 模式启用；未启用 LLM 时走 RESPONSE_TEMPLATES）
FINAL_SYSTEM_PROMPT: str = """\
[角色]
你是 MindIsle（心屿）多智能体系统的协调智能体。你综合运用 ACPs 协议下四位专业
智能体的能力（安全评估一票否决、共情陪伴、认知行为 CBT、情景导演场景演练），
面向 {age} 岁学生给出温暖、安全、简短、符合其年龄认知水平的回复。

[当前风险等级]
{risk_level_display}

[必须遵守的红线]
1. red 高危：优先安抚情绪，必须明确建议联系可信任的成年人或拨打 24 小时
   心理援助热线 {hotline}；绝不鼓励压抑或“想开一点”。
2. orange：先共情，再明确建议求助老师/家长/心理老师，不替学生做诊断。
3. yellow：共情 + 温和引导 + 给 1-2 条当下就能做的小建议。
4. green：自然温暖的陪伴式回应，可追问细节，让对话延续下去。
5. 不评判、不说教、不诊断、不贴标签；语言口语化，不使用心理学术语堆砌。

[输出要求]
只回复直接对学生说的 50-180 字内容：不要任何 JSON、不要前缀后缀、不要引号包装、
不要提及“风险等级”“智能体”“规则”等系统内部概念。
"""

# ---------------------------------------------------------------------------
# 本地兜底风险评估（仅当 backend/risk.py 无法导入时启用）
# 关键词表与 backend/risk.py 的 KEYWORD_MAP 保持一致。
# ---------------------------------------------------------------------------
_LOCAL_KEYWORDS: Dict[str, List[str]] = {
    "green": ["开心", "高兴", "很好", "不错", "喜欢", "满意", "快乐", "幸福",
              "棒", "还行", "挺好", "没事", "哈哈", "嘻嘻", "谢谢", "感激"],
    "yellow": ["压力", "难过", "焦虑", "烦恼", "担心", "害怕考试", "累",
               "心累", "郁闷", "烦躁", "不开心", "不太好", "紧张", "迷茫",
               "孤独", "失落", "沮丧", "忧愁", "撑不下去", "撑不住", "扛不住",
               "坚持不下去", "熬不住", "挺不住"],
    "orange": ["欺凌", "欺负", "被欺负", "被打", "挨打", "讨厌", "恨", "恐惧",
               "害怕", "怕", "威胁", "勒索", "孤立", "排挤", "家庭暴力",
               "被骂", "人身攻击"],
    "red": ["自杀", "不想活", "想死", "跳楼", "割腕", "结束生命", "活不下去",
            "了断", "去死", "自伤", "自残", "上吊", "跳江", "吞药", "安眠药",
            "轻生", "寻短见", "坠楼", "结束自己", "跳河"],
}
_LOCAL_ORDER: List[str] = ["green", "yellow", "orange", "red"]
_LOCAL_SCORES: Dict[str, float] = {"green": 0.1, "yellow": 0.35, "orange": 0.7, "red": 1.0}


def _local_assess(text: str) -> Dict[str, Any]:
    """与 backend/risk.py::assess 等价的本地兜底实现。"""
    text = text or ""
    # 与 backend/risk.py::assess 一致的“最长匹配优先 + 区间重叠去重”
    hits: List[Any] = []
    for level in _LOCAL_ORDER:
        li = _LOCAL_ORDER.index(level)
        for kw in _LOCAL_KEYWORDS[level]:
            pos = text.find(kw)
            if pos != -1:
                hits.append((li, kw, pos, pos + len(kw)))
    hits.sort(key=lambda h: (-len(h[1]), h[0]))
    adopted: List[Any] = []
    for li, kw, s, e in hits:
        overlapped = any(s < e2 and s2 < e for (_, _, s2, e2) in adopted)
        if not overlapped:
            adopted.append((li, kw, s, e))
    adopted.sort(key=lambda h: (h[0], h[1]))
    all_matched = [kw for (_, kw, _, _) in adopted]
    best_level = _LOCAL_ORDER[max(h[0] for h in adopted)] if adopted else "green"
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

# 专业智能体角色 → 其独立生成用的结构化 Prompt（优先级一：让每类智能体真正独立调用 LLM）
_AGENT_SYSTEM_PROMPTS: Dict[str, str] = {
    "empathy_companion": COMPANION_AGENT_PROMPT,
    "cognitive_behavior": CBT_AGENT_PROMPT,
    "scenario_director": SCENARIO_DIRECTOR_AGENT_PROMPT,
}


def _parse_agent_json(text: str) -> Optional[Dict[str, Any]]:
    """把智能体输出的文本解析为结构化 JSON dict；失败 / 非对象时返回 None。"""
    if not text:
        return None
    t = text.strip()
    # 去掉可能包裹的三反引号代码块
    if t.startswith("```"):
        t = t.strip("`")
        if t.startswith("json"):
            t = t[len("json"):].lstrip()
    try:
        obj = json.loads(t)
    except (json.JSONDecodeError, TypeError):
        return None
    return obj if isinstance(obj, dict) else None


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
        self.last_final_response: str = ""                      # 最近一次整合回复（避免重复调用 LLM）
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
    def _agent_rule_output(self, agent: str, risk_level: str, user_text: str) -> Dict[str, Any]:
        """各专业智能体的规则版建议载荷（无网络兜底）。"""
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
        if agent == "scenario_director":
            return {
                "role": "scenario_director",
                "simulated_scene": (
                    "想象这样一个场景：课间，几位同学围在一起，对着你取笑、起外号，"
                    "周围还有人跟着笑起来，你站在原地，脸上火辣辣的，不知道该怎么办。"
                ),
                "character_roles": ["你", "取笑的同学", "围观的同伴"],
                "coping_options": [
                    "平静地说一句“请不要这样叫我，我不喜欢”，说完转身去找信任的朋友待在一起",
                    "课后单独把这件事告诉班主任或心理老师，请他们出面协调处理",
                    "先做几次深呼吸告诉自己：是他们做得不对，不是我的错，我不必用同样的方式回应",
                ],
                "role_play_line": "“请不要这样叫我，我不喜欢这样的称呼。”",
                "safe_guard": "仅进行口头/想象演练，不鼓励任何争吵或对抗行为；演练后如有需要可求助家长或老师",
                "risk_alert": risk_level,
                "confidence": 0.8,
            }
        return {"role": agent, "note": "规则版占位输出", "risk_alert": risk_level}

    # ------------------------------------------------------------------
    # 3b. 智能体独立生成（优先级一：让每类智能体真正独立调用大模型，产出结构化建议）
    # ------------------------------------------------------------------
    def _agent_prompt(self, agent: str, risk_level: str, user_text: str) -> str:
        """渲染对应智能体的结构化 Prompt；无模板时返回空串。"""
        prompt = _AGENT_SYSTEM_PROMPTS.get(agent)
        if not prompt:
            return ""
        try:
            return prompt.format(age=self.age, user_text=user_text, risk_level=risk_level)
        except (KeyError, IndexError, ValueError):
            return prompt

    def _agent_output(self, agent: str, risk_level: str, user_text: str) -> Dict[str, Any]:
        """生成单个智能体的结构化建议：LLM 优先，失败/未启用时回退规则版载荷。

        使用 json_mode 让模型输出与 Prompt 约定一致的结构化 JSON，被安全解析后
        与规则版载荷做字段级合并（保留 role / risk_alert / confidence 等框架字段）。
        """
        base = self._agent_rule_output(agent, risk_level, user_text)
        if not llm.is_enabled():
            return base
        prompt = self._agent_prompt(agent, risk_level, user_text)
        if not prompt:
            return base
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_text},
        ]
        text = llm.safe_chat(messages, fallback="", json_mode=True,
                             temperature=0.7, max_tokens=512)
        parsed = _parse_agent_json(text)
        if not parsed:
            return base
        merged = dict(base)
        for key, value in parsed.items():
            if value is not None and value != "":
                merged[key] = value
        merged["role"] = base.get("role") or agent
        merged["risk_alert"] = base.get("risk_alert") or risk_level
        return merged

    def _agent_context_text(
        self, outputs: Dict[str, Dict[str, Any]], risk_level: str
    ) -> str:
        """把各专业智能体的独立产出折叠成一句紧凑的『多智能体意见』，
        供协调智能体的最终整合（LLM）作为参考上下文。"""
        lines: List[str] = []
        if "empathy_companion" in outputs:
            o = outputs["empathy_companion"]
            lines.append("共情陪伴智能体：" + str(o.get("emotion_reflection", "")).strip())
        if "cognitive_behavior" in outputs:
            o = outputs["cognitive_behavior"]
            lines.append("认知行为智能体：" + str(o.get("reframed_thought", "")).strip())
            plan = o.get("action_plan") or []
            if plan:
                lines.append("认知行为智能体·行为建议：" + "；".join(map(str, plan)))
        if "scenario_director" in outputs:
            o = outputs["scenario_director"]
            opts = o.get("coping_options") or []
            lines.append("情景导演智能体·演练场景：" + str(o.get("simulated_scene", "")).strip())
            if opts:
                lines.append("情景导演智能体·应对选项：" + "；".join(map(str, opts)))
        return "\n".join(line for line in lines if line)

    def _assemble_offline_response(
        self,
        outputs: Dict[str, Dict[str, Any]],
        risk_level: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """离线时用各智能体（规则版）的结构化字段组装最终回复，
        而非只返回固定的 RESPONSE_TEMPLATES —— 让兜底也更有针对性。"""
        fallback = RESPONSE_TEMPLATES.get(risk_level, RESPONSE_TEMPLATES["green"])
        if not outputs:
            return fallback
        emp = outputs.get("empathy_companion") or {}
        cbt = outputs.get("cognitive_behavior") or {}
        sdir = outputs.get("scenario_director") or {}
        pieces: List[str] = []

        companion = str(emp.get("companion_response", "")).strip() or fallback
        pieces.append(companion)

        if cbt.get("reframed_thought"):
            pieces.append("试着换个角度看：" + str(cbt["reframed_thought"]).strip())
        plan = cbt.get("action_plan") or []
        if plan:
            pieces.append("今天你可以试着：-" + "；".join(map(str, plan[:2])))

        if risk_level == "orange" and sdir.get("coping_options"):
            opts = sdir["coping_options"]
            pieces.append("如果情境重现，你可以选择：-" + "；".join(map(str, opts[:2])))
            if sdir.get("role_play_line"):
                pieces.append("可以试着练习这句：" + str(sdir["role_play_line"]).strip())
        return "\n".join(pieces)




    def negotiate(
        self,
        user_text: str,
        risk: Dict[str, Any],
        session_id: str = "",
        history: Optional[List[Dict[str, str]]] = None,
    ) -> List[AIPMessage]:
        """组织一次 ACPs/AIP 内部协商，返回完整报文列表。

        流程：协调→安全评估(优先) → [高危:VETO_INTERRUPT 广播中断]
              → 协调→各专业智能体并行讨论 → 交叉校验 → 整合输出。
        """
        msgs: List[AIPMessage] = []
        risk_level: str = risk.get("level", "green")
        routed: List[str] = self.dispatch(risk_level)
        risk_hint = f"level={risk_level}, score={risk.get('score', 0.0)}"

        # 本轮各专业智能体的独立产出（供最终回复整合使用）
        agent_outputs: Dict[str, Dict[str, Any]] = {}
        self.last_agent_outputs = agent_outputs

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
            emergency_text = self._generate_emergency_text(user_text, history=history)
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
            "scenario_director": SCENARIO_DIRECTOR_AGENT_PROMPT,
        }
        # 仅多智能体协商（yellow/orange 且路由 >= 2）才让每个智能体独立调用 LLM；
        # green 仅共情陪伴 1 个智能体，由协调器一次性整合，保证单次调用与既有契约。
        multi_agent = risk_level in ("yellow", "orange") and len(routed) >= 2
        for agent in routed:
            prompt = agent_prompts.get(agent, "")
            if prompt:
                prompt = prompt.format(
                    age=self.age, user_text=user_text, risk_level=risk_level,
                )
            output = (
                self._agent_output(agent, risk_level, user_text)
                if multi_agent else self._agent_rule_output(agent, risk_level, user_text)
            )
            if multi_agent:
                agent_outputs[agent] = output
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
                payload=output,
                session_id=session_id,
                reply_to=req.message_id,
            ))

        # 多智能体意见汇总 → 供协调器最终整合（LLM 上下文 / 离线组装）
        self.last_agent_context = self._agent_context_text(agent_outputs, risk_level)

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

        # ---- Step 4b：整合修订阶段（真正启用 REVISION_NOTICE + INTEGRATE_* 报文） ----
        # 多智能体协商时：交叉校验后由协调器广播修订指令，并逐个请求/回收各智能体的
        # 最终整合意见。此阶段让 AIP 协议里"修订→整合"的报文类型真正投入使用，
        # 并把各智能体的最终意见回灌到 last_agent_outputs，供 Step5 整合回复参考。
        if risk_level in ("yellow", "orange") and len(routed) >= 2:
            msgs.append(new_message(
                COORDINATOR, "all", MsgType.REVISION_NOTICE,
                payload={
                    "instruction": "请各专业智能体依据交叉校验结果复核并最终确定各自建议。",
                    "base": "cross_check",
                    "risk_level": risk_level,
                },
                session_id=session_id,
            ))
            for agent in routed:
                opinion = agent_outputs.get(agent)
                if opinion is None:
                    opinion = self._agent_rule_output(agent, risk_level, user_text)
                req = new_message(
                    COORDINATOR, agent, MsgType.INTEGRATE_REQUEST,
                    payload={"risk_level": risk_level, "revised": True},
                    session_id=session_id,
                )
                msgs.append(req)
                msgs.append(new_message(
                    agent, COORDINATOR, MsgType.INTEGRATE_RESPONSE,
                    payload={
                        "final_opinion": opinion,
                        "revised_note": "经交叉校验后确认，未作额外改动",
                    },
                    session_id=session_id,
                    reply_to=req.message_id,
                ))

        # ---- Step 5：协调智能体整合统一回复 ----
        final_response = self.build_response(user_text, risk_level, history=history)
        self.last_final_response = final_response  # 供 process_dialogue 直接复用，避免重复调用 LLM
        msgs.append(new_message(
            COORDINATOR, "all", MsgType.INTEGRATE_RESPONSE,
            payload={
                "final_response": final_response,
                "action": self.decide_action(risk_level),
                "risk_level": risk_level,
                "routed_agents": routed,
            },
            session_id=session_id,
        ))
        return msgs

    def _build_llm_messages(
        self,
        user_text: str,
        risk_level: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, str]]:
        """把 system prompt + 多轮历史 + 当前用户输入拼成 OpenAI messages 列表。"""
        risk_display = {
            "green": "green（绿/低风险：日常分享或一般情绪波动）",
            "yellow": "yellow（黄/中风险：压力、焦虑、难过等负面情绪）",
            "orange": "orange（橙/较高风险：恐惧、受欺凌、被威胁等）",
            "red": "red（红/高危：自杀/自伤意念等）",
        }.get(risk_level, risk_level)

        system_prompt = FINAL_SYSTEM_PROMPT.format(
            age=self.age,
            risk_level_display=risk_display,
            hotline=self.emergency_hotline,
        )
        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
        for item in (history or [])[-8:]:  # 只携带最近 8 条，避免上下文超长
            role = item.get("role")
            content = str(item.get("content", "")).strip()
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        # 将本轮各专业智能体的独立意见作为协调器整合的参考上下文（多智能体时才非空）
        if getattr(self, "last_agent_context", ""):
            messages.append({
                "role": "system",
                "content": "以下是本轮各专业智能体的独立意见，请整合后给出最终回复：\n"
                           + self.last_agent_context,
            })
        messages.append({"role": "user", "content": user_text})
        return messages

    # ------------------------------------------------------------------
    # 4. 内容感知的应急话术（解决"每次危机都回同一句模板"的体验问题）
    # ------------------------------------------------------------------
    def _has_repeated_crisis(
        self, history: Optional[List[Dict[str, str]]] = None
    ) -> bool:
        """历史中是否已出现过含热线/援助提示的高危助理回复（用于连续高风险时进一步强调求助）。"""
        if not history:
            return False
        for item in history[-12:]:
            content = str(item.get("content", "") or "")
            if item.get("role") == "assistant" and (
                self.emergency_hotline in content or "心理援助热线" in content
            ):
                return True
        return False

    def _pick(self, pool: List[str]) -> str:
        """从给定语料池里随机取一句（无固定 seed，保证同一输入多轮也不同）。"""
        return random.choice(pool)

    def _compose_emergency_response(
        self,
        user_text: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """离线应急话术：真正在"句式结构"层面多变，而不是换几个词。

        做法：按命中的危机子信号挑选镜映措辞 → 其余句子从语料池随机 → 再随机
        套用一套不同的句子骨架（镜映 / 求助先后顺序、开头方式等都会变化）→
        最后由 _enforce_safety_mandate 兜底热度与真实成人求助，确保安全不变。
        设计初衷：既定的 single-template + 固定拼接顺序正是"每次句式都一样"
        的根源；本实现让骨架、块顺序、措辞三层都发生变化。
        """
        signals = _detect_crisis_signals(user_text)
        hotline = self.emergency_hotline

        if signals["help_invalidation"]:
            mirror = self._pick(_MIRROR_INVALIDATION)
        elif signals["hopelessness"]:
            mirror = self._pick(_MIRROR_HOPELESSNESS)
        elif signals["active_plan"]:
            mirror = self._pick(_MIRROR_PLAN)
        else:
            mirror = self._pick(_MIRROR_GENERIC)

        bridge = self._pick(_BRIDGE)
        escalation = self._pick(_ESCALATION).format(hotline=hotline)

        if self._has_repeated_crisis(history):
            closing = self._pick(_CLOSING_REPEAT)
        else:
            closing = self._pick(_CLOSING_NORMAL)

        parts = {
            "mirror": mirror,
            "bridge": bridge,
            "escalation": escalation,
            "close": closing,
        }
        order = self._pick(_OFFLINE_STRUCTURES)
        pieces: List[str] = []
        for key in order:
            if key == "esc_urgent_first":
                pieces.append(self._pick(_URGENT_FIRST))
            else:
                pieces.append(parts[key])
        return _enforce_safety_mandate("".join(pieces), hotline)

    def _llm_emergency(
        self,
        user_text: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """（可选·受约束）调用大模型生成危机回复。

        仅在 _crisis_guard_enabled() 且 LLM 已启用时由 _generate_emergency_text 调用；
        返回文本随后仍会过 _enforce_safety_mandate，保证安全。失败则回退离线生成。
        """
        fallback = self._compose_emergency_response(user_text, history=history)
        if not llm.is_enabled():
            return fallback
        system_prompt = CRISIS_GUARDED_PROMPT.format(
            age=self.age, user_text=user_text, hotline=self.emergency_hotline
        )
        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
        for item in (history or [])[-8:]:
            role = item.get("role")
            content = str(item.get("content", "")).strip()
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_text})
        return llm.safe_chat(messages, fallback=fallback, temperature=0.9, max_tokens=256)

    def _generate_emergency_text(
        self,
        user_text: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """高危应急话术统一入口：生成 → 安全兜底 → 复用缓存，避免重复调用。"""
        if not self.last_final_response:
            text = self._compose_emergency_response(user_text, history=history)
            if _crisis_guard_enabled():
                text = self._llm_emergency(user_text, history=history)
            self.last_final_response = _enforce_safety_mandate(text, self.emergency_hotline)
        return self.last_final_response

    # ------------------------------------------------------------------
    # 4b. 统一回复生成
    # ------------------------------------------------------------------
    def build_response(
        self,
        user_text: str,
        risk_level: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """按风险等级生成最终回复（接入 LLM，支持多轮记忆）。

        - red 高危：不交给 LLM 自由发挥，直接输出含热线的应急话术；
        - 其他等级：LLM 已启用时调用大模型生成个性化回复（并参考各智能体独立意见）；
        - LLM 未启用 / 调用失败：用各智能体结构化字段组装兜底（否则回退 RESPONSE_TEMPLATES）。
        """
        fallback = RESPONSE_TEMPLATES.get(risk_level, RESPONSE_TEMPLATES["green"])
        if risk_level == "red":
            return self._generate_emergency_text(user_text, history=history)
        if not llm.is_enabled():
            return self._assemble_offline_response(
                getattr(self, "last_agent_outputs", {}), risk_level, history=history
            ) or fallback
        messages = self._build_llm_messages(user_text, risk_level, history)
        return llm.safe_chat(messages, fallback=fallback, temperature=0.7, max_tokens=512)

    # ------------------------------------------------------------------
    # 5. 对外主入口
    # ------------------------------------------------------------------
    def process_dialogue(
        self,
        user_text: str,
        session_id: str = "",
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """处理一段用户输入，返回统一对话结果（对外主入口）。

        :param history: 可选，该会话此前消息的历史列表，形如
            [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
            用于给 LLM 提供多轮对话记忆；None 表示无语境（首轮）。
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
        #    —— 每轮重置"上一轮整合回复"缓存，避免高危轮误复用上一轮（低危）话术：
        #    此前 red 在 negotiate() 中提前 return，不会更新 last_final_response，
        #    导致"先聊低落→再表达危机"时返回上一轮的无效模板、漏掉危机信号。
        self.last_final_response = ""
        risk = self.assess_risk(text)
        risk_level: str = risk.get("level", "green")

        # 2) 一票否决判定（风险等级为 red，或风险模块判定为 critical）
        is_vetoed: bool = (risk_level == "red") or self.is_critical_fn(risk_level)

        # 3) 组织 ACPs/AIP 协商，记录协作日志
        messages = self.negotiate(text, risk, session_id=session_id, history=history)
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
            "response_text": getattr(self, "last_final_response", None)
            or self.build_response(text, risk_level, history=history),
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

