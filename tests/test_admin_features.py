"""tests/test_admin_features.py
验证本轮新增：后台管理数据库能力、情绪识别、风险关键词可配置与协调器契约不被破坏。

运行：python -m pytest tests/test_admin_features.py -v
"""
import os
import sys
import tempfile
import unittest
from contextlib import contextmanager
from unittest import mock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend import database as db
from backend import risk
from backend import emotion as emotion_mod

_LLM_ENV_KEYS = ("LLM_ENABLED", "LLM_API_KEY", "LLM_API_BASE", "LLM_MODEL", "LLM_TIMEOUT")


@contextmanager
def _clean_llm_env():
    backup = {k: os.environ.pop(k) for k in _LLM_ENV_KEYS if k in os.environ}
    try:
        yield
    finally:
        for key, value in backup.items():
            os.environ[key] = value


@contextmanager
def _temp_db():
    tmp = tempfile.mkstemp(prefix="mindisle_test_", suffix=".db")
    os.close(tmp[0])
    with mock.patch.object(db, "DB_PATH", tmp[1]):
        db.init_db()
        try:
            yield db
        finally:
            os.remove(tmp[1])


class TestEmotion(unittest.TestCase):
    def test_happy(self):
        r = emotion_mod.detect("今天考了100分，太开心了！")
        self.assertEqual(r["emotion"], "happy")
        self.assertEqual(r["label_cn"], "开心")

    def test_angry(self):
        r = emotion_mod.detect("气死我了，他那样对我！")
        self.assertEqual(r["emotion"], "angry")

    def test_anxious(self):
        r = emotion_mod.detect("最近压力好大，好焦虑，担心考不好")
        self.assertIn(r["emotion"], ("anxious", "sad"))
        self.assertTrue(r["matched"])

    def test_neutral_fallback(self):
        r = emotion_mod.detect("@@@@@")
        self.assertEqual(r["emotion"], "neutral")


class TestRiskConfigurable(unittest.TestCase):
    def test_effective_default_equals_builtin(self):
        with _temp_db(), mock.patch("backend.database.list_enabled_risk_keywords", return_value=[]):
            eff = risk.effective_keywords()
        self.assertEqual(eff, {lv: list(ws) for lv, ws in risk.KEYWORD_MAP.items()})

    def test_custom_keyword_affects_assess_and_cleanup(self):
        with _temp_db():
            kid, err = db.add_risk_keyword("red", "魔法测试自杀词")
            self.assertIsNone(err)
            r = risk.assess("我现在魔法测试自杀词了")
            self.assertEqual(r["level"], "red")
            self.assertIn("魔法测试自杀词", r["matched"])
            self.assertTrue(db.delete_risk_keyword(kid))

    def test_get_hotline_default(self):
        with _temp_db():
            self.assertEqual(risk.get_hotline(), "400-161-9995")
            db.set_config("crisis_hotline", "400-000-0000")
            self.assertEqual(risk.get_hotline(), "400-000-0000")


class TestDatabaseAdmin(unittest.TestCase):
    def test_user_crud(self):
        with _temp_db():
            uid, err = db.admin_create_account("teacher", "teach999", "123456")
            self.assertIsNone(err)
            rows = db.list_accounts(role="teacher")
            self.assertTrue(any(r["username"] == "teach999" for r in rows))
            _, err2 = db.admin_create_account("teacher", "teach999", "123456")
            self.assertEqual(err2, "用户名已被占用")
            self.assertTrue(db.update_account_password(uid, "abcdef"))
            self.assertTrue(db.update_account_role(uid, "admin"))
            self.assertTrue(db.delete_account(uid))

    def test_resource_crud(self):
        with _temp_db():
            rid = db.add_resource("放松训练", "relax", "/audio/1.mp3", "说明", "published")
            self.assertTrue(any(r["id"] == rid for r in db.list_resources()))
            self.assertTrue(db.update_resource(rid, status="unpublished"))
            self.assertTrue(db.delete_resource(rid))
            self.assertIsNone(db.get_resource(rid))

    def test_config_and_logs(self):
        with _temp_db():
            db.set_config("crisis_hotline", "400-000-0000")
            self.assertEqual(db.get_config("crisis_hotline"), "400-000-0000")
            db.add_login_log("admin", "admin", True, "登录成功", user_id=3)
            db.add_operation_log("admin", "admin", "配置热线", "400", user_id=3)
            self.assertEqual(len(db.list_login_logs()), 1)
            self.assertEqual(len(db.list_operation_logs()), 1)


class TestCoordinatorIntegration(unittest.TestCase):
    def test_default_routing_unchanged(self):
        from ai_agents.coordinator import MultiAgentCoordinator
        with _clean_llm_env(), _temp_db():
            r = MultiAgentCoordinator().process_dialogue("最近压力好大，晚上睡不着，有点难过")
            self.assertEqual(r["routed_agents"], ["empathy_companion", "cognitive_behavior"])

    def test_extra_agents_join_negotiation_not_routing(self):
        from ai_agents.coordinator import MultiAgentCoordinator, MsgType
        with _clean_llm_env(), _temp_db(), \
             mock.patch.dict(os.environ, {"AGENT_EXTRA_ROLES": "all"}, clear=False):
            c = MultiAgentCoordinator()
            r = c.process_dialogue("最近压力好大，晚上睡不着，有点难过")
            # 对外路由保持既有契约，不受补充智能体影响
            self.assertEqual(r["routed_agents"], ["empathy_companion", "cognitive_behavior"])
            log = c.get_collaboration_log()
            senders = {m["sender"] for m in log if m["msg_type"] == MsgType.DISCUSS_RESPONSE}
            self.assertIn("developmental_psychology", senders)
            self.assertIn("home_school_context", senders)


if __name__ == "__main__":
    unittest.main(verbosity=2)
