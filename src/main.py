"""
src/main.py
MindIsle（心屿）程序入口 / 联调演示

ACPSMultiAgentOrchestrator 核心逻辑已规范化迁移至 src/agent_core.py，
此处仅复用，避免重复维护。
"""

import os
import sys

# 兼容两种运行方式：
#   python src/main.py  （脚本所在目录 src/ 位于 sys.path）
#   python -m src.main  （项目根目录位于 sys.path）
try:
    from src.agent_core import ACPSMultiAgentOrchestrator
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from agent_core import ACPSMultiAgentOrchestrator


if __name__ == "__main__":
    orchestrator = ACPSMultiAgentOrchestrator()
    print("测试正常对话:", orchestrator.process_dialogue("今天考试没考好，有点难过"))
    print("测试安全一票否决:", orchestrator.process_dialogue("我真的不想活了，想跳楼"))
