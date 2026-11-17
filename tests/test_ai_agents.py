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
from unittest import mock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_agents.coordinator import EMERGENCY_HOTLINE, MultiAgentCoordinator
from ai_agents.protocols import AIPMessage, MsgType, new_message

OLD_EMERGENCY_TEMPLATE = (
    "听到你现在经历的痛苦，我非常关切你。你并不孤单，"
    "请立刻寻求老师、家长或拨打 24 小时全国心理援助热线：" + EMERGENCY_HOTLINE + "。"
)


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


class TestCrisisResponseQuality(unittest.TestCase):
    """危机应急话术的质量：不再机械重复、不再反驳学生"帮不了/解决不了"的绝望。

    对应体验反馈问题：当学生表达"你帮不了我 / 也解决不了我的问题 / 我选择去死"时，
    系统此前每次都回同一句固定模板（"你并不孤单……"），既重复又未真正接住内容。
    """

    def setUp(self):
        self.coordinator = MultiAgentCoordinator()

    def test_help_invalidation_is_mirrored_not_contradicted(self):
        """表达"帮不了/解决不了"时，回复必须接住这句话本身，而非机械反驳"""
        text = "你帮不了我，也解决不了我的问题，我选择去死"
        result = self.coordinator.process_dialogue(text)
        self.assertTrue(result["is_vetoed"])
        self.assertEqual(result["risk_level"], "red")
        self.assertEqual(result["action"], "TRIGGER_EMERGENCY_POPUP")
        # 安全底线仍在：给出 24 小时援助热线
        self.assertIn(EMERGENCY_HOTLINE, result["response_text"])
        # 关键：不再返回旧的唯一固定模板
        self.assertNotEqual(result["response_text"], OLD_EMERGENCY_TEMPLATE)
        # 关键：真正镜映了"帮不了/解决不了"这份绝望
        self.assertIn("帮不了", result["response_text"])
        self.assertIn("解决不了", result["response_text"])
        # 不再用"你并不孤单"之类的话反驳其真实感受
        self.assertNotIn("你并不孤单", result["response_text"])

    def test_hopelessness_signal_recognized(self):
        """'撑不下去'这类无望信号也应有对应镜映"""
        result = self.coordinator.process_dialogue("我真的撑不下去了，不想活了")
        self.assertTrue(result["is_vetoed"])
        self.assertIn(EMERGENCY_HOTLINE, result["response_text"])
        self.assertNotEqual(result["response_text"], OLD_EMERGENCY_TEMPLATE)

    def test_crisis_replies_not_byte_identical(self):
        """不同危机表达应产生不同回复，而非每次一字不差"""
        a = self.coordinator.process_dialogue("我真的不想活了，想跳楼")["response_text"]
        b = self.coordinator.process_dialogue("你别逼我，我今晚就从楼上跳下去")["response_text"]
        c = self.coordinator.process_dialogue("你帮不了我，我选择去死")["response_text"]
        self.assertEqual(len({a, b, c}), 3, "三次不同危机应得到不同回复")

    def test_repeated_crisis_escalates_after_history(self):
        """历史中已出现过危机时，应急话术应进一步强调立即求助，避免重复套话"""
        history = [
            {"role": "user", "content": "我好痛苦"},
            {"role": "assistant", "content": f"……心理援助热线：{EMERGENCY_HOTLINE}……"},
        ]
        first = self.coordinator.process_dialogue("我不想活了")["response_text"]
        second = self.coordinator.process_dialogue(
            "我不想活了", history=history
        )["response_text"]
        self.assertNotEqual(first, second)
        # 连续危机的回复包含强调"上次/再次"的求助升级话术
        self.assertIn("上次", second)

    def test_custom_hotline_used_in_composed_reply(self):
        """自定义热线仍生效，且不泄漏默认热线"""
        coordinator = MultiAgentCoordinator(emergency_hotline="12345-6")
        result = coordinator.process_dialogue("帮不了我，我选择去死")
        self.assertTrue(result["is_vetoed"])
        self.assertIn("12345-6", result["response_text"])
        self.assertNotIn(EMERGENCY_HOTLINE, result["response_text"])

    def test_crisis_after_low_risk_turn_does_not_leak_old_reply(self):
        """多轮场景：先低危、再危机时，高危轮必须返回应急话术，
        绝不能复用上一轮（低危）的普通模板（原状态泄漏 bug 的回归测试）"""
        coordinator = MultiAgentCoordinator()
        # 第一轮低危：写入 last_final_response = 普通模板
        low = coordinator.process_dialogue("最近压力有点大，好累")
        self.assertFalse(low["is_vetoed"])
        self.assertIn("压力", low["response_text"])

        # 第二轮危机：必须绕过上一轮的失效缓存，返回应急话术
        crisis = coordinator.process_dialogue("我撑不下去了，我选择去死")
        self.assertTrue(crisis["is_vetoed"])
        self.assertEqual(crisis["risk_level"], "red")
        self.assertIn(EMERGENCY_HOTLINE, crisis["response_text"])
        # 关键断言：不再返回上一轮的普通陪伴模板
        self.assertNotEqual(crisis["response_text"], low["response_text"])

    def test_new_suicidal_intent_words_detected(self):
        """补充的自杀意图词（轻生/坠楼/跳河等）应被识别为高危"""
        cases = ["我今晚想轻生", "我准备从楼上坠楼", "我想去跳河，救不了我"]
        for text in cases:
            with self.subTest(text=text):
                result = self.coordinator.process_dialogue(text)
                self.assertTrue(result["is_vetoed"], text)
                self.assertEqual(result["risk_level"], "red")
                self.assertIn(EMERGENCY_HOTLINE, result["response_text"])

    def test_offline_same_input_yields_varied_structure(self):
        """同一高危输入多次离线生成的回复不应一字不差（骨架/块顺序/措辞都会变）"""
        coordinator = MultiAgentCoordinator()
        texts = {
            coordinator.process_dialogue("我选择去死")["response_text"]
            for _ in range(40)
        }
        self.assertGreater(len(texts), 1, "离线应急话术应存在结构性变化，而非固定一句")

    def test_all_offline_crisis_replies_pass_safety_mandate(self):
        """离线生成的任何应急回复都必须同时含热线与'向真实成人求助'语义"""
        coordinator = MultiAgentCoordinator()
        samples = [
            "你帮不了我，我选择去死",
            "我真的不想活了，想跳楼",
            "我撑不下去了，活不下去",
            "我今晚想轻生",
        ]
        for s in samples:
            for _ in range(15):
                text = coordinator.process_dialogue(s)["response_text"]
                self.assertIn(EMERGENCY_HOTLINE, text)
                self.assertTrue(
                    any(k in text for k in ("老师", "家长", "成人", "班主任", "大人", "成年人")),
                    f"缺少真实成人求助语义: {text}",
                )

    def test_guarded_crisis_uses_llm_when_enabled(self):
        """开启 LLM_GUARDED_CRISIS 且 LLM 可用时，red 由大模型生成，但仍被安全兜底"""
        with mock.patch.dict(os.environ, {"LLM_GUARDED_CRISIS": "true"}, clear=False), \
             mock.patch("ai_agents.llm.is_enabled", return_value=True), \
             mock.patch(
                 "ai_agents.llm.chat_completion",
                 return_value="我知道你现在很难受，先停一下，好吗？",
             ) as mock_chat:
            result = self.coordinator.process_dialogue("我选择去死")
            self.assertTrue(mock_chat.called)
        self.assertTrue(result["is_vetoed"])
        self.assertEqual(result["risk_level"], "red")
        # 即便模型没写热线，安全兜底也会强制补上热线与真人求助
        self.assertIn(EMERGENCY_HOTLINE, result["response_text"])
        self.assertTrue(
            any(k in result["response_text"] for k in ("老师", "家长", "成人", "班主任"))
        )

    def test_crisis_guard_off_never_calls_llm_for_red(self):
        """默认（未开启 LLM_GUARDED_CRISIS）：red 绝不调用大模型，保持安全契约"""
        with mock.patch("ai_agents.llm.is_enabled", return_value=True), \
             mock.patch("ai_agents.llm.chat_completion") as mock_chat:
            result = self.coordinator.process_dialogue("我真的不想活了，想跳楼")
            mock_chat.assert_not_called()
        self.assertTrue(result["is_vetoed"])
        self.assertIn(EMERGENCY_HOTLINE, result["response_text"])


class TestMultiAgentLLMIntegration(unittest.TestCase):
    """优先级一：多智能体协商时，每个路由智能体独立调用大模型，产出结构化建议，
    并真正进入协作日志 / 最终回复（而非只写日志、回复仍用固定模板）。"""

    def setUp(self):
        self.coordinator = MultiAgentCoordinator()

    def test_yellow_calls_each_agent_llm_and_uses_outputs(self):
        """yellow（共情+CBT）时，两类智能体各自独立调用 LLM，且协作日志里
        DISCUSS_RESPONSE 的载荷确实是 LLM 结构化产出（而非规则版占位）"""
        calls = []

        def fake_chat(messages, **kw):
            calls.append(1)
            sys_p = messages[0]["content"]
            if "Companion Agent" in sys_p:
                return ('{"emotion_reflection":"（LLM）我能感觉到你现在很不好受。",'
                        '"companion_response":"（LLM）我在，愿意听你说。",'
                        '"gentle_guidance":"（LLM）先慢慢呼吸。"}')
            if "CBT Agent" in sys_p:
                return ('{"reframed_thought":"（LLM）一次没做好不等于什么都做不好。",'
                        '"action_plan":["（LLM）先休息10分钟","（LLM）把担心的写下来"]}')
            return "（协调器）辛苦你了，我们一起看看怎么让你好受一点。"

        with mock.patch("ai_agents.llm.is_enabled", return_value=True), \
             mock.patch("ai_agents.llm.chat_completion", side_effect=fake_chat) as mc:
            result = self.coordinator.process_dialogue(
                "最近压力好大，晚上睡不着，有点难过"
            )
        self.assertEqual(result["risk_level"], "yellow")
        self.assertFalse(result["is_vetoed"])

        log = self.coordinator.get_collaboration_log()
        emp = [m["payload"] for m in log
               if m["msg_type"] == "DISCUSS_RESPONSE" and m["sender"] == "empathy_companion"]
        cbt = [m["payload"] for m in log
               if m["msg_type"] == "DISCUSS_RESPONSE" and m["sender"] == "cognitive_behavior"]
        self.assertTrue(emp and cbt, "yellow 的两类智能体都应有 DISCUSS_RESPONSE")
        # 关键：结构化产出来自 LLM（带 （LLM） 标记），而非规则版占位
        self.assertIn("（LLM）", emp[0].get("emotion_reflection", ""))
        self.assertIn("（LLM）", cbt[0].get("reframed_thought", ""))
        # 两类 agent 各自独立调用 + 协调器整合 = 至少 3 次
        self.assertGreaterEqual(mc.call_count, 3)

    def test_offline_assemble_uses_agent_fields(self):
        """离线（未启用 LLM）时，最终回复由各智能体结构化字段组装，
        而非只返回固定 RESPONSE_TEMPLATES"""
        with mock.patch("ai_agents.llm.is_enabled", return_value=False):
            result = self.coordinator.process_dialogue("最近压力好大，晚上睡不着")
        self.assertEqual(result["risk_level"], "yellow")
        self.assertFalse(result["is_vetoed"])
        # 组装必含 CBT 智能体规则载荷里的认知重建与行为建议
        self.assertIn("换个角度看", result["response_text"])
        self.assertTrue(
            any(k in result["response_text"] for k in ("我暂时还没学会", "先休息")),
            result["response_text"],
        )

    def test_green_keeps_single_llm_call_contract(self):
        """green（仅共情陪伴 1 个智能体）维持单次 LLM 调用契约，不触发逐 agent 生成"""
        with mock.patch("ai_agents.llm.is_enabled", return_value=True), \
             mock.patch("ai_agents.llm.chat_completion",
                        return_value="真替你开心，是用功换来的！") as mc:
            result = self.coordinator.process_dialogue("今天考试考了100分，好开心")
        self.assertEqual(result["risk_level"], "green")
        self.assertEqual(mc.call_count, 1)
        self.assertEqual(result["response_text"], "真替你开心，是用功换来的！")

    def test_multiagent_integrate_revision_messages_emitted(self):
        """优先级四：多智能体协商时，真正发出并回收 REVISION_NOTICE 与
        逐智能体的 INTEGRATE_REQUEST / INTEGRATE_RESPONSE 报文，
        而不是只停留在脚本里宣称的协议类型。"""
        with mock.patch("ai_agents.llm.is_enabled", return_value=False):
            result = self.coordinator.process_dialogue(
                "最近压力好大，晚上睡不着，有点难过"
            )
        self.assertEqual(result["risk_level"], "yellow")
        msgs = self.coordinator.get_collaboration_log()

        def has(sender, mtype):
            return any(m["sender"] == sender and m["msg_type"] == mtype for m in msgs)

        # 修订：协调器向 all 广播一次
        self.assertTrue(has("coordinator", "REVISION_NOTICE"), "应广播 REVISION_NOTICE")
        # 整合：协调器向每个路由智能体发 INTEGRATE_REQUEST，且各智能体回 INTEGRATE_RESPONSE
        for agent in ("empathy_companion", "cognitive_behavior"):
            self.assertTrue(
                has("coordinator", "INTEGRATE_REQUEST"),
                f"协调器应向 {agent} 等路由智能体发 INTEGRATE_REQUEST",
            )
            self.assertTrue(
                has(agent, "INTEGRATE_RESPONSE"),
                f"{agent} 应返回 INTEGRATE_RESPONSE",
            )
        # INTEGRATE_RESPONSE：仅限路由智能体返回的（协调器的最终广播不是意见回传）
        integ_resp = [m for m in msgs
                      if m["msg_type"] == "INTEGRATE_RESPONSE"
                      and m["sender"] in ("empathy_companion", "cognitive_behavior")]
        self.assertEqual(len(integ_resp), 2, "两个路由智能体都应回传 INTEGRATE_RESPONSE")
        for m in integ_resp:
            self.assertIn("final_opinion", m["payload"])
            self.assertIn("revised_note", m["payload"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
