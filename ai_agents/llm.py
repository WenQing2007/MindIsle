"""
ai_agents/llm.py
MindIsle（心屿）大模型接入层 —— OpenAI 兼容 chat/completions 客户端

支持任何提供 OpenAI 兼容接口的服务商（仅需三种配置）：
  DeepSeek     https://api.deepseek.com/v1                  模型 deepseek-chat
  OpenAI       https://api.openai.com/v1
  硅基流动     https://api.siliconflow.cn/v1
  Moonshot     https://api.moonshot.cn/v1
  通义千问     https://dashscope.aliyuncs.com/compatible-mode/v1
  智谱 GLM     https://open.bigmodel.cn/api/paas/v4
  本地 Ollama  http://localhost:11434/v1                    模型 qwen2 / llama3

启用方式（环境变量，建议写入项目根目录 .env 文件；.env 已被 .gitignore 忽略，
API Key 不会提交到 git）：
    LLM_ENABLED=true
    LLM_API_KEY=sk-xxxxxxxxxxxxxxxx
    LLM_API_BASE=https://api.deepseek.com/v1
    LLM_MODEL=deepseek-chat
    LLM_TIMEOUT=30

容错设计：未配置 Key 或任何调用失败时，上层协调器自动回退到规则模板话术，
保证系统在无网络 / 无 Key 环境下依然可以完整跑通协商流程。
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# 配置加载（环境变量，支持 .env 由后端启动时加载）
# ---------------------------------------------------------------------------

DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_MODEL = "deepseek-chat"


def get_config() -> Dict[str, Any]:
    """读取 LLM 相关环境变量配置。"""
    return {
        "enabled": bool(os.getenv("LLM_ENABLED", "").strip().lower() in ("1", "true", "yes", "on")),
        "base": os.getenv("LLM_API_BASE", DEFAULT_BASE_URL).strip().rstrip("/") or DEFAULT_BASE_URL,
        "key": os.getenv("LLM_API_KEY", "").strip(),
        "model": os.getenv("LLM_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL,
        "timeout": float(os.getenv("LLM_TIMEOUT", "30") or 30),
    }


def is_enabled() -> bool:
    """是否启用 LLM 自动回复（需 LLM_ENABLED=true 且已配置 API Key）。"""
    cfg = get_config()
    return cfg["enabled"] and bool(cfg["key"])


def status_text() -> str:
    """供后台 /health 等展示用的可读状态。"""
    cfg = get_config()
    if cfg["enabled"] and cfg["key"]:
        return f"已接入 {cfg['base']} / {cfg['model']}"
    if cfg["enabled"] and not cfg["key"]:
        return "LLM_ENABLED=true 但缺少 LLM_API_KEY，当前使用模板兜底"
    return "未启用（设置 LLM_ENABLED=true 与 LLM_API_KEY 后接入大模型）"


class LLMError(Exception):
    """LLM 调用失败（网络 / 鉴权 / 响应格式）。"""


# ---------------------------------------------------------------------------
# 对话补全
# ---------------------------------------------------------------------------

def chat_completion(
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 1024,
    json_mode: bool = False,
) -> str:
    """调用 OpenAI 兼容 chat/completions，返回模型输出的文本内容。

    :param messages: 形如 [{"role": "system"|"user"|"assistant", "content": "..."}]
    :param json_mode: True 时请求 response_format 为 json_object，要求模型输出合法 JSON
    :raises LLMError: Key 未配置、网络失败、HTTP 错误或响应格式异常
    """
    cfg = get_config()
    if not cfg["key"]:
        raise LLMError("LLM_API_KEY 未配置，无法调用大模型")

    url = cfg["base"] + "/chat/completions"
    body: Dict[str, Any] = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}

    req = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + cfg["key"],
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=cfg["timeout"]) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8")[:300]
        except Exception:  # noqa: BLE001
            pass
        raise LLMError(f"LLM HTTP {exc.code}: {detail or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise LLMError(f"LLM 请求失败: {exc.reason}") from exc

    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"LLM 响应格式异常: {str(data)[:300]}") from exc


def safe_chat(
    messages: List[Dict[str, str]],
    fallback: str = "",
    **kwargs: Any,
) -> str:
    """带兜底的 LLM 调用：成功返回模型文本，未启用 / 失败返回 fallback。"""
    if not is_enabled():
        return fallback
    try:
        text = chat_completion(messages, **kwargs)
        return text or fallback
    except LLMError as exc:
        print(f"[MindIsle·LLM] 调用失败，回退模板话术 - {exc}")
        return fallback
    except Exception as exc:  # noqa: BLE001 任何异常都不影响主流程
        print(f"[MindIsle·LLM] 未预期异常，回退模板话术 - {exc}")
        return fallback


if __name__ == "__main__":
    print("MindIsle LLM 接入层")
    print("  当前配置:", get_config())
    print("  状态:", status_text())
    print("  是否启用:", is_enabled())
