
## 📊 `backend/database.py` 设计总览

### 技术选型
- **SQLite** —— Python 内置，零依赖，文件型数据库，非常适合桌面应用分发
- 数据库文件自动创建在 `data/mindisle.db`

### 5 张核心表

| 表名 | 用途 | 关键字段 |
|---|---|---|
| `student` | 学生信息 | name, gender, age, school, grade |
| `chat_session` | 聊天会话 | 关联 student_id，记录开始/结束时间 |
| `chat_message` | 聊天记录 | role(user/assistant/system), content, emotion |
| `risk_assessment` | 风险评估 | risk_level(low/medium/high/critical), score, indicators |
| `report` | 报告记录 | report_type(counseling/warning/weekly), content, file_path |

### 表关系（级联删除）
```
student ──1:N──> chat_session ──1:N──> chat_message
                            ├──1:N──> risk_assessment  
                            └──1:N──> report
```
删除学生时，所有关联的会话、消息、风险、报告会**自动删除**（`ON DELETE CASCADE`）。

### 提供的 API 函数（共 20+ 个）

- **学生**：`add_student` / `get_student` / `get_all_students` / `update_student` / `delete_student`
- **会话**：`create_session` / `end_session` / `get_session` / `get_sessions_by_student`
- **消息**：`add_message` / `get_messages` / `get_all_messages_for_student`
- **风险**：`add_risk_assessment` / `get_latest_risk` / `get_risk_by_session` / `get_student_risk_history`
- **报告**：`add_report` / `get_report` / `get_reports_by_session` / `get_reports_by_student`
- **工具**：`init_db()`（初始化，程序启动调用）、`get_stats()`（全局统计）

### 使用示例（其他模块只需这样调用）
```python
from backend import database as db

db.init_db()                                    # 程序启动时调用一次
sid   = db.add_student("小明", age=14)          # 新增学生
seid  = db.create_session(sid)                  # 开始会话
db.add_message(seid, "user", "我压力很大")
db.add_risk_assessment(seid, "high", score=85)
db.add_report(seid, "warning", "家校预警", "...")
```

### 设计亮点
1. **连接管理器** —— `@contextmanager` + `try/except/finally` 自动提交/回滚/关闭连接，不会泄露
2. **参数化查询** —— 所有 SQL 都用 `?` 占位符，防止 SQL 注入
3. **CHECK 约束** —— 枚举字段（role/risk_level/report_type）直接在数据库层限制取值，脏数据进不来
4. **外键级联** —— 设置 `PRAGMA foreign_keys = ON`，删除学生自动清理所有下游数据
5. **索引** —— 在高频查询字段建索引，消息/风险/报告按 session 查询更快
6. **时间格式统一** —— 全部用 ISO 8601 格式（`datetime.now().isoformat(timespec="seconds")`），方便排序和解析

数据库模块已经就绪，可以作为后续 `agent_core.py`、`report.py`、`risk.py` 等模块的数据层基础了！