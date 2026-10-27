"""ai_agents —— MindIsle（心屿）ACPs 多智能体核心模块包

遵循北邮智能体互联协议（ACPs）：
  - prompts.py      ：三个专业智能体（Safety / Companion / CBT）的 Prompt 模板
  - protocols.py    ：AIP 交互协议 JSON 报文封装（sender / receiver / msg_type / payload / timestamp）
  - coordinator.py  ：多智能体协商与路由协调器（结合 backend/risk.py 风险等级，高危一票否决）
"""
from ai_agents.prompts import (
    CBT_AGENT_PROMPT,
    COMPANION_AGENT_PROMPT,
    SAFETY_AGENT_PROMPT,
    SYSTEM_PROMPTS,
    VETO_INTERRUPT_PROMPT,
)
from ai_agents.protocols import AGENT_ROLES, AIPMessage, MsgType, new_message
from ai_agents.coordinator import MultiAgentCoordinator

__all__ = [
    "AGENT_ROLES",
    "AIPMessage",
    "CBT_AGENT_PROMPT",
    "COMPANION_AGENT_PROMPT",
    "MsgType",
    "MultiAgentCoordinator",
    "SAFETY_AGENT_PROMPT",
    "SYSTEM_PROMPTS",
    "VETO_INTERRUPT_PROMPT",
    "new_message",
]
