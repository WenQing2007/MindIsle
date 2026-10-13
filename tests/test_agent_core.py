"""
tests/test_agent_core.py
验证 MindIsle 核心协调器 ACPSMultiAgentOrchestrator 的“安全评估一票否决”机制。

覆盖分支：
  [分支 1] 危险输入（想死 / 自杀 / 跳楼 / 割腕 / 被打了 / 霸凌）
           → is_vetoed=True，risk_level=red，action=TRIGGER_EMERGENCY_POPUP，
             response_text 必须包含 24 小时心理援助热线。
  [分支 2] 普通倾诉输入 → is_vetoed=False，走正常共情陪伴流程（NORMAL_TALK）。

运行方式（在项目根目录下）：
  python tests/test_agent_core.py
  python -m unittest discover -s tests -v
"""

import os
import sys
import unittest

# 将项目根目录加入 sys.path，保证直接运行本脚本时也能导入 src.agent_core
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from src.agent_core import ACPSMultiAgentOrchestrator, EMERGENCY_HOTLINE
except ImportError:  # 兜底：以 python -m unittest 运行且 src 已在路径上时
    from agent_core import ACPSMultiAgentOrchestrator, EMERGENCY_HOTLINE


class TestACPSOneVetoMechanism(unittest.TestCase):
    """ACPs 多智能体安全一票否决机制测试"""

    def setUp(self):
        # 每个用例使用独立实例，确保默认配置不被篡改
        self.orchestrator = ACPSMultiAgentOrchestrator()

    # ---------------- 分支 1：危险输入 → 一票否决 ----------------
    def test_danger_keywords_trigger_veto(self):
        """命中高危关键词时，必须触发一票否决并返回 24 小时心理援助热线"""
        cases = [
            "我真的不想活了，想死",
            "他这几天一直说要自杀",
            "我现在很想跳楼",
            "她昨夜拿刀割腕了",
            "我在学校天天被霸凌",
            "我在学校被打了，很害怕",
        ]
        for text in cases:
            with self.subTest(user_text=text):
                result = self.orchestrator.process_dialogue(text)
                self.assertTrue(result["is_vetoed"], f"该输入应被一票否决: {text}")
                self.assertEqual(result["risk_level"], "red")
                self.assertEqual(result["action"], "TRIGGER_EMERGENCY_POPUP")
                # 应急回复必须包含 24 小时心理援助热线
                self.assertIn(EMERGENCY_HOTLINE, result["response_text"])

    def test_check_safety_marks_risk_and_veto(self):
        """check_safety 对危险输入应标记风险并置起 veto 标志"""
        result = self.orchestrator.check_safety("我现在只想跳楼")
        self.assertTrue(result["is_risk"])
        self.assertEqual(result["risk_level"], "red")
        self.assertTrue(result["veto"])
        self.assertEqual(result["keyword"], "跳楼")
        self.assertIn("跳楼", result["reason"])

    # ---------------- 分支 2：普通输入 → 共情陪伴 ----------------
    def test_normal_input_not_vetoed(self):
        """普通倾诉输入不触发否决，走正常共情陪伴流程"""
        cases = [
            "今天考试没考好，有点难过",
            "我和最好的朋友吵架了",
            "最近总是睡不好，好累",
        ]
        for text in cases:
            with self.subTest(user_text=text):
                result = self.orchestrator.process_dialogue(text)
                self.assertFalse(result["is_vetoed"])
                self.assertEqual(result["risk_level"], "green")
                self.assertEqual(result["action"], "NORMAL_TALK")
                # 正常陪伴话术不应夹带应急热线
                self.assertNotIn(EMERGENCY_HOTLINE, result["response_text"])
                self.assertTrue(result["response_text"])

    def test_check_safety_green_when_no_risk(self):
        """无风险输入时 check_safety 返回绿色且不带 veto"""
        result = self.orchestrator.check_safety("今天天气真好")
        self.assertFalse(result["is_risk"])
        self.assertFalse(result["veto"])
        self.assertEqual(result["risk_level"], "green")
        self.assertIsNone(result["keyword"])

    # ---------------- 可配置性 ----------------
    def test_custom_hotline_and_keywords(self):
        """支持自定义高危关键词表与心理援助热线"""
        orchestrator = ACPSMultiAgentOrchestrator(
            high_risk_keywords=["不想活了"],
            emergency_hotline="12345-6",
        )
        danger = orchestrator.process_dialogue("我有点不想活了")
        self.assertTrue(danger["is_vetoed"])
        self.assertIn("12345-6", danger["response_text"])
        self.assertNotIn(EMERGENCY_HOTLINE, danger["response_text"])

        normal = orchestrator.process_dialogue("今天有点难过")
        self.assertFalse(normal["is_vetoed"])
        self.assertEqual(normal["action"], "NORMAL_TALK")


def run_demo() -> None:
    """打印两条分支的演示输出，便于人工快速查看。"""
    orchestrator = ACPSMultiAgentOrchestrator()
    print("=" * 64)
    print("[演示] 分支 1：危险输入 -> 一票否决返回热线")
    print(orchestrator.process_dialogue("我真的不想活了，想跳楼"))
    print("=" * 64)
    print("[演示] 分支 2：普通输入 -> 共情陪伴")
    print(orchestrator.process_dialogue("今天考试没考好，有点难过"))
    print("=" * 64)
    print("（如需完整单测报告，请执行：python -m unittest discover -s tests -v）")


if __name__ == "__main__":
    run_demo()
    unittest.main(verbosity=2)
