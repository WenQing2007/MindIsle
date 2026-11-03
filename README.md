# MindIsle / 心屿 —— 学生心理安全评估与多智能体陪伴系统

> **《程序设计实验》课程设计 · 三人小组 · Python 桌面应用**
>
> 一句话概括：**跟孩子说说话 → 识别情绪与风险等级 → 多智能体按北邮 ACPs 协作疏导 → 高危信号触发“一票否决”并展示 24 小时心理援助热线 → 必要时家校预警与心理报告。**

---

MindIsle（心屿）是一款面向 **6–18 岁中小学生**的语音心理陪伴与多智能体心理疏导系统。系统以语音/文字对话为入口感知学生情绪与心理状态，由**安全评估、共情陪伴、认知行为（CBT）、情景导演、发展心理学、家校上下文、协调**等多个专业智能体，严格遵循**北邮 ACPs（Agent Collaboration Protocols）智能体互联协议**并行产出建议、内部校验与整合输出统一回复；同时配合人像、场景、轻音乐营造沉浸式交互体验，对话自动记录日志，可生成心理成长报告与家校预警文本。

- 面向对象：中小学生（核心用户）、心理教师与班主任（预警处置）、系统管理员
- 运行形态：Python 桌面应用，可独立部署；预留“智慧校园学生心理健康服务平台”子模块接入接口
- 课程信息：2025219107 班 · 指导教师 许晨 · 2026 年 9 月 29 日

---

## 🏛️ 核心特性与架构（Core Features & Architecture）

### 1️⃣ 严格遵循北邮 ACPs（Agent Collaboration Protocols）协议

系统内部智能体之间的注册、发现、协作与消息路由全面遵循北邮智能体互联协议标准：

| 协议 | 全称 | 在本系统中的作用 |
|---|---|---|
| **ARP / ADP** | Agent Registration / Discovery Protocol | 各专业智能体能力的**动态注册**与**分布式寻址** |
| **AIP** | Agent Interaction Protocol | 多智能体**并行讨论、交叉校验、修订整合**的报文格式与传输规范，以及安全评估智能体“一票否决”**中断指令**的规范 |

典型处理流水线：

```
学生输入（语音 / 文字）
   │
   ├─ ASR 语音识别（可选）
   ▼
[安全评估 Agent] —— 优先独立运行，拥有最高优先级
   │   ├─ 命中高危信号？── 是 ──▶ 🛑 一票否决，立即中断，展示 24 小时援助热线
   │   └─ 未命中
   ▼
[共情陪伴 Agent]  [认知行为 CBT Agent]  [情景导演 Agent]  [发展心理学 Agent] …
   │                   互相对话、交叉校验、修订（ACPs / AIP）
   ▼
[协调 Agent] —— 汇总整合为统一回复，按分龄策略输出
   │
   ▼
TTS 语音合成 / 文字气泡 输出
```

### 2️⃣ 安全评估智能体优先运行与“一票否决”机制

> **核心安全设计**：安全评估 Agent 独立于疏导流程**优先运行**，且拥有**一票否决权（veto）**。

- 高危信号（自伤、自杀意向、严重欺凌与暴力等）由安全评估 Agent 独立识别；
- 一旦命中，**任何其他智能体的正常疏导输出一律作废**，立即：
  1. 返回 `is_vetoed = True`、`risk_level = red`；
  2. 中断剧情 / 正常对话流程，切换到应急话术；
  3. 展示 **24 小时全国心理援助热线：400-161-9995**；
  4. 触发前端应急弹窗（`action = TRIGGER_EMERGENCY_POPUP`）。
- **危机红线**：无论系统是否故障，一旦识别到自伤、自杀等危险信号，必须保证第一时间展示心理援助热线。

当前 `src/agent_core.py` 已实现的关键词层拦截（规则版）：

```python
HIGH_RISK_KEYWORDS = ["想死", "自杀", "跳楼", "割腕", "被打了", "霸凌"]
```

### 3️⃣ 共情陪伴与 CBT（认知行为疗法）多智能体协同

- **共情陪伴 Agent**：识别并接住情绪，提供无条件积极关注的陪伴式回应，适合小学生角色陪伴与日常疏导；
- **认知行为（CBT）Agent**：运用认知重建、行为激活等技术，帮助学生识别不合理信念、从“知道”到“做到”；
- **情景导演 / 发展心理学 / 家校上下文 Agent**：模拟真实困境场景（起外号、考试失利、同伴矛盾、亲子沟通、识别欺凌等），并结合分龄特征与家校背景输出差异化建议；
- 多智能体在 **协调 Agent** 组织下按 ACPs（AIP）规则**并行讨论 → 交叉校验 → 修订整合**为统一回复，避免单一智能体角色混乱；
- **冲突或存疑时，以安全评估 Agent 的一票否决为准，并输出经审核的兜底话术。**

### 4️⃣ 多级风险预警体系（绿 / 黄 / 橙 / 红）

| 等级 | 语义 | 系统动作 |
|---|---|---|
| 🟢 绿 | 一般情绪波动 | 情绪素养课程 / 正常共情陪伴 |
| 🟡 黄 | 轻度风险 | 推送放松训练，匿名化提示教师关注 |
| 🟠 橙 | 中度风险 | 通知心理教师介入并预约面谈 |
| 🔴 红 | 高危（自伤 / 自杀意向 / 严重欺凌等） | **一票否决中断剧情，立即展示 24 小时心理援助热线，家校预警** |

### 5️⃣ 其他关键能力

语音对话与情绪疏导、情景演练、多模态心理画像（文本 / 语音韵律 / 绘画 / 沙盘）、自动报告生成（个体成长报告 / 班级心理氛围报告 / 危机事件处置报告）、心理资源与测评中心、教师工作台与管理后台、内容安全过滤与系统级安全管控。

---

## 🧰 技术栈（Tech Stack）

| 类别 | 选型 |
|---|---|
| 开发语言 | **Python 3** |
| 数据库 | **SQLite**（学生、会话、测评等业务数据；音频/图片大文件存文件目录） |
| 语音 | SpeechRecognition（ASR）、pyttsx3（TTS） |
| 音频播放 | playsound |
| 界面 | tkinter（图形界面） |
| 版本管理 | **Git / GitHub Desktop** |
| 协作协议 | 北邮 ACPs（ARP/ADP/AIP） |

依赖清单见 [`requirements.txt`](requirements.txt)。

---

## 📁 项目目录结构（Project Structure）

```
MindIsle/
├── src/                       # 源码目录
│   ├── agent_core.py          # 【核心】ACPs 多智能体协调器 + 安全一票否决
│   ├── main.py                # 程序入口 / 联调演示
│   ├── emotion_dict.py        # 情绪关键词库与疏导话术库
│   ├── gui_voice.py           # tkinter 界面 + 语音 + 图片/音乐
│   └── report_save.py         # 日志读写、报告与预警生成
├── tests/
│   ├── test_agent_core.py     # 安全一票否决机制单元测试
│   └── .gitkeep
├── docs/                      # 需求分析 / 课程设计报告 / 图表
│   └── 需求分析.md            # 需求分析文档（Markdown 版）
├── img/portrait · img/scene   # 人像图片、场景背景图
├── audio/bgm · audio/tts_cache# 背景轻音乐、语音合成缓存
├── data/ · output/            # 对话日志、报告输出
├── requirements.txt           # 第三方依赖清单
└── README.md
```

### 🔑 关键文件说明

| 文件 | 职责说明 |
|---|---|
| **`src/agent_core.py`** | 项目**核心模块**。封装遵循北邮 ACPs 规范的 `ACPSMultiAgentOrchestrator` 多智能体协调器：安全评估 Agent 优先独立运行并执行**一票否决（veto）**；`check_safety()` 输出风险判定（`is_risk / risk_level / veto / keyword`），`process_dialogue()` 返回统一对话结果（`is_vetoed / response_text / action`）。高危时回复包含 24 小时心理援助热线 `400-161-9995`，正常时返回共情陪伴话术。 |
| **`src/main.py`** | **程序入口 / 联调演示**。从 `agent_core` 复用协调器，演示“普通输入 → 共情陪伴”与“危险输入 → 一票否决”两条分支，支持 `python src/main.py` 直接运行。 |
| **`tests/test_agent_core.py`** | **核心机制单元测试**（标准库 `unittest`，零额外依赖）。覆盖“危险输入 → 一票否决返回热线”与“普通输入 → 共情陪伴”两条主分支，并验证关键词命中细节、绿色放行与自定义关键词/热线可配置性，共 5 个用例。 |

---

## 🚀 快速开始与测试指南（Quick Start & Testing）

### 环境准备

```bash
# 1. 安装第三方依赖（Windows 环境）
pip install -r requirements.txt

# 2. 建议 Python 3.9+，确认版本
python --version
```

### 运行单元测试

```bash
# 方式一：推荐（discover 自动发现 tests/ 下所有 test_*.py）
python -m unittest discover -s tests -v

# 方式二：直接运行测试脚本（附带两条分支的演示输出）
python tests\test_agent_core.py
```

预期结果：`Ran 5 tests ... OK`，覆盖“一票否决”与“共情陪伴”两条分支及边界情况。

### 接入大模型（LLM 自动回复，可选）

聊天默认使用内置分级模板话术；如需由大模型生成个性化回复，只需在项目根目录
建立 `.env` 文件（模板见 `.env.example`，`.env` 已被 `.gitignore` 忽略，Key 不会入库）：

```bash
# 复制模板并填入你的 API Key
copy .env.example .env
```

```dotenv
LLM_ENABLED=true
LLM_API_KEY=sk-你的密钥
LLM_API_BASE=https://api.deepseek.com/v1   # OpenAI 兼容地址均可（通义/智谱/硅基流动/Moonshot/Ollama）
LLM_MODEL=deepseek-chat
```

建议参考 `GET /health` 返回的 `llm` 字段确认接入状态。机制说明：

- **多轮记忆**：后端自动携带当前会话最近 8 条历史给模型；
- **高危一票否决**：`red` 级输入**不会**交给大模型自由发挥，仍输出含 24 小时
  心理援助热线的应急话术（红线兜底）；
- **故障降级**：未配置 Key / 请求失败 / 超时时自动回退到内置分级模板，保证系统离线可用。

### 运行主程序

```bash
python src\main.py
```

预期输出示例：

```text
测试正常对话: {'risk_level': 'green', 'is_vetoed': False, 'response_text': '收到你的倾诉。…', 'action': 'NORMAL_TALK', 'reason': ''}
测试安全一票否决: {'risk_level': 'red', 'is_vetoed': True, 'response_text': '听到你现在经历的痛苦，…24 小时全国心理援助热线：400-161-9995。', 'action': 'TRIGGER_EMERGENCY_POPUP', 'reason': '触发高危词汇: 跳楼'}
```

### 在代码中使用核心协调器

```python
from src.agent_core import ACPSMultiAgentOrchestrator

orchestrator = ACPSMultiAgentOrchestrator()   # 支持自定义关键词表与热线：
# orchestrator = ACPSMultiAgentOrchestrator(
#     high_risk_keywords=["不想活了"],
#     emergency_hotline="400-161-9995",
# )
result = orchestrator.process_dialogue("我真的不想活了，想跳楼")
# {'is_vetoed': True, 'response_text': '…400-161-9995…', 'action': 'TRIGGER_EMERGENCY_POPUP', ...}
```

---

## 👥 团队与分工（Team & Responsibilities）

**小组成员**：彭钰哿 · 黄文卿 · 李锦　（指导教师：许晨）

| 模块 | 路径 | 负责人 |
|---|---|---|
| 程序入口与整体联调 | `src/main.py` | C |
| ACPs 多智能体核心逻辑（含安全一票否决） | `src/agent_core.py` | A |
| 情绪关键词库与疏导话术库 | `src/emotion_dict.py` | A |
| tkinter 界面 + 语音 + 图片/音乐 | `src/gui_voice.py` | B |
| 日志读写、报告与预警生成 | `src/report_save.py` | C |
| 需求分析 / 课程设计报告 / 图表 / PPT | `docs/` | 全员 |

---

## 📚 相关文档

- [`docs/需求分析.md`](docs/需求分析.md) —— 需求分析文档（任务概述、需求规定、运行环境等）

## ⚠️ 伦理与安全声明

- 系统只提供**心理支持、预防与预警**，不输出医疗诊断与治疗方案；
- 所有 AI 生成内容标注 **“AI 生成，供参考，不构成诊断结论”**；
- 高危个案必须**转介专业机构 / 心理教师**，任何环节不得隐藏危机信号；
- 遵循《个人信息保护法》《未成年人保护法》《儿童个人信息网络保护规定》，未成年人数据**最小采集、加密存储、到期删除**，使用前获得监护人知情同意。
