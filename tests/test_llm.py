"""
tests/test_llm.py
验证 MindIsle 大模型接入层（ai_agents/llm.py）及其与协调器的集成。

覆盖分支：
  [配置层] 默认配置、启用判定（需要 LLM_ENABLED=true 且配置了 API Key）；
  [调用层] 未配置 Key 时抛出 LLMError、safe_chat 兜底回退；
  [协调器] 未启用 LLM 时保持模板兜底（不破坏原有行为）；
  [接入后] 启用 LLM 时 process_dialogue 生成的内容来自大模型；
  [记忆]   history 多轮历史正确拼入 messages，且当前输入作为最后一条 user。

运行方式（在项目根目录下）：
  python -m unittest tests.test_llm -v
  python -m unittest discover -s tests -v
"""
import os
import sys
import unittest
from contextlib import contextmanager
from unittest import mock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_agents.llm as llm
from ai_agents.coordinator import MultiAgentCoordinator

# 测试时统一清空，避免依赖真实配置 / 污染环境
_LLM_ENV_KEYS = ("LLM_ENABLED", "LLM_API_KEY", "LLM_API_BASE", "LLM_MODEL", "LLM_TIMEOUT")


@contextmanager
def _clean_llm_env():
    """上下文管理器：临时移除 llm 相关环境变量，退出后恢复原值。"""
    backup = {k: os.environ.pop(k) for k in _LLM_ENV_KEYS if k in os.environ}
    try:
        yield
    finally:
        for key, value in backup.items():
            os.environ[key] = value


class TestLLMConfig(unittest.TestCase):
    def test_default_config(self):
        """无任何环境变量时给出 DeepSeek 默认值且不启用。"""
        with _clean_llm_env():
            cfg = llm.get_config()
            self.assertEqual(cfg["base"], llm.DEFAULT_BASE_URL)
            self.assertEqual(cfg["model"], llm.DEFAULT_MODEL)
            self.assertEqual(cfg["key"], "")
            self.assertFalse(cfg["enabled"])
            self.assertFalse(llm.is_enabled())

    def test_is_enabled_needs_both_flag_and_key(self):
        """仅 LLM_ENABLED=true 但没有 Key 不得启用；补上 Key 后启用。"""
        with _clean_llm_env():
            with mock.patch.dict(os.environ, {"LLM_ENABLED": "true"}, clear=False):
                self.assertFalse(llm.is_enabled())
            with mock.patch.dict(
                os.environ, {"LLM_ENABLED": "true", "LLM_API_KEY": "sk-test"}, clear=False
            ):
                self.assertTrue(llm.is_enabled())


class TestLLMCall(unittest.TestCase):
    def test_chat_completion_requires_key(self):
        """未配置 API Key 时调用必须抛出 LLMError（不发起网络请求）。"""
        with _clean_llm_env():
            with self.assertRaises(llm.LLMError):
                llm.chat_completion([{"role": "user", "content": "你好"}])

    def test_safe_chat_falls_back_when_disabled(self):
        """未启用 LLM 时 safe_chat 直接返回 fallback，不产生网络请求。"""
        with _clean_llm_env():
            with mock.patch("ai_agents.llm.chat_completion") as mock_chat:
                out = llm.safe_chat(
                    [{"role": "user", "content": "你好"}], fallback="模板兜底话术"
                )
                mock_chat.assert_not_called()
            self.assertEqual(out, "模板兜底话术")

    def test_safe_chat_falls_back_on_error(self):
        """服务端报错时 safe_chat 回退 fallback，不向上抛异常影响主流程。"""
        with _clean_llm_env():
            with mock.patch.dict(
                os.environ, {"LLM_ENABLED": "true", "LLM_API_KEY": "sk-test"}, clear=False
            ):
                with mock.patch(
                    "ai_agents.llm.chat_completion",
                    side_effect=llm.LLMError("network down"),
                ) as mock_chat, mock.patch("builtins.print") as mock_print:
                    out = llm.safe_chat(
                        [{"role": "user", "content": "你好"}], fallback="模板兜底话术"
                    )
                    mock_chat.assert_called_once()
                    mock_print.assert_called_once()  # 应有一条回退警告日志
                self.assertEqual(out, "模板兜底话术")


class TestCoordinatorLLMIntegration(unittest.TestCase):
    def setUp(self):
        self.coordinator = MultiAgentCoordinator()

    def test_falls_back_to_template_when_llm_disabled(self):
        """未启用 LLM 时行为与接入前完全一致：使用内置分级模板。"""
        with _clean_llm_env(), mock.patch("ai_agents.llm.chat_completion") as mock_chat:
            result = self.coordinator.process_dialogue("今天考试考了 100 分，好开心")
            mock_chat.assert_not_called()
        self.assertEqual(result["risk_level"], "green")
        self.assertEqual(result["action"], "NORMAL_TALK")
        self.assertFalse(result["is_vetoed"])

    def test_response_comes_from_llm_when_enabled(self):
        """启用 LLM 后，最终回复文本应来自大模型输出。"""
        with _clean_llm_env():
            with mock.patch("ai_agents.llm.is_enabled", return_value=True), \
                 mock.patch(
                     "ai_agents.llm.chat_completion",
                     return_value="哇，考了满分！真替你开心，是用功换来的结果吧～",
                 ) as mock_chat:
                result = self.coordinator.process_dialogue("今天考试考了 100 分，好开心")
                mock_chat.assert_called_once()
        self.assertEqual(result["response_text"], "哇，考了满分！真替你开心，是用功换来的结果吧～")
        # 最后一条 messages 应为当前用户输入
        messages = mock_chat.call_args.args[0]
        self.assertEqual(messages[-1]["role"], "user")
        self.assertEqual(messages[-1]["content"], "今天考试考了 100 分，好开心")

    def test_history_passed_to_llm(self):
        """多轮历史应以 system → user/assistant 交替顺序拼入，并以当前输入收尾。"""
        history = [
            {"role": "user", "content": "最近压力好大"},
            {"role": "assistant", "content": "辛苦了，愿意和我多说说吗？"},
        ]
        with _clean_llm_env():
            with mock.patch("ai_agents.llm.is_enabled", return_value=True), \
                 mock.patch(
                     "ai_agents.llm.chat_completion", return_value="我在听哦～",
                 ) as mock_chat:
                result = self.coordinator.process_dialogue("我有点睡不着", history=history)
        self.assertEqual(result["response_text"], "我在听哦～")
        messages = mock_chat.call_args.args[0]
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("压力好大", messages[1]["content"])
        self.assertIn("愿意和我多说说吗", messages[2]["content"])
        self.assertEqual(messages[-1]["content"], "我有点睡不着")

    def test_red_still_uses_emergency_template(self):
        """高危（red）不交给 LLM 自由发挥，必须输出含热线的应急话术。"""
        with _clean_llm_env():
            with mock.patch("ai_agents.llm.is_enabled", return_value=True), \
                 mock.patch("ai_agents.llm.chat_completion") as mock_chat:
                result = self.coordinator.process_dialogue("我真的不想活了，想跳楼")
                mock_chat.assert_not_called()
        self.assertTrue(result["is_vetoed"])
        self.assertEqual(result["action"], "TRIGGER_EMERGENCY_POPUP")
        self.assertIn("400-161-9995", result["response_text"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

