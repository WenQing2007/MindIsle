"""
tests/test_ai_agents.py
验证 ai_agents 多智能体模块（ACPs / AIP 协议 + 高风险一票否决 + 分发路由）。

覆盖分支：
  [协议层] AIPMessage 报文字段、JSON 序列化 / 反序列化往返、合法性校验；
  [协调层] 四级风险（green / yellow / orange / red）的路由分发；
  [核心机制] red 高危 → 一票否决（is_vetoed=True, action=TRIGGER_EMERGENCY_POPUP,
            回复包含 24 小时心理援助热线，协作日志含 VETO_INTERRUPT 中断报文）；
  [后端结合] 确认协调器加载的是 backend/risk.py 的风险评估接口。

运行方式（在项目根目录下）：
  python -m unittest discover -s tests -v
"""
import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_agents.coordinator import EMERGENCY_HOTLINE, MultiAgentCoordinator
from ai_agents.protocols import AIPMessage, MsgType, new_message


class TestAIPProtocol(unittest.TestCase):
    """ACPs/AIP 报文封装测试"""

    def test_message_fields_and_serialization_roundtrip(self):
        """报文字段完整，JSON 序列化后能无损还原"""
        msg = new_message(
            sender="coordinator",
            receiver="empathy_companion",
            msg_type=MsgType.DISCUSS_REQUEST,
            payload={"user_text": "你好呀", "risk_level": "green"},
            session_id="s001",
        )
        data = msg.to_dict()
        # 标准字段齐全
        for field in ("sender", "receiver", "msg_type", "payload", "timestamp",
                      "message_id", "session_id", "protocol", "version"):
            self.assertIn(field, data)
        self.assertEqual(data["sender"], "coordinator")
        self.assertEqual(data["receiver"], "empathy_companion")
        self.assertEqual(data["msg_type"], "DISCUSS_REQUEST")
        self.assertEqual(data["payload"]["risk_level"], "green")
        self.assertIn("ACPs", data["protocol"])

        restored = AIPMessage.from_json(msg.to_json())
        self.assertEqual(restored.sender, msg.sender)
        self.assertEqual(restored.receiver, msg.receiver)
        self.assertEqual(restored.msg_type, msg.msg_type)
        self.assertEqual(restored.payload, msg.payload)
        self.assertEqual(restored.message_id, msg.message_id)

    def test_timestamp_auto_filled(self):
        """未指定时间戳时自动填充 ISO 8601 时间"""
        msg = new_message("a", "b", MsgType.AIP_HEARTBEAT, {})
        self.assertTrue(msg.timestamp)

    def test_validation(self):
        """校验：空角色 / 非法类型应被识别"""
        bad = AIPMessage(sender="", receiver="", msg_type="NOT_A_TYPE")
        self.assertFalse(bad.is_valid())
        errors = bad.validate()
        self.assertTrue(any("sender" in e for e in errors))
        self.assertTrue(any("msg_type" in e for e in errors))


class TestCoordinatorRouting(unittest.TestCase):
    """多智能体路由与一票否决测试"""

    def setUp(self):
        self.coordinator = MultiAgentCoordinator()

    def test_uses_backend_risk_api(self):
        """协调器应结合后端 backend/risk.py 的风险评估接口"""
        from ai_agents.coordinator import _ASSESS
        self.assertEqual(_ASSESS.__module__, "backend.risk")

    def test_green_routes_to_companion(self):
        """绿色：仅路由到共情陪伴智能体，正常对话"""
        result = self.coordinator.process_dialogue("今天考试考了 100 分，好开心")
        self.assertEqual(result["risk_level"], "green")
        self.assertEqual(result["routed_agents"], ["empathy_companion"])
        self.assertFalse(result["is_vetoed"])
        self.assertEqual(result["action"], "NORMAL_TALK")
        self.assertNotIn(EMERGENCY_HOTLINE, result["response_text"])

    def test_yellow_routes_to_companion_and_cbt(self):
        """黄色：路由到共情陪伴 + CBT，进行交叉校验"""
        result = self.coordinator.process_dialogue("最近压力好大，晚上睡不着，有点难过")
        self.assertEqual(result["risk_level"], "yellow")
        self.assertEqual(result["routed_agents"],
                         ["empathy_companion", "cognitive_behavior"])
        self.assertEqual(result["action"], "WARN_TEACHER_ANONYMOUS")
        log_types = [m["msg_type"] for m in self.coordinator.get_collaboration_log()]
        self.assertIn(MsgType.CROSS_CHECK_REQUEST, log_types)
        self.assertIn(MsgType.CROSS_CHECK_RESPONSE, log_types)

    def test_orange_action_notify_teacher(self):
        """橙色：通知心理教师介入"""
        result = self.coordinator.process_dialogue("我被同学欺负了，很害怕去学校")
        self.assertEqual(result["risk_level"], "orange")
        self.assertEqual(result["action"], "NOTIFY_TEACHER")
        self.assertFalse(result["is_vetoed"])

    def test_red_triggers_one_vote_veto(self):
        """红色/高危：安全评估智能体一票否决，立即中断并给出 24 小时热线"""
        result = self.coordinator.process_dialogue("我真的不想活了，想跳楼")
        self.assertEqual(result["risk_level"], "red")
        self.assertTrue(result["is_vetoed"])
        self.assertEqual(result["action"], "TRIGGER_EMERGENCY_POPUP")
        self.assertIn(EMERGENCY_HOTLINE, result["response_text"])
        self.assertEqual(result["routed_agents"], ["safety_assessor"])

        # 协作日志必须包含 VETO_INTERRUPT 中断指令与 ROUTE_NOTIFY 路由通知
        log_types = [m["msg_type"] for m in self.coordinator.get_collaboration_log()]
        self.assertIn(MsgType.VETO_INTERRUPT, log_types)
        self.assertIn(MsgType.ROUTE_NOTIFY, log_types)
        # 中断后不应再有正常讨论报文
        self.assertNotIn(MsgType.DISCUSS_RESPONSE, log_types)

    def test_custom_hotline(self):
        """支持自定义热线"""
        coordinator = MultiAgentCoordinator(emergency_hotline="12345-6")
        result = coordinator.process_dialogue("我不想活了")
        self.assertTrue(result["is_vetoed"])
        self.assertIn("12345-6", result["response_text"])

    def test_empty_input_safe_fallback(self):
        """空输入必须有安全兜底，不触发异常"""
        result = self.coordinator.process_dialogue("   ")
        self.assertEqual(result["risk_level"], "green")
        self.assertFalse(result["is_vetoed"])
        self.assertTrue(result["response_text"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
