"""
ai_agents/protocols.py
北邮 ACPs（Agent Collaboration Protocols）· AIP 交互协议 JSON 报文封装

遵循《需求分析文档》3.3 接口规范：
  交互与协作（AIP）：规定多智能体并行讨论、交叉校验及安全评估智能体
  “一票否决”中断指令的报文格式与传输规范。

标准报文字段：
  protocol     : 协议名（北邮智能体互联协议（ACPs）· AIP 交互协议）
  version      : 协议版本
  message_id   : 报文唯一标识（uuid）
  sender       : 发送方智能体角色
  receiver     : 接收方智能体角色（"all" 表示广播）
  msg_type     : 报文类型（见 MsgType）
  timestamp    : ISO 8601 时间戳（本地时区，秒级）
  session_id   : 会话标识（可为空）
  reply_to     : 所回复的上一条报文 message_id
  payload      : 业务载荷（dict，可包含 prompt / 建议 / 风险信息等）
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# 协议元信息
# ---------------------------------------------------------------------------
ACPS_SPEC = "北邮智能体互联协议（ACPs）"
AIP_PROTOCOL_NAME = "AIP 交互协议（Agent Interaction Protocol）"
AIP_VERSION = "1.0"

# 智能体角色表（与 backend/requirements.py 的 AGENT_ROLES 对齐）
AGENT_ROLES: List[str] = [
    "coordinator",               # 协调智能体
    "safety_assessor",           # 安全评估智能体（VETO_AGENT，一票否决）
    "empathy_companion",         # 共情陪伴智能体
    "cognitive_behavior",        # 认知行为（CBT）智能体
    "scenario_director",         # 情景导演智能体
    "developmental_psychology",  # 发展心理学智能体
    "home_school_context",       # 家校上下文智能体
]

SYSTEM_ROLES: List[str] = ["system", "student"]

class MsgType:
    """ACPs/AIP 报文类型（并行讨论 · 交叉校验 · 修订整合 · 一票否决）"""

    # ---- 发现与心跳 ----
    AIP_HEARTBEAT = "AIP_HEARTBEAT"

    # ---- 并行讨论 ----
    DISCUSS_REQUEST = "DISCUSS_REQUEST"      # 协调 → 专业智能体：发起并行讨论
    DISCUSS_RESPONSE = "DISCUSS_RESPONSE"    # 专业智能体 → 协调：返回建议

    # ---- 交叉校验 ----
    CROSS_CHECK_REQUEST = "CROSS_CHECK_REQUEST"    # 协调 → 专业智能体：请求交叉校验
    CROSS_CHECK_RESPONSE = "CROSS_CHECK_RESPONSE"  # 专业智能体 → 协调：返回校验结论

    # ---- 修订 ----
    REVISION_NOTICE = "REVISION_NOTICE"      # 协调 → 专业智能体：要求修订

    # ---- 整合 ----
    INTEGRATE_REQUEST = "INTEGRATE_REQUEST"  # 协调 → 专业智能体：请求整合意见
    INTEGRATE_RESPONSE = "INTEGRATE_RESPONSE"  # 协调 → 全部：发布统一回复

    # ---- 安全一票否决中断指令 ----
    VETO_INTERRUPT = "VETO_INTERRUPT"        # safety_assessor → 广播：立即中断一切流程

    # ---- 消息路由 ----
    ROUTE_NOTIFY = "ROUTE_NOTIFY"            # 协调 → 相关智能体：通知路由结果

    VALID = frozenset(
        {
            AIP_HEARTBEAT,
            DISCUSS_REQUEST,
            DISCUSS_RESPONSE,
            CROSS_CHECK_REQUEST,
            CROSS_CHECK_RESPONSE,
            REVISION_NOTICE,
            INTEGRATE_REQUEST,
            INTEGRATE_RESPONSE,
            VETO_INTERRUPT,
            ROUTE_NOTIFY,
        }
    )


@dataclass
class AIPMessage:
    """ACPs/AIP 交互协议报文。

    提供统一 JSON 序列化 / 反序列化能力，供协调器记录协作日志、
    交叉校验与跨进程传输（可直接存入后台协作日志或网络发送）。
    """

    sender: str
    receiver: str
    msg_type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    message_id: str = ""
    session_id: str = ""
    reply_to: str = ""
    protocol: str = f"{ACPS_SPEC} · {AIP_PROTOCOL_NAME}"
    version: str = AIP_VERSION

    def __post_init__(self) -> None:
        if not self.message_id:
            self.message_id = uuid.uuid4().hex[:16]
        if not self.timestamp:
            self.timestamp = self._now()

    @staticmethod
    def _now() -> str:
        """ISO 8601 本地时间（秒级），与数据库模块时间格式保持一致。"""
        return datetime.now().astimezone().isoformat(timespec="seconds")

    # ------------------------------------------------------------------
    # 序列化 / 反序列化
    # ------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        """转为标准报文字典（JSON 友好）。"""
        return {
            "protocol": self.protocol,
            "version": self.version,
            "message_id": self.message_id,
            "sender": self.sender,
            "receiver": self.receiver,
            "msg_type": self.msg_type,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "reply_to": self.reply_to,
            "payload": self.payload,
        }

    def to_json(self, ensure_ascii: bool = False, **kwargs: Any) -> str:
        """转为 JSON 字符串（默认保留中文可读性）。"""
        return json.dumps(self.to_dict(), ensure_ascii=ensure_ascii, **kwargs)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AIPMessage":
        """从报文字典还原报文对象。"""
        return cls(
            sender=data.get("sender", ""),
            receiver=data.get("receiver", ""),
            msg_type=data.get("msg_type", ""),
            payload=data.get("payload", {}),
            timestamp=data.get("timestamp", ""),
            message_id=data.get("message_id", ""),
            session_id=data.get("session_id", ""),
            reply_to=data.get("reply_to", ""),
            protocol=data.get("protocol", f"{ACPS_SPEC} · {AIP_PROTOCOL_NAME}"),
            version=data.get("version", AIP_VERSION),
        )

    @classmethod
    def from_json(cls, text: str) -> "AIPMessage":
        """从 JSON 字符串还原报文对象。"""
        return cls.from_dict(json.loads(text))

    # ------------------------------------------------------------------
    # 校验
    # ------------------------------------------------------------------
    def validate(self) -> List[str]:
        """校验报文字段合法性，返回错误清单（空列表表示合法）。"""
        errors: List[str] = []
        if not self.sender:
            errors.append("sender 不能为空")
        if not self.receiver:
            errors.append("receiver 不能为空")
        if self.msg_type not in MsgType.VALID:
            errors.append(f"未知的 msg_type: {self.msg_type!r}（合法值见 MsgType.VALID）")
        return errors

    def is_valid(self) -> bool:
        """报文是否合法。"""
        return not self.validate()


def new_message(
    sender: str,
    receiver: str,
    msg_type: str,
    payload: Dict[str, Any] | None = None,
    **kwargs: Any,
) -> AIPMessage:
    """便捷构造一条 AIP 报文（payload 缺省为空字典）。"""
    return AIPMessage(sender, receiver, msg_type, payload or {}, **kwargs)


if __name__ == "__main__":
    # 演示：构造、序列化、反序列化一条 AIP 报文
    demo = new_message(
        sender="safety_assessor",
        receiver="all",
        msg_type=MsgType.VETO_INTERRUPT,
        payload={"reason": "命中高危信号: 不想活", "hotline": "400-161-9995"},
        session_id="demo-001",
    )
    print("== AIPMessage 演示 ==")
    print("是否合法:", [demo.is_valid(), demo.validate()])
    print("JSON:", demo.to_json())
    restored = AIPMessage.from_json(demo.to_json())
    print("还原后 sender/msg_type:", restored.sender, "/", restored.msg_type)

