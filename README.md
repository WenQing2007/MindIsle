# MindIsle（心屿）—— 学生心理安全评估与多智能体陪伴系统

> **《程序设计实验》课程设计 · 三人小组 · Web 全栈应用**
>
> 一句话概括：**学生和 AI 说说话 → 四级风险评估 → ACPs 多智能体按等级协作疏导 → 高危触发「一票否决」立即展示 24 小时心理援助热线 → 教师端收到四色预警并生成 PDF 心理报告。**

MindIsle（心屿）是一套面向 **6–18 岁中小学生**的心理陪伴与安全评估系统。学生通过 Web 页面以文字方式与 AI 倾诉，系统对其输入进行**四级风险（绿 / 黄 / 橙 / 红）实时评估**，并交由遵循**北邮 ACPs（Agent Collaboration Protocols）** 的多智能体协调器协同疏导；接入大模型后由 LLM 实时生成个性化回复；教师端提供"四色预警名单"，并可一键生成 PDF 心理报告。

- 面向对象：中小学生（核心用户）、心理教师与班主任（预警处置）、系统管理员
- 运行形态：Vue3 前后端分离 Web 应用（FastAPI + SQLite），可本地独立部署
- 课程信息：2025219107 班 · 指导教师 许晨
- 详细设计见：[`docs/需求分析.md`](docs/需求分析.md) 与 [`docs/02_课程设计报告/课程设计报告.md`](docs/02_课程设计报告/课程设计报告.md)

---

## ✨ 核心特性

### 1️⃣ 四级风险路由的多智能体体系（ACPs）

| 风险等级 | 判定语义（示例关键词） | 参与智能体 | 系统动作 |
|---|---|---|---|
| 🟢 绿 / `low` | 情绪积极、一般波动（开心、谢谢） | 共情陪伴 Agent | 正常聊天陪伴 |
| 🟡 黄 / `medium` | 压力、焦虑、难过（压力大、睡不着） | 共情陪伴 + **CBT 认知行为** | 匿名提示教师关注 |
| 🟠 橙 / `high` | 受欺凌、恐惧、被威胁（被欺负、害怕） | 共情陪伴 + CBT + **情景导演** | 通知心理教师介入 |
| 🔴 红 / `critical` | 自伤、自杀意念（想死、跳楼、割腕） | 安全评估 Agent（**一票否决**） | 中断对话，展示 24h 心理援助热线 |

### 2️⃣ 安全智能体优先运行与「一票否决」
- 安全评估 Agent **独立优先运行**，拥有最高优先级；
- 一旦命中 🔴 高危信号，其他智能体的正常疏导输出**一律作废**，并保证 4 件事：
  1. 返回 `is_vetoed=True`、`risk_level=red`；
  2. 🔴 级输入**不会交给大模型自由发挥**，直接返回含 **24 小时全国心理援助热线 `400-161-9995`** 的应急话术；
  3. 触发前端应急弹窗 `TRIGGER_EMERGENCY_POPUP`，聊天页显示红色警示横幅；
  4. 自动写入 `risk_assessment` 表并进入教师端预警名单。

### 3️⃣ 大模型实时生成 + 模板兜底降级
- 通过 **OpenAI 兼容接口**接入大模型（默认北邮 myai 平台，模型 `deepseek-v4-flash`）；
- 自动携带当前会话**最近 8 条历史**，实现多轮对话记忆；
- 未配置 Key / 断网 / 超时 / 响应异常时，**自动回退内置分级模板话术**，保证离线可用。

### 4️⃣ 三类用户角色
| 角色 | 可用功能 |
|---|---|
| 🧑‍🎓 学生 | 注册 / 登录、AI 心理陪伴聊天（历史会话）、匿名**树洞**、我的心理报告 |
| 👩‍🏫 教师 | 登录、**四色风险预警名单**（统计卡片 + 表格）、生成 PDF 心理报告 |
| 🛠️ 管理员 | 登录（管理后台预留） |

---

## 🧰 技术栈（Tech Stack）

| 层 | 选型 |
|---|---|
| 前端 | **Vue 3** · Vite · Element Plus · Vue Router · Axios |
| 后端 | **FastAPI** · Uvicorn · SQLite（文件型） |
| AI 引擎 | OpenAI 兼容大模型（默认北邮 myai 网关 `/llm-gw/v1`，`deepseek-v4-flash`） |
| 智能体引擎 | 自研 ACPs 多智能体协调器（协商 → 路由 → 交叉校验 → 整合）+ AIP 报文协议 |
| 报告 | fpdf2（中文 PDF，黑体字体） |
| 测试 | **pytest（24 个用例全部通过）** |

---

## 🏛️ 系统架构

```text
浏览器（Vue3 单页应用）
        │  HTTP / JSON（开发期由 Vite Proxy 转发到 :8000）
        ▼
FastAPI 后端（backend/app.py）
   ├── 认证 / 会话 / 树洞 / 报告 路由  ──► SQLite（backend/database.py）
   ├── 教师四色预警  /api/teacher/warnings
   └── AI 聊天  /api/chat/send
            │
            ▼
    多智能体协调器（ai_agents/coordinator.py · MultiAgentCoordinator）
         ① 安全评估 Agent（优先独立运行，可一票否决）
         ② 按风险等级路由：共情陪伴 / CBT / 情景导演
         ③ ACPs / AIP 协商：DISCUSS → CROSS_CHECK → INTEGRATE（记录协作日志）
         ④ 协调器整合统一回复
            │
            ▼
   大模型（deepseek-v4-flash · OpenAI 兼容 /chat/completions）
   或 规则模板兜底（离线降级）
```

---

## 📁 项目目录结构（Project Structure）

```text
MindIsle/
├── backend/                     # FastAPI 后端
│   ├── app.py                   # 应用入口：全部 REST 路由
│   ├── database.py              # SQLite 数据层（7 张表，参数化查询 + 外键级联）
│   ├── risk.py                  # 四级风险评估（关键词规则）
│   ├── report.py                # PDF 心理报告生成（fpdf2）
│   ├── requirements.py          # 环境依赖说明脚本
│   └── *.md                     # 各模块设计文档
├── ai_agents/                   # ACPs 多智能体引擎（核心）
│   ├── coordinator.py           # 协调器：路由 / 协商 / 一票否决 / 整合
│   ├── protocols.py             # AIP 交互协议报文封装（ACPs/AIP）
│   ├── prompts.py               # 四类专业智能体 Prompt 模板
│   └── llm.py                   # 大模型接入层（配置 / 调用 / 降级）
├── Mindlsle_fronted/frontend/   # Vue3 前端
│   └── src/
│       ├── api/                 # Axios 接口封装（student/teacher/chat/request）
│       ├── router/index.js      # 路由与登录守卫
│       ├── views/student/       # 学生端：登录 / 注册 / 首页 / Chat / 树洞 / 报告
│       ├── views/teacher/       # 教师端：登录 / WarnList 预警名单
│       └── views/admin/         # 管理员登录
├── src/                         # 早期经典实现（agent_core.py 兼容保留）
├── tests/                       # pytest 测试（24 用例）
│   ├── test_agent_core.py       # 一票否决核心机制
│   ├── test_ai_agents.py        # AIP 协议 + 多智能体路由
│   └── test_llm.py              # LLM 接入与降级
├── data/mindisle.db             # SQLite 数据库（启动自动初始化，gitignore）
├── output/                      # 生成的 PDF 报告输出目录
├── .env.example                 # 环境变量模板（LLM 配置）
├── requirements.txt             # Python 依赖
└── docs/                        # 需求分析、课程设计报告
```

---

## 🚀 快速启动指南（Quick Start）

### 0️⃣ 环境准备
- Python **3.10+**
- Node.js **18+**（含 npm）

### 1️⃣ 配置大模型 `.env`（可选，不配也能用）
```bash
copy .env.example .env      # Windows
```
编辑 `.env` 填入你的密钥：
```dotenv
LLM_ENABLED=true
LLM_API_KEY=sk-你的密钥
LLM_API_BASE=https://myai.bupt.edu.cn/llm-gw/v1
LLM_MODEL=deepseek-v4-flash
LLM_TIMEOUT=30
```
> ⚠️ 说明：**未配置 Key 时系统会自动降级为内置模板话术**，聊天、树洞、预警等功能仍可完整使用；`.env` 已被 .gitignore 忽略，Key 不会进入版本库。

### 2️⃣ 启动后端（终端 1）
```powershell
# 安装依赖（首次）
pip install -r requirements.txt

# 启动后端（务必只启动一个实例，避免端口冲突）
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
```
验证：浏览器打开 `http://localhost:8000/health`，应返回 JSON（含 `llm` 接入状态）。

### 3️⃣ 启动前端（终端 2）
```powershell
cd Mindlsle_fronted/frontend
npm install          # 首次
npm run dev
```
访问：**http://localhost:5173/**（Vite 已将 `/api` 代理到后端 :8000）。

### 4️⃣ 内置测试账号
| 角色 | 用户名 | 密码 |
|---|---|---|
| 🧑🎓 学生 | `student` | `123456` |
| 👩‍🏫 教师 | `teacher` | `teacher` |
| 🛠️ 管理员 | `admin` | `admin` |

---

## 🔬 测试方法（Testing）

```powershell
# 方式一：pytest（推荐）
python -m pytest tests -v

# 方式二：标准库 unittest
python -m unittest discover -s tests -v
```

预期结果：**24 passed**（另含 9 个子断言），覆盖：
- 安全评估「一票否决」（red → 应急热线，且不交给大模型）；
- 四级风险路由（绿→共情 / 黄→共情+CBT / 橙→+情景导演 / 红→仅安全评估）；
- AIP 协议报文的构造、序列化往返与合法性校验；
- LLM 接入层（未配置 Key 抛错、失败回退模板）与协调器集成（多轮记忆拼装、red 级别仍走应急模板）。

更多人工联调路径：学生端聊天输入"我最近压力好大"（黄）→ "我被同学欺负了"（橙）→ "我真的不想活了"（红），观察聊天页风险标签、橙色预警与红色热线横幅。

---

## 🌐 主要 API 一览

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/student/register` / `/api/student/login` | 学生注册 / 登录 |
| POST | `/api/teacher/login` / `/api/admin/login` | 教师 / 管理员登录 |
| POST | `/api/chat/send` | 发送消息，返回回复 + 风险评估 |
| GET | `/api/chat/sessions` / `/api/chat/history` | 会话列表 / 会话记录 |
| GET | `/api/treehole/list` / POST `/api/treehole/add` | 树洞匿名内容 |
| GET | `/api/teacher/warnings` | 教师四色预警名单 |
| POST | `/api/report/student/{id}` / `download` | 生成 / 下载 PDF 报告 |
| GET | `/health` | 健康检查（含 LLM 接入状态） |

---

## 👥 团队与分工（Team & Responsibilities）

**小组成员**：彭钰哿 · 黄文卿 · 李锦（指导教师：许晨）

| 模块 | 负责人 |
|---|---|
| ACPs 多智能体引擎 · 风险评估 · 测试 | 彭钰哿 |
| Vue3 前端 · UI / 交互 | 黄文卿 |
| FastAPI 后端 · 数据库 · PDF 报告 · 需求文档 | 李锦 |

---

## ⚠️ 伦理与安全声明

- 本系统只提供**心理支持、预防与预警**，不输出医疗诊断与治疗方案；
- 所有 AI 生成内容标注 **"AI 生成，供参考，不构成诊断结论"**；
- 高危个案必须**转介专业机构 / 心理教师**，任何环节不得隐藏危机信号；
- 遵循《个人信息保护法》《未成年人保护法》《儿童个人信息网络保护规定》，未成年人数据**最小采集、加密存储、到期删除**，使用前获得监护人知情同意。
