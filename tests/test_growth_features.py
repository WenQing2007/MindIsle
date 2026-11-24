"""tests/test_growth_features.py
覆盖本轮新增的学生成长功能（情景演练 / 量表测评 / 预警复核与阈值）。

运行：python -m pytest tests/test_growth_features.py -v
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

# 避免在收集阶段 import backend.app（其 _load_dotenv 会写真实 LLM 环境变量，
# 污染后续运行测试导致误用真实大模型）；改为在测试方法内延迟 import。
# 同时在收集阶段清除一次性 LLM 环境，保证其余用例走模板兜底、快速稳定。
os.environ.pop("LLM_ENABLED", None)
os.environ.pop("LLM_API_KEY", None)
os.environ.pop("LLM_API_BASE", None)
os.environ.pop("LLM_MODEL", None)
os.environ.pop("LLM_TIMEOUT", None)


@contextmanager
def _temp_db():
    tmp = tempfile.mkstemp(prefix="mindisle_growth_", suffix=".db")
    os.close(tmp[0])
    with mock.patch.object(db, "DB_PATH", tmp[1]):
        db.init_db()
        db.seed_default_users()
        try:
            yield db
        finally:
            os.remove(tmp[1])


class TestScenarioRecord(unittest.TestCase):
    def test_add_and_level(self):
        with _temp_db():
            rid = db.add_scenario_record(1, "exam", "考前焦虑", good=2, mid=1, bad=0)
            self.assertTrue(rid > 0)
            recs = db.get_scenario_records(1)
            self.assertEqual(recs[0]["level"], "A")
            self.assertEqual(recs[0]["score"], 0.83)
            stats = db.get_student_scenario_stats(1)
            self.assertEqual(stats["cnt"], 1)
            self.assertEqual(stats["best"], "A")

    def test_poor_level(self):
        with _temp_db():
            db.add_scenario_record(1, "friend", "朋友矛盾", good=0, mid=0, bad=2)
            recs = db.get_scenario_records(1)
            self.assertEqual(recs[0]["level"], "C")
            self.assertEqual(recs[0]["score"], 0.0)


class TestAssessmentRecord(unittest.TestCase):
    def test_add_and_list(self):
        with _temp_db():
            rid = db.add_assessment_record(1, "phq9", "PHQ-9", 7, "mild", "轻度")
            self.assertTrue(rid > 0)
            recs = db.get_assessment_records(1)
            self.assertEqual(len(recs), 1)
            self.assertEqual(recs[0]["scale_id"], "phq9")

    def test_isolation_between_students(self):
        with _temp_db():
            s2 = db.add_student("李四", gender="女", age=15, grade="高二(2)班")
            db.add_assessment_record(1, "phq9", "PHQ-9", 3, "none", "无明显")
            db.add_assessment_record(s2, "gad7", "GAD-7", 12, "moderate", "中度")
            self.assertEqual(len(db.get_assessment_records(1)), 1)
            self.assertEqual(len(db.get_assessment_records(s2)), 1)


class TestWarningReviewAndThreshold(unittest.TestCase):
    def test_min_level_default(self):
        with _temp_db():
            self.assertEqual(db.get_warning_min_level(), "medium")
            self.assertTrue(db.set_warning_min_level("high"))
            self.assertEqual(db.get_warning_min_level(), "high")
            self.assertFalse(db.set_warning_min_level("low"))  # 非法值被拒

    def test_review_roundtrip(self):
        with _temp_db():
            # 学生1已由 seed 建好，为其建一个会话再写一条风险记录
            sid = db.create_session(1)
            db.add_risk_assessment(sid, "high", score=0.7, indicators="被欺负")
            history = db.get_student_risk_history(1)
            assessment_id = history[0]["id"]
            self.assertTrue(assessment_id)
            # get_risk_by_id 关联出学生
            row = db.get_risk_by_id(assessment_id)
            self.assertEqual(row["student_id"], 1)
            rid = db.add_warning_review(assessment_id, 1, "王老师", "followed_up", "已家访")
            self.assertTrue(rid > 0)
            review = db.get_latest_warning_review(1)
            self.assertEqual(review["status"], "followed_up")
            self.assertEqual(review["teacher_name"], "王老师")
            # 复核后再取仍是最新
            db.add_warning_review(assessment_id, 1, "李老师", "reviewed", "再次确认")
            latest = db.get_latest_warning_review(1)
            self.assertEqual(latest["status"], "reviewed")


class TestAppRoutes(unittest.TestCase):
    def _app(self):
        import os as _os
        for k in ("LLM_ENABLED", "LLM_API_KEY"):
            _os.environ.pop(k, None)
        from backend import app as _app_mod
        return _app_mod

    def test_routes_registered(self):
        paths = [r.path for r in self._app().app.routes]
        self.assertIn("/api/scenario/record", paths)
        self.assertIn("/api/scenario/records", paths)
        self.assertIn("/api/assessment/record", paths)
        self.assertIn("/api/assessment/records", paths)
        self.assertIn("/api/resources", paths)
        self.assertIn("/api/teacher/warning-config", paths)

    def test_warnings_contract(self):
        # 只读调用真实接口（不写库），验证返回结构包含复核字段
        from fastapi.testclient import TestClient
        resp = TestClient(self._app().app).get("/api/teacher/warnings")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["code"], 200)
        data = resp.json()["data"]
        self.assertIsInstance(data, list)
        if data:
            first = data[0]
            for key in ("assessment_id", "review_status", "review_note", "review_teacher"):
                self.assertIn(key, first)

    def test_resources_contract(self):
        from fastapi.testclient import TestClient
        resp = TestClient(self._app().app).get("/api/resources")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["code"], 200)
        self.assertIn("resources", resp.json()["data"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
