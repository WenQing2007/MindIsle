"""
tests/test_risk_boundaries.py
面向 agent（风险评估 / 安全评估 / 一票否决）方向的**边界与健壮性**测试。

覆盖重点：
  [健壮性]   空串 / 全空白 / None / 纯标点 / 纯符号 / 纯数字 / URL /
             超长输入等非正常输入，必须安全降级为 green 且不抛异常；
  [高危触发] 仅含单个短危险词的输入（'想死' / '不想活' / '跳楼'）→ red，
             触发一票否决并返回 24h 热线；
  [多级叠加] 同一句同时命中多级关键词时，按**最高**风险等级裁定（安全优先）；
  [结果契约] score / level_db / matched / matched_level 之间的映射一致性；
  [路由/动作] 四级风险 → 正确的智能体路由表与系统动作；
  [已知误判] 关键词重叠导致 '怕考试 / 害怕考试' 被偏高判为 orange
             （记录当前行为作为后续优化输入，不改变设计意图）。

运行方式（在项目根目录下）：
  python -m unittest discover -s tests -v
  python -m pytest tests/test_risk_boundaries.py -v
"""
import os
import sys
import unittest
from contextlib import contextmanager
from unittest import mock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend import risk
from ai_agents.coordinator import (
    ACTION_MAP,
    EMERGENCY_HOTLINE,
    RISK_ROUTING,
    MultiAgentCoordinator,
)

# 测试时统一清空 llm 相关环境变量，避免误启用网络请求
_LLM_ENV_KEYS = ("LLM_ENABLED", "LLM_API_KEY", "LLM_API_BASE", "LLM_MODEL", "LLM_TIMEOUT")


@contextmanager
def _clean_llm_env():
    """临时移除 llm 相关环境变量，退出后恢复原值。"""
    backup = {k: os.environ.pop(k) for k in _LLM_ENV_KEYS if k in os.environ}
    try:
        yield
    finally:
        for key, value in backup.items():
            os.environ[key] = value


class TestRiskRobustness(unittest.TestCase):
    """非正常输入必须安全降级，绝不抛异常。"""

    def setUp(self):
        self.coordinator = MultiAgentCoordinator()

    def test_risk_module_weird_inputs_do_not_crash(self):
        """backend/risk.assess 对各类非正常输入不抛异常，且默认降为 green。"""
        cases = [
            "", "   ", "　　", "。。。", "！@#￥", "。。。？",
            "99%", "12345", "https://example.com/a?b=1", "@#$%^&*",
            "x" * 5000, None,
        ]
        for value in cases:
            with self.subTest(value=value):
                result = risk.assess(value)
                self.assertEqual(result["level"], "green")
                self.assertEqual(result["score"], 0.1)
                self.assertEqual(result["matched"], [])

    def test_coordinator_weird_inputs_do_not_crash(self):
        """协调器对非正常输入安全降级为 green 正常陪伴，不触发否决。"""
        cases = ["", "   ", "。。。", "!@#", "99%", "https://example.com", "x" * 5000, None]
        for value in cases:
            with self.subTest(value=value):
                result = self.coordinator.process_dialogue(value)
                self.assertEqual(result["risk_level"], "green")
                self.assertFalse(result["is_vetoed"])
                self.assertEqual(result["action"], "NORMAL_TALK")
                self.assertTrue(result["response_text"])

    def test_long_input_does_not_doom_risk(self):
        """超长输入（模拟复制粘贴大段话）能正常走到评估，不因长度异常。"""
        text = ("我真的压力好大，" * 300) + "，晚上睡不着。"
        result = self.coordinator.process_dialogue(text)
        self.assertEqual(result["risk_level"], "yellow")
        self.assertFalse(result["is_vetoed"])


class TestRiskHighestPriority(unittest.TestCase):
    """同一句命中多级关键词时，按最高风险等级裁定（安全优先）。"""

    def setUp(self):
        self.coordinator = MultiAgentCoordinator()

    def test_matrix_top_level_wins(self):
        """green+yellow→yellow；含 orange→orange；任何含红词→red。"""
        cases = [
            ("虽然压力大但今天很开心", "yellow", "开心", False),
            ("确实被欺负了很难受但妈妈说会帮我", "orange", "欺负", False),
            ("最近压力大但要是真要被威胁就报警", "orange", "威胁", False),
            ("压力好大，有时候真想跳楼", "red", "跳楼", True),
            ("今天很开心但难过的事也常有", "yellow", "难过", False),
        ]
        for text, level, kw, veto in cases:
            with self.subTest(text=text):
                result = self.coordinator.process_dialogue(text)
                self.assertEqual(result["risk_level"], level)
                self.assertEqual(result["is_vetoed"], veto)
                self.assertIn(kw, result["risk_matched"])


class TestRiskSingleSignalVeto(unittest.TestCase):
    """极短、无上下文、仅含单个危险词的输入也必须一票否决。"""

    def setUp(self):
        self.coordinator = MultiAgentCoordinator()

    def test_short_danger_words_trigger_veto(self):
        """无论单词还是嵌入句中，命中高危词即 veto + 热线。"""
        cases = ["想死", "不想活", "跳楼", "自残", "割腕", "我特别想死"]
        for text in cases:
            with self.subTest(text=text):
                result = self.coordinator.process_dialogue(text)
                self.assertTrue(result["is_vetoed"])
                self.assertEqual(result["risk_level"], "red")
                self.assertEqual(result["action"], "TRIGGER_EMERGENCY_POPUP")
                self.assertIn(EMERGENCY_HOTLINE, result["response_text"])
                self.assertEqual(result["hotline"], EMERGENCY_HOTLINE)

    def test_veto_hotline_is_returned_always(self):
        """red 时 hotline 字段不应为空；非 red 时 hotline 为 None。"""
        vetoed = self.coordinator.process_dialogue("我不想活了")
        self.assertEqual(vetoed["hotline"], EMERGENCY_HOTLINE)
        normal = self.coordinator.process_dialogue("今天考试考了 100 分")
        self.assertIsNone(normal["hotline"])


class TestRiskResultContract(unittest.TestCase):
    """评估返回结构各字段之间的一致性契约。"""

    def test_score_and_db_level_map(self):
        """level 与 score、level_db 保持映射一致。"""
        expect = {
            "green": (0.1, "low"),
            "yellow": (0.35, "medium"),
            "orange": (0.7, "high"),
            "red": (1.0, "critical"),
        }
        probes = {
            "green": "今天好开心呀",
            "yellow": "最近压力好大",
            "orange": "我被同学欺负了，好害怕",
            "red": "我真的不想活了",
        }
        for level, text in probes.items():
            with self.subTest(level=level):
                r = risk.assess(text)
                self.assertEqual(r["level"], level)
                self.assertEqual(r["score"], expect[level][0])
                self.assertEqual(r["level_db"], expect[level][1])
                self.assertEqual(r["matched_level"], level)
                self.assertTrue(r["matched"], "应至少命中一个关键词")

    def test_matched_contains_all_hits(self):
        """matched 应包含所有命中关键词。"""
        r = risk.assess("最近压力大又有点难过")
        self.assertIn("压力", r["matched"])
        self.assertIn("难过", r["matched"])


class TestCoordinatorRoutingContract(unittest.TestCase):
    """四级风险 → 智能体路由与系统动作的一致性。"""

    def setUp(self):
        self.coordinator = MultiAgentCoordinator()

    def test_routing_table_and_actions(self):
        routing = {
            "green": ["empathy_companion"],
            "yellow": ["empathy_companion", "cognitive_behavior"],
            "orange": ["empathy_companion", "cognitive_behavior", "scenario_director"],
            "red": ["safety_assessor"],
        }
        actions = {
            "green": "NORMAL_TALK",
            "yellow": "WARN_TEACHER_ANONYMOUS",
            "orange": "NOTIFY_TEACHER",
            "red": "TRIGGER_EMERGENCY_POPUP",
        }
        for level in routing:
            with self.subTest(level=level):
                self.assertEqual(
                    MultiAgentCoordinator().dispatch(level), routing[level], "路由表不一致"
                )
                self.assertEqual(MultiAgentCoordinator().decide_action(level), actions[level])

    def test_unknown_level_falls_back_to_green(self):
        """未知等级应安全回退 green 路由，不抛异常。"""
        self.assertEqual(
            MultiAgentCoordinator().dispatch("unknown_level"), RISK_ROUTING["green"]
        )

    def test_full_pipeline_route_and_action_consistency(self):
        """端到端：评估→路由→动作 三者一致。"""
        samples = {
            "今天考试考了 100 分，好开心": "green",
            "最近压力好大好难过": "yellow",
            "我被同学欺负了，很害怕": "orange",
            "我真的不想活了一了百了": "red",
        }
        for text, level in samples.items():
            with self.subTest(level=level):
                result = self.coordinator.process_dialogue(text)
                self.assertEqual(result["risk_level"], level)
                self.assertEqual(result["action"], ACTION_MAP[level])
                self.assertEqual(result["routed_agents"], RISK_ROUTING[level])


class TestKnownOverlapEdgeCase(unittest.TestCase):
    """
    已知误判点（不改变「安全优先」设计，仅固定并记录当前行为）：

    关键词表把 '害怕 / 怕' 归为 orange（受欺凌/恐惧），把 '害怕考试' 归为 yellow。
    由于 '害怕考试' 中同时包含 '害怕'、'怕'，会导致 '我害怕考试' 被偏高判为 orange
    （需通知心理教师），而不是语义更贴切的 yellow（考试焦虑）。

    这里显式固定当前输出，防止未来改动无意识地改变行为；同时可作后续优化输入：
    建议对关键词做「最长匹配优先 / 否定排除」处理。
    """

    def setUp(self):
        self.coordinator = MultiAgentCoordinator()

    def test_fear_of_exam_currently_flagged_orange(self):
        result = self.coordinator.process_dialogue("我害怕考试，怕考不好")
        self.assertEqual(result["risk_level"], "orange")
        self.assertEqual(result["action"], ACTION_MAP["orange"])


if __name__ == "__main__":
    unittest.main(verbosity=2)