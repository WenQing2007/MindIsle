# MindIsle
MindIsle is a multi-agent psychological counseling and scenario interaction system oriented to primary and secondary school students. Based on multi-agent technology, the system recognizes user emotions and delivers customized psychological counseling, building an immersive interactive scene to assist adolescents in managing their mental health
# MindIsle 心屿 · 中小学生心理疏导系统

> 《程序设计实验》课程设计 · 3 人小组 · Python 桌面应用

## 📖 项目简介

MindIsle（心屿）是一个面向中小学生的语音心理疏导桌面软件。系统通过语音对话感知学生情绪，
由多个智能体（情绪识别 / 疏导 / 干预 / 调度）协作完成分析与回应，并配合人像图片、
场景背景和背景音乐营造沉浸式交互体验；对话过程自动记录日志，可生成心理报告与家校预警文本。

**一句话**：跟孩子说说话 → 判断情绪等级 → 给出疏导回应 → 必要时预警 → 生成报告。

## ✨ 主要功能

- 🎤 语音对话：麦克风语音输入（SpeechRecognition），文字转语音朗读（pyttsx3）
- 🤖 多智能体协作：情绪识别 Agent、疏导 Agent、干预 Agent、调度 Agent
- 🖼️ 场景化交互：按情绪自动切换人像图片、场景背景与轻音乐
- 🛡️ 分级处理：轻度（预防疏导）/ 中度（干预建议）/ 高危（家校预警）
- 📄 数据与报告：对话日志（json）→ 自动心理报告（txt）→ 家校预警文本

## 🗂️ 目录结构

| 路径 | 说明 | 负责人 |
|---|---|---|
| `main.py` | 程序入口与整体联调 | C |
| `agent_core.py` | 多智能体核心逻辑 | A |
| `emotion_dict.py` | 情绪关键词库与疏导话术库 | A |
| `gui_voice.py` | tkinter 界面 + 语音 + 图片/音乐 | B |
| `report_save.py` | 日志读写、报告与预警生成 | C |
| `img/portrait` · `img/scene` | 人像图片、场景背景图 | B |
| `audio/bgm` | 背景轻音乐 | B |
| `data` · `output` | 对话日志、报告输出 | C |
| `docs` | 需求分析、课程设计报告、图表、PPT | 全员 |
| `tests` | 各模块自测脚本 | 全员 |

## 🚀 运行方法

```bash
pip install -r requirements.txt
python main.py